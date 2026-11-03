"""BEA real GDP growth vintages. Excerpt rows are copied from the 3 November 2026 workbook.

The dotted cell is synthetic and is only there to prove an unpublished estimate is skipped.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from aqil_research.adapters.bea_gdp_vintage.ingest import (
    VintageIngestError,
    assert_local_research_database,
    observations_from_points,
)
from aqil_research.adapters.bea_gdp_vintage.parse import (
    DATASET_ID,
    VintageWorkbookError,
    parse_real_gdp_vintage_workbook,
    series_checksum,
)
from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    SeriesProvenance,
    model_available_at,
)
from aqil_research.discovery.guards import LeakageError, recorded_series_class
from aqil_research.methods.registry import default_method_registry
from aqil_research.vintages.asof import select_as_of_series
from aqil_research.vintages.store import InMemoryObservationStore
from fixtures.observation_factory import make_observation

RETRIEVED = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)


def _workbook(rows: list[list[str | None]]) -> bytes:
    shared: list[str] = []
    index: dict[str, int] = {}

    def sid(value: str) -> int:
        if value not in index:
            index[value] = len(shared)
            shared.append(value)
        return index[value]

    sheet_rows: list[str] = []
    for row_number, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column, value in enumerate(row, start=1):
            if value is None:
                continue
            letter = chr(64 + column)
            cells.append(f'<c r="{letter}{row_number}" t="s"><v>{sid(value)}</v></c>')
        sheet_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    shared_xml = "".join(f"<si><t>{escape(value)}</t></si>" for value in shared)
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    shared_doc = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"{shared_xml}</sst>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Vintage History" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    package = "http://schemas.openxmlformats.org/package/2006/relationships"
    sheet_type = "application/vnd.openxmlformats-officedocument.spreadsheetml."
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{package}">'
        f'<Relationship Id="rId1" Type="{office}worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        f'<Relationship Id="rId2" Type="{office}sharedStrings" '
        'Target="sharedStrings.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/xl/workbook.xml" ContentType="{sheet_type}sheet.main+xml"/>'
        f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{sheet_type}worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        f'ContentType="{sheet_type}sharedStrings+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{package}">'
        f'<Relationship Id="rId1" Type="{office}officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as book:
        book.writestr("[Content_Types].xml", content_types)
        book.writestr("_rels/.rels", root_rels)
        book.writestr("xl/workbook.xml", workbook)
        book.writestr("xl/_rels/workbook.xml.rels", rels)
        book.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        book.writestr("xl/sharedStrings.xml", shared_doc)
    return buffer.getvalue()


def _excerpt() -> bytes:
    return _workbook(
        [
            ["Last Updated October 29, 2026"],
            [
                "Estimates of real growth rates by publication (or vintage) date. "
                "Copied excerpt, not the full workbook."
            ],
            ["2026Q3"],
            [None, "Vintage", "GDP", "GDI", "Real GDP", "Real GDI", "Release Date"],
            [
                None,
                "Advance",
                "33,010.0",
                ".....",
                "3.4",
                ".....",
                "Oct 29, 2026 GDI not published",
            ],
            ["2026Q2"],
            [None, "Third", "32,563.0", "32,752.5", "2.2", "2.6", "Sep 30, 2026"],
            [None, "Second", "32,486.1", "32,245.1", "1.5", "2.2", "Aug 26, 2026"],
            [
                None,
                "Advance",
                "32,475.2",
                ".....",
                "1.5",
                ".....",
                "Jul 30, 2026 GDI not published",
            ],
            ["2002Q1"],
            [
                None,
                "Advance",
                "10,431.3",
                ".....",
                "5.8",
                ".....",
                "Apr 26, 2002  GDI not published",
            ],
            [None, "Final", "10,449.8", "10,621.1", ".....", ".....", "Jun 27, 2002"],
        ]
    )


def test_excerpt_keeps_printed_real_gdp_vintages_and_skips_dots() -> None:
    parsed = parse_real_gdp_vintage_workbook(_excerpt())
    assert parsed.updated_on is not None
    assert parsed.updated_on.isoformat() == "2026-10-29"
    assert parsed.skipped_unpublished == 1
    assert [
        (point.quarter_label, point.vintage_label, point.raw_value) for point in parsed.points
    ] == [
        ("2026Q3", "Advance", "3.4"),
        ("2026Q2", "Third", "2.2"),
        ("2026Q2", "Second", "1.5"),
        ("2026Q2", "Advance", "1.5"),
        ("2002Q1", "Advance", "5.8"),
    ]
    assert parsed.points[0].period_start.isoformat() == "2026-07-01"
    assert parsed.points[0].period_end.isoformat() == "2026-09-30"
    assert series_checksum(parsed.points)


def test_as_of_uses_only_the_vintage_known_on_the_decision_date() -> None:
    parsed = parse_real_gdp_vintage_workbook(_excerpt())
    rows = observations_from_points(parsed.points, retrieved_at=RETRIEVED)
    advance = next(row for row in rows if row.period_start.isoformat() == "2026-07-01")
    assert advance.series_provenance == SeriesProvenance.PROVIDER_VINTAGE
    assert advance.availability_precision == AvailabilityPrecision.DATE
    assert advance.earliest_model_available_at is None
    available = model_available_at(advance)
    assert available == datetime(2026, 10, 30, tzinfo=UTC)

    before = select_as_of_series(
        rows,
        DATASET_ID,
        datetime(2026, 10, 29, 23, 0, tzinfo=UTC),
        AnalysisMode.POINT_IN_TIME,
    )
    assert "2026-07-01" not in {item.isoformat() for item in before}
    after = select_as_of_series(
        rows,
        DATASET_ID,
        datetime(2026, 10, 30, tzinfo=UTC),
        AnalysisMode.POINT_IN_TIME,
    )
    assert after[advance.period_start].raw_value == "3.4"

    second_day = datetime(2026, 8, 27, tzinfo=UTC)
    selected = select_as_of_series(rows, DATASET_ID, second_day, AnalysisMode.POINT_IN_TIME)
    quarter = next(
        row.period_start for row in rows if row.provider_vintage_date.isoformat() == "2026-08-26"
    )
    assert selected[quarter].raw_value == "1.5"
    assert selected[quarter].provider_vintage_date.isoformat() == "2026-08-26"
    third_day = datetime(2026, 10, 1, tzinfo=UTC)
    revised = select_as_of_series(rows, DATASET_ID, third_day, AnalysisMode.POINT_IN_TIME)
    assert revised[quarter].raw_value == "2.2"

    early = select_as_of_series(
        rows,
        DATASET_ID,
        datetime(2002, 4, 26, 23, 0, tzinfo=UTC),
        AnalysisMode.POINT_IN_TIME,
    )
    assert early == {}


def test_point_in_time_rejects_a_later_vintage_and_a_latest_revised_row() -> None:
    parsed = parse_real_gdp_vintage_workbook(_excerpt())
    rows = observations_from_points(parsed.points, retrieved_at=RETRIEVED)
    leaked = rows[0].model_copy(
        update={
            "observation_id": "future-leak",
            "raw_value": "9.9",
            "provider_vintage_date": date(2026, 12, 1),
            "source_release_at": datetime(2026, 12, 1, tzinfo=UTC),
            "retrieved_at": datetime(2026, 12, 2, tzinfo=UTC),
            "first_seen_at": datetime(2026, 12, 2, tzinfo=UTC),
        }
    )
    selected = select_as_of_series(
        rows + (leaked,),
        DATASET_ID,
        datetime(2026, 10, 30, tzinfo=UTC),
        AnalysisMode.POINT_IN_TIME,
    )
    assert selected[rows[0].period_start].raw_value == "3.4"
    assert (
        recorded_series_class(
            rows,
            DATASET_ID,
            datetime(2026, 10, 30, tzinfo=UTC),
            AnalysisMode.POINT_IN_TIME,
        )
        == "point_in_time"
    )
    latest = make_observation(
        period_start=rows[0].period_start,
        raw_value="8.8",
        provider_vintage_date=rows[0].provider_vintage_date,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        observation_id="latest-revised-gdp",
    ).model_copy(update={"dataset_id": DATASET_ID})
    with pytest.raises(LeakageError, match="latest_revised"):
        recorded_series_class(
            rows + (latest,),
            DATASET_ID,
            datetime(2026, 10, 30, tzinfo=UTC),
            AnalysisMode.POINT_IN_TIME,
        )


def test_repeat_import_is_unchanged_and_a_changed_value_conflicts() -> None:
    parsed = parse_real_gdp_vintage_workbook(_excerpt())
    rows = observations_from_points(parsed.points, retrieved_at=RETRIEVED)
    store = InMemoryObservationStore()
    first = store.append_many(rows)
    second = store.append_many(rows)
    assert first.inserted == len(rows)
    assert second.unchanged == len(rows)
    changed = rows[0].model_copy(update={"raw_value": "9.1", "observation_id": "conflict-row"})
    with pytest.raises(Exception, match="conflicting value"):
        store.append(changed)


def test_malformed_real_gdp_cell_is_rejected() -> None:
    payload = _workbook(
        [
            ["Last Updated October 29, 2026"],
            ["Estimates by publication date."],
            ["2026Q3"],
            [None, "Advance", "1", ".....", "not-a-number", ".....", "Oct 29, 2026"],
        ]
    )
    with pytest.raises(VintageWorkbookError, match="not a decimal"):
        parse_real_gdp_vintage_workbook(payload)


def test_two_values_on_one_release_date_are_rejected() -> None:
    payload = _workbook(
        [
            ["Last Updated October 29, 2026"],
            ["Estimates by publication date."],
            ["2026Q2"],
            [None, "Second", "1", "1", "1.5", "1", "Aug 26, 2026"],
            [None, "Other", "1", "1", "2.2", "1", "Aug 26, 2026"],
        ]
    )
    with pytest.raises(VintageWorkbookError, match="two different"):
        parse_real_gdp_vintage_workbook(payload)


def test_no_registered_method_depends_on_this_vintage() -> None:
    for method in default_method_registry().registered():
        assert DATASET_ID not in method.required_dataset_ids()


def test_import_refuses_a_database_that_is_not_local_postgres() -> None:
    with pytest.raises(VintageIngestError, match="loopback"):
        assert_local_research_database("postgresql://research_worker@127.0.0.1:5432/postgres")
    with pytest.raises(VintageIngestError, match="postgres"):
        assert_local_research_database("postgresql://research_worker@127.0.0.1:55432/aqil_etf")
