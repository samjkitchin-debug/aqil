"""Cabinet Office machinery orders: nominal calendar month, stable ids, no fiscal year."""

from __future__ import annotations

import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

import aqil_research.adapters.cao_mo_private_ex_volatile.adapter as adapter_module
from aqil_research.adapters.cao_mo_private_ex_volatile.adapter import (
    CaoMoAdapter,
    CaoMoAdapterConfig,
)
from aqil_research.adapters.cao_mo_private_ex_volatile.client import (
    MAX_ATTEMPTS,
    CaoMoClientError,
    catalogue_url,
    workbook_url_from_catalogue,
)
from aqil_research.adapters.cao_mo_private_ex_volatile.constants import (
    CATALOGUE_URL,
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    SOURCE_ID,
    UNIT_TEXT,
)
from aqil_research.adapters.cao_mo_private_ex_volatile.parse import parse_cao_mo_workbook
from aqil_research.adapters.cao_mo_private_ex_volatile.stability import StoredCaoMoPoint
from aqil_research.adapters.protocol import ProviderFailureCode
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsDecision,
    load_source_rights,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = (
    Path(__file__).parent / "fixtures" / "cao_mo_private_ex_volatile" / "chouki_1_excerpt.xlsx"
)
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "cao_mo_private_ex_volatile_sa_monthly.csv"
)
RETRIEVED = datetime(2026, 10, 24, 4, 0, tzinfo=UTC)
DEFAULT_ROWS = (
    ("2026", "6", "1055761.7610599999"),
    ("2026", "7", None),
    ("2026", "8", "1069778.74994"),
)
EXCERPT_VALUES = {
    date(2026, 6, 1): "1055761.7610599999",
    date(2026, 8, 1): "1069778.74994",
}
STRINGS = (
    "主要需要者別受注額(季調系列・月次)",
    "Machinery Orders by Sectors, Sales and Remainders(Seasonally adjusted, Monthly)",
    "(単位:100万円)",
    "(船舶・電力",
    "を除く)",
    "(Exc. Volatile",
    "orders*)",
    "note",
    "年度",
)


def _collapsed(value: str) -> str:
    return " ".join(value.split())


def write_workbook(
    path: Path,
    rows: tuple[tuple[str, str, str | None], ...] = DEFAULT_ROWS,
    *,
    include_bound_sheet: bool = True,
    column_mark: str = "(船舶・電力",
) -> None:
    """Write a small workbook. The fiscal-year sheet carries a decoy value of 1."""
    strings = list(STRINGS)
    strings[3] = column_mark
    sheet_rows: list[str] = [
        '<c r="D2" t="s"><v>0</v></c>',
        '<c r="D3" t="s"><v>1</v></c>',
        '<c r="P2" t="s"><v>2</v></c>',
        '<c r="J5" t="s"><v>3</v></c>',
        '<c r="J6" t="s"><v>4</v></c>',
        '<c r="J8" t="s"><v>5</v></c>',
        '<c r="J9" t="s"><v>6</v></c>',
        '<c r="D10"><v>999999999</v></c>',
        '<c r="B16" t="s"><v>7</v></c>',
    ]
    for offset, (year, month, value) in enumerate(rows):
        row_number = 10 + offset
        sheet_rows.append(f'<c r="B{row_number}"><v>{year}</v></c>')
        sheet_rows.append(f'<c r="C{row_number}"><v>{month}</v></c>')
        if value is not None:
            sheet_rows.append(f'<c r="J{row_number}"><v>{value}</v></c>')
    bound_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData><row>{''.join(sheet_rows)}</row></sheetData></worksheet>"
    )
    decoy_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row><c r="D2" t="s"><v>8</v></c>'
        '<c r="B10"><v>2026</v></c><c r="C10"><v>8</v></c>'
        '<c r="J10"><v>1</v></c></row></sheetData></worksheet>'
    )
    shared_items = "".join(f"<si><t>{text}</t></si>" for text in strings)
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"{shared_items}</sst>"
    )
    sheets = []
    if include_bound_sheet:
        sheets.append(('name="季調・月次" sheetId="1" r:id="rId1"', "sheet1.xml", bound_xml))
    sheets.append(('name="年度・暦年" sheetId="2" r:id="rId2"', "sheet2.xml", decoy_xml))
    sheet_tags = "".join(f"<sheet {attrs}/>" for attrs, _name, _xml in sheets)
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_tags}</sheets></workbook>"
    )
    rel_items = "".join(
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        if name == "sheet1.xml"
        else '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet2.xml"/>'
        for _attrs, name, _xml in sheets
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{rel_items}</Relationships>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as book:
        book.writestr("xl/workbook.xml", workbook_xml)
        book.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        book.writestr("xl/sharedStrings.xml", shared_xml)
        for _attrs, name, xml in sheets:
            book.writestr(f"xl/worksheets/{name}", xml)


def write_default_fixture() -> None:
    write_workbook(FIXTURE)


def _refuse_database(*args: object, **kwargs: object) -> None:
    raise AssertionError(f"database connection is not allowed: {args!r} {kwargs!r}")


def _bind_memory(monkeypatch: pytest.MonkeyPatch) -> InMemoryObservationStore:
    monkeypatch.setattr("psycopg.connect", _refuse_database)
    records = load_source_rights(FRAGMENT)
    monkeypatch.setattr(
        "aqil_research.collection.service.load_source_rights",
        lambda path=None: records,
    )
    store = InMemoryObservationStore()
    monkeypatch.setattr(
        "aqil_research.collection.service.InMemoryObservationStore",
        lambda: store,
    )
    return store


def _adapter(
    path: Path,
    retrieved_at: datetime,
    prior: tuple[StoredCaoMoPoint, ...] = (),
) -> CaoMoAdapter:
    return CaoMoAdapter(
        config=CaoMoAdapterConfig(live=False, fixture_path=path),
        retrieved_at=retrieved_at,
        prior_points=prior,
    )


def _points(store: InMemoryObservationStore) -> tuple[StoredCaoMoPoint, ...]:
    return tuple(
        StoredCaoMoPoint(
            period_start=row.period_start,
            observation_id=row.observation_id,
            raw_value=row.raw_value,
            provider_vintage_date=row.provider_vintage_date,
            source_release_at=row.source_release_at,
            retrieved_at=row.retrieved_at,
            first_seen_at=row.first_seen_at,
        )
        for row in store.all_observations()
    )


def test_rights_fragment_clears_first_live_use() -> None:
    records = load_source_rights(FRAGMENT)
    record = records[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.operational_status == OperationalStatus.ENABLED
    assert record.attribution == AttributionRequirement.REQUIRED
    assert record.assessed_on.isoformat() == "2026-10-24"
    assert record.terms_url in record.evidence_urls
    assert "商用利用も可能です" in record.evidence_note
    assert "nominal" in record.evidence_note
    assert "fiscal-year" in record.evidence_note
    assert "calendar month" in record.evidence_note
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(record.evidence_note)
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED


def test_adapter_documents_method_compatibility() -> None:
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(adapter_module.__doc__ or "")
    assert DATASET_ID not in SahmAnalyticalMethod().required_dataset_ids()


def test_catalogue_selects_one_workbook_and_does_not_ask_for_history() -> None:
    assert catalogue_url() == CATALOGUE_URL
    assert "includeHistory" not in catalogue_url()
    assert MAX_ATTEMPTS == 1
    html = '<a href="2026/2608chouki-1.xlsx">series</a><a href="2026/2608chouki-2.xlsx">other</a>'
    assert workbook_url_from_catalogue(html).endswith("/2026/2608chouki-1.xlsx")
    with pytest.raises(CaoMoClientError, match="found 0"):
        workbook_url_from_catalogue("<a href='https://example.com/a.xlsx'>x</a>")
    with pytest.raises(CaoMoClientError, match="found 2"):
        workbook_url_from_catalogue(
            '<a href="2026/2608chouki-1.xlsx">a</a><a href="2026/2609chouki-1.xlsx">b</a>',
        )
    with pytest.raises(CaoMoClientError, match="query"):
        workbook_url_from_catalogue('<a href="2026/2608chouki-1.xlsx?includeHistory=1">a</a>')


def test_excerpt_is_nominal_calendar_month_schema_v1() -> None:
    parsed = parse_cao_mo_workbook(FIXTURE.read_bytes(), retrieved_at=RETRIEVED)
    assert parsed.series_key == "private_ex_volatile"
    assert parsed.unit == UNIT_TEXT
    assert parsed.seasonal_adjustment == "seasonally adjusted"
    assert parsed.frequency == "monthly"
    assert parsed.calendar_basis == "calendar_month"
    assert parsed.vintage_class == "latest_revised"
    assert parsed.omitted_periods == ("2026-07",)
    assert len(parsed.observations) == 2
    for observation in parsed.observations:
        assert observation.schema_version == "1.0"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.availability_precision == AvailabilityPrecision.UNKNOWN
        assert observation.earliest_model_available_at is None
        assert observation.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        assert observation.frequency.value == "monthly"
        assert observation.geography == "JP"
        assert observation.unit == UNIT_TEXT
        assert observation.dataset_id == DATASET_ID
        assert observation.source_id == SOURCE_ID
        assert observation.provider_id == "cao"
        assert observation.raw_value == EXCERPT_VALUES[observation.period_start]
        assert observation.source_locator == CATALOGUE_URL
    stored = {row.raw_value for row in parsed.observations}
    assert "1" not in stored
    assert "999999999" not in stored


def test_blank_month_is_omitted_and_not_stored_as_zero() -> None:
    parsed = parse_cao_mo_workbook(FIXTURE.read_bytes(), retrieved_at=RETRIEVED)
    assert all(row.period_start != date(2026, 7, 1) for row in parsed.observations)
    assert all(row.raw_value != "0" for row in parsed.observations)


def test_missing_sheet_and_fiscal_label_fail(tmp_path: Path) -> None:
    missing = tmp_path / "missing.xlsx"
    write_workbook(missing, include_bound_sheet=False)
    result = _adapter(missing, RETRIEVED).fetch()
    assert result.errors[0].code == ProviderFailureCode.PARSE_FAILED
    assert "季調・月次" in result.errors[0].message
    fiscal = tmp_path / "fiscal.xlsx"
    write_workbook(fiscal, rows=(("4-3", "1", "10"),))
    fiscal_result = _adapter(fiscal, RETRIEVED).fetch()
    assert fiscal_result.observations == ()
    assert "fiscal-year" in fiscal_result.errors[0].message


def test_wrong_column_and_non_numeric_fail(tmp_path: Path) -> None:
    wrong = tmp_path / "wrong.xlsx"
    write_workbook(wrong, column_mark="(船舶を除く")
    wrong_result = _adapter(wrong, RETRIEVED).fetch()
    assert wrong_result.observations == ()
    assert "volatile" in wrong_result.errors[0].message
    bad = tmp_path / "bad.xlsx"
    write_workbook(bad, rows=(("2026", "8", "not-a-number"),))
    bad_result = _adapter(bad, RETRIEVED).fetch()
    assert bad_result.errors[0].code == ProviderFailureCode.PARSE_FAILED


def test_contradictory_values_are_not_treated_as_vintages(tmp_path: Path) -> None:
    path = tmp_path / "two.xlsx"
    write_workbook(
        path,
        rows=(("2026", "8", "1069778.74994"), ("2026", "8", "1069779")),
    )
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert "vintage panel" in result.errors[0].message


def test_missing_fixture_and_client_error(monkeypatch: pytest.MonkeyPatch) -> None:
    missing = CaoMoAdapter(
        config=CaoMoAdapterConfig(live=False, fixture_path=None),
        retrieved_at=RETRIEVED,
    ).fetch()
    assert missing.errors[0].code == ProviderFailureCode.FETCH_FAILED

    def _boom() -> tuple[bytes, int, str]:
        raise CaoMoClientError("Cabinet Office machinery orders returned HTTP 503")

    monkeypatch.setattr(
        "aqil_research.adapters.cao_mo_private_ex_volatile.adapter.fetch_workbook",
        _boom,
    )
    failed = CaoMoAdapter(config=CaoMoAdapterConfig(live=True), retrieved_at=RETRIEVED).fetch()
    assert failed.errors[0].code == ProviderFailureCode.FETCH_FAILED
    assert "503" in failed.errors[0].message


def test_second_fixture_ingest_reuses_observation_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _bind_memory(monkeypatch)
    adapter = _adapter(FIXTURE, RETRIEVED)
    first, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert first.outcome == "success"
    assert first.observations_newly_stored == 2
    assert psycopg.connect is _refuse_database
    first_ids = {row.period_start: row.observation_id for row in store.all_observations()}
    later = datetime(2026, 10, 25, 4, 0, tzinfo=UTC)
    adapter.prior_points = _points(store)
    adapter.retrieved_at = later
    second, _again = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert second.outcome == "unchanged"
    assert second.observations_newly_stored == 0
    assert {row.period_start: row.observation_id for row in store.all_observations()} == first_ids


def test_changed_value_is_a_new_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _bind_memory(monkeypatch)
    collect_registered_adapter(
        store_backend="memory",
        adapter=_adapter(FIXTURE, RETRIEVED),
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    original = next(
        row.observation_id
        for row in store.all_observations()
        if row.period_start == date(2026, 8, 1)
    )
    changed = tmp_path / "changed.xlsx"
    write_workbook(changed, rows=(("2026", "6", "1055761.7610599999"), ("2026", "8", "1069800")))
    later = datetime(2026, 10, 25, 4, 0, tzinfo=UTC)
    second, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=_adapter(changed, later, _points(store)),
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert second.observations_newly_stored == 1
    august = [row for row in store.all_observations() if row.period_start == date(2026, 8, 1)]
    assert {row.raw_value for row in august} == {"1069778.74994", "1069800"}
    assert any(row.observation_id == original for row in august)
