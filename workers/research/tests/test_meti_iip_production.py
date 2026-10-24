"""METI production: rights, schema 1.0, omitted gaps, and a second ingest that adds nothing."""

from __future__ import annotations

import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

import aqil_research.adapters.meti_iip_production.adapter as adapter_module
import aqil_research.adapters.meti_iip_production.client as client_module
from aqil_research.adapters.meti_iip_production.adapter import (
    MetiIipProductionAdapter,
    MetiIipProductionAdapterConfig,
)
from aqil_research.adapters.meti_iip_production.client import (
    MetiIipClientError,
    fetch_workbook,
    series_request_headers,
    series_workbook_url,
)
from aqil_research.adapters.meti_iip_production.constants import (
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    SERIES_KEY,
    SERIES_NAME,
    SHEET_NAME,
    SOURCE_ID,
    TITLE,
    UNIT_TEXT,
    WEIGHT_TEXT,
)
from aqil_research.adapters.meti_iip_production.parse import parse_meti_iip_workbook
from aqil_research.adapters.meti_iip_production.stability import StoredMetiPoint
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.census_adv_orders import CensusAdvOrdersMethod
from aqil_research.methods.credit_standards_volumes import CreditStandardsVolumesMethod
from aqil_research.methods.industrial_production_activity import (
    IndustrialProductionActivityMethod,
)
from aqil_research.methods.labour_market import LabourMarketConditionsMethod
from aqil_research.methods.macro_conditions import MacroConditionsMethod
from aqil_research.methods.prices_and_policy import PricesAndPolicyMethod
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.methods.sloos_cil import SloosCilMethod
from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsDecision,
    load_source_rights,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "meti_iip" / "b2020_gsm1_kogyo_excerpt.xlsx"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "meti_iip_production_sa.csv"
)
RETRIEVED = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
EXCERPT_VALUES = {
    date(2026, 5, 1): "102.6",
    date(2026, 6, 1): "104.6",
    date(2026, 7, 1): "104.4",
    date(2026, 8, 1): "101.9",
}
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def _collapsed(value: str) -> str:
    return " ".join(value.split())


def _refuse_database(*args: object, **kwargs: object) -> None:
    raise AssertionError(f"database connection is not allowed: {args!r} {kwargs!r}")


def _bind_memory(monkeypatch: pytest.MonkeyPatch) -> InMemoryObservationStore:
    monkeypatch.setattr("psycopg.connect", _refuse_database)
    records = load_source_rights(FRAGMENT)
    # The fragment stays disabled. This copy lets the offline parser tests run.
    enabled = (records[0].model_copy(update={"operational_status": OperationalStatus.ENABLED}),)
    monkeypatch.setattr(
        "aqil_research.collection.service.load_source_rights",
        lambda path=None: enabled,
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
    prior: tuple[StoredMetiPoint, ...] = (),
) -> MetiIipProductionAdapter:
    return MetiIipProductionAdapter(
        config=MetiIipProductionAdapterConfig(live=False, fixture_path=path),
        retrieved_at=retrieved_at,
        prior_points=prior,
    )


def _points(store: InMemoryObservationStore) -> tuple[StoredMetiPoint, ...]:
    return tuple(
        StoredMetiPoint(
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


def _column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _cell(ref: str, value: str, *, number: bool) -> str:
    if number:
        return f'<c r="{ref}"><v>{value}</v></c>'
    escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<c r="{ref}" t="inlineStr"><is><t>{escaped}</t></is></c>'


def _write_workbook(
    path: Path,
    columns: list[tuple[str, str, str | None]],
    *,
    title: str = TITLE,
    sheet_name: str = SHEET_NAME,
    item_key: str = SERIES_KEY,
    item_name: str = SERIES_NAME,
    weight: str = WEIGHT_TEXT,
) -> None:
    """Write the production-sheet layout. A missing value is an omitted month."""
    rows: list[str] = []

    def add(row_number: int, cells: list[str]) -> None:
        rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')

    add(1, [_cell("A1", title, number=False)])
    code_cells = [_cell("C2", "時系列コード", number=False)]
    header_cells = [
        _cell("A3", "品目番号", number=False),
        _cell("B3", "品目名称", number=False),
        _cell("C3", "付加生産ウエイト", number=False),
    ]
    value_cells = [
        _cell("A4", item_key, number=False),
        _cell("B4", item_name, number=False),
        _cell("C4", weight, number=True),
    ]
    other_cells = [
        _cell("A5", "1100000000", number=False),
        _cell("B5", "製造工業", number=False),
        _cell("C5", "9983.5", number=True),
    ]
    for offset, (header, code, value) in enumerate(columns, start=4):
        letter = _column_letter(offset)
        code_cells.append(_cell(f"{letter}2", code, number=False))
        header_cells.append(_cell(f"{letter}3", header, number=False))
        if value is not None:
            value_cells.append(_cell(f"{letter}4", value, number=True))
            other_cells.append(_cell(f"{letter}5", "1.0", number=True))
    add(2, code_cells)
    add(3, header_cells)
    add(4, value_cells)
    add(5, other_cells)
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{NS}">'
        f"<sheetData>{''.join(rows)}</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{NS}" xmlns:r="{REL}">'
        f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


def _excerpt_columns() -> list[tuple[str, str, str | None]]:
    return [
        ("202605", "2026000505", "102.6"),
        ("202606", "2026000606", "104.6"),
        ("202607", "2026000707", "104.4"),
        ("202608", "2026000808", "101.9"),
    ]


def test_rights_fragment_clears_first_live_use() -> None:
    records = load_source_rights(FRAGMENT)
    assert len(records) == 1
    record = records[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.series_or_dataset_code == SERIES_KEY
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.operational_status == OperationalStatus.DISABLED
    blocked_text = f"{record.conditions} {record.evidence_note}".lower()
    assert "technically blocked" in blocked_text
    assert "http 403" in blocked_text
    assert record.attribution == AttributionRequirement.REQUIRED
    assert record.ai_processing == RightsDecision.UNKNOWN
    assert record.ai_model_training == RightsDecision.UNKNOWN
    assert record.assessed_on.isoformat() == "2026-10-24"
    assert record.terms_url in record.evidence_urls
    assert record.terms_url.startswith("https://")
    assert record.access_url.startswith("https://")
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED
    assert TITLE in record.evidence_note
    assert "latest-revised" in record.evidence_note
    assert "not a historical vintage panel" in record.evidence_note
    assert "2018-01" in record.evidence_note
    assert "2026-08" in record.evidence_note
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(record.evidence_note)
    assert "fiscal-year" in record.evidence_note
    assert "value-added" in record.evidence_note


def test_adapter_documents_method_compatibility() -> None:
    text = adapter_module.__doc__ or ""
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(text)
    assert "1000000000" in text
    assert SahmAnalyticalMethod().required_dataset_ids() == ("bls.ln.LNS14000000",)
    assert LabourMarketConditionsMethod().required_dataset_ids() == (
        "bls.ln.LNS14000000",
        "bls.ce.CES0000000001",
        "bls.jt.JTS000000000000000JOL",
    )
    assert PricesAndPolicyMethod().required_dataset_ids() == (
        "bls.cu.CUSR0000SA0",
        "fed.h15.RIFSPFF_N.M",
        "fed.h15.RIFLGFCY10_N.M",
    )
    assert IndustrialProductionActivityMethod().required_dataset_ids() == ("fed.g17.IP.B50001.S",)
    assert CreditStandardsVolumesMethod().required_dataset_ids() == (
        "fed.sloos.SUBLPDCILS_N.Q",
        "fed.h8.B1001NCBA",
    )
    assert SloosCilMethod().required_dataset_ids() == ("fed.sloos.SUBLPDCILS_N.Q",)
    assert CensusAdvOrdersMethod().required_dataset_ids() == ("census.m3.adv.MDM.NO",)
    assert MacroConditionsMethod().required_dataset_ids() == (
        "bls.ln.LNS14000000",
        "fed.sloos.SUBLPDCILS_N.Q",
        "census.m3.adv.MDM.NO",
    )
    for method in (
        SahmAnalyticalMethod(),
        LabourMarketConditionsMethod(),
        PricesAndPolicyMethod(),
        IndustrialProductionActivityMethod(),
        CreditStandardsVolumesMethod(),
        SloosCilMethod(),
        CensusAdvOrdersMethod(),
        MacroConditionsMethod(),
    ):
        assert DATASET_ID not in method.required_dataset_ids()


def test_request_does_not_ask_for_history() -> None:
    url = series_workbook_url()
    assert url == "https://www.meti.go.jp/statistics/tyo/iip/xls/b2020_gsm1j.xlsx"
    assert "includeHistory" not in url
    assert series_request_headers()["User-Agent"].startswith("AqilResearch/")


def test_client_refuses_another_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "ACCESS_URL", "https://example.com/b2020_gsm1j.xlsx")
    with pytest.raises(MetiIipClientError, match="host"):
        fetch_workbook()


def test_excerpt_is_latest_revised_schema_v1() -> None:
    parsed = parse_meti_iip_workbook(FIXTURE.read_bytes(), retrieved_at=RETRIEVED)
    assert parsed.series_key == SERIES_KEY
    assert parsed.compiler_sentence == TITLE
    assert parsed.unit == UNIT_TEXT
    assert parsed.seasonal_adjustment == "Seasonally adjusted"
    assert parsed.frequency == "Monthly"
    assert parsed.vintage_class == "latest_revised"
    assert parsed.omitted_periods == ()
    assert len(parsed.observations) == 4
    for observation in parsed.observations:
        assert observation.schema_version == "1.0"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.availability_precision == AvailabilityPrecision.UNKNOWN
        assert observation.earliest_model_available_at is None
        assert observation.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        assert observation.unit == UNIT_TEXT
        assert observation.frequency.value == "monthly"
        assert observation.geography == "JP"
        assert observation.raw_value == EXCERPT_VALUES[observation.period_start]
        assert observation.dataset_id == DATASET_ID
    periods = [row.period_start for row in parsed.observations]
    assert periods == sorted(EXCERPT_VALUES)


def test_blank_month_is_omitted_and_not_stored_as_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "gap.xlsx"
    columns = _excerpt_columns()
    columns[2] = ("202607", "2026000707", None)
    _write_workbook(path, columns)
    parsed = parse_meti_iip_workbook(path.read_bytes(), retrieved_at=RETRIEVED)
    assert parsed.omitted_periods == ("2026-07-01",)
    assert all(row.period_start != date(2026, 7, 1) for row in parsed.observations)
    assert all(row.raw_value != "0" for row in parsed.observations)
    store = _bind_memory(monkeypatch)
    result, bound = collect_registered_adapter(
        store_backend="memory",
        adapter=_adapter(path, RETRIEVED),
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert bound is store
    assert result.outcome == "success"
    assert result.observations_received == 3
    assert result.observations_newly_stored == 3
    assert result.retrieval_id is None
    assert {row.period_start for row in store.all_observations()} == {
        date(2026, 5, 1),
        date(2026, 6, 1),
        date(2026, 8, 1),
    }


def test_other_item_and_fiscal_year_are_refused(tmp_path: Path) -> None:
    other = tmp_path / "other.xlsx"
    _write_workbook(other, _excerpt_columns(), item_name="製造工業")
    result = _adapter(other, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors
    assert "refusing" in result.errors[0].message

    fiscal = tmp_path / "fiscal.xlsx"
    _write_workbook(fiscal, [("2025FY", "2025FY", "100.0")])
    fiscal_result = _adapter(fiscal, RETRIEVED).fetch()
    assert fiscal_result.observations == ()
    assert fiscal_result.errors
    assert "fiscal-year" in fiscal_result.errors[0].message

    shipments = tmp_path / "ship.xlsx"
    _write_workbook(shipments, _excerpt_columns(), sheet_name="出荷")
    shipment_result = _adapter(shipments, RETRIEVED).fetch()
    assert shipment_result.observations == ()
    assert shipment_result.errors
    assert "shipments" in shipment_result.errors[0].message


def test_contradictory_values_are_not_treated_as_vintages(tmp_path: Path) -> None:
    path = tmp_path / "two.xlsx"
    _write_workbook(
        path,
        [
            ("202608", "2026000808", "101.9"),
            ("202608", "2026000808", "102.5"),
        ],
    )
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors
    assert "vintage panel" in result.errors[0].message


def test_second_fixture_ingest_inserts_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _bind_memory(monkeypatch)
    adapter = _adapter(FIXTURE, RETRIEVED)
    first, bound = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert bound is store
    assert first.outcome == "success"
    assert first.source_id == SOURCE_ID
    assert first.dataset_id == DATASET_ID
    assert first.data_provenance == "latest_revised"
    assert first.observations_received == 4
    assert first.observations_newly_stored == 4
    assert first.retrieval_id is None
    assert psycopg_is_blocked()
    metadata = adapter.last_parse
    assert metadata is not None
    assert metadata.compiler_sentence == TITLE
    assert metadata.vintage_class == "latest_revised"
    assert metadata.omitted_periods == ()
    first_ids = {row.period_start: row.observation_id for row in store.all_observations()}

    later = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
    adapter.prior_points = _points(store)
    adapter.retrieved_at = later
    second, again = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert again is store
    assert second.outcome == "unchanged"
    assert second.observations_newly_stored == 0
    assert second.observations_unchanged == 4
    assert len(store.all_observations()) == 4
    assert {row.period_start: row.observation_id for row in store.all_observations()} == first_ids


def psycopg_is_blocked() -> bool:
    import psycopg

    return psycopg.connect is _refuse_database


def test_changed_value_is_a_new_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _bind_memory(monkeypatch)
    adapter = _adapter(FIXTURE, RETRIEVED)
    collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    kept = {
        row.period_start: row.observation_id
        for row in store.all_observations()
        if row.period_start != date(2026, 8, 1)
    }
    original_august = next(
        row.observation_id
        for row in store.all_observations()
        if row.period_start == date(2026, 8, 1)
    )
    changed = tmp_path / "changed.xlsx"
    columns = _excerpt_columns()
    columns[3] = ("202608", "2026000808", "102.0")
    _write_workbook(changed, columns)
    later = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
    follow_up = _adapter(changed, later, _points(store))
    second, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=follow_up,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert second.observations_newly_stored == 1
    assert second.observations_unchanged == 3
    august = [row for row in store.all_observations() if row.period_start == date(2026, 8, 1)]
    assert len(august) == 2
    revised = next(row for row in august if row.raw_value == "102.0")
    assert revised.observation_id != original_august
    assert any(row.observation_id == original_august for row in august)
    for period_start, observation_id in kept.items():
        match = next(row for row in store.all_observations() if row.period_start == period_start)
        assert match.observation_id == observation_id
        assert match.raw_value == EXCERPT_VALUES[period_start]
