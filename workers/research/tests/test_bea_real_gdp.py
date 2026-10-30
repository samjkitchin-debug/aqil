"""Table 1.1.6 line 1 is US real GDP. Euro-area GDP is a different dataset."""

from __future__ import annotations

import zipfile
from datetime import date
from io import BytesIO

import pytest

from aqil_research.adapters.bea_workbook import real_gross_domestic_product
from aqil_research.workflow.bea_factor_inputs import GDP_DATASET_ID

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def test_workbook_binds_line_1_account_a191rx() -> None:
    extracted = real_gross_domestic_product(_workbook())
    assert extracted.sheet_name == "T10106-Q"
    assert extracted.line_number == "1"
    assert extracted.account_code == "A191RX"
    assert extracted.line_label == "Gross domestic product"
    assert "Seasonally adjusted at annual rates" in extracted.unit_text
    assert "chained (2017) dollars" in extracted.unit_text
    assert extracted.published_on == date(2026, 10, 29)
    assert [(item.period_start, item.value) for item in extracted.quarters] == [
        (date(1947, 1, 1), "2182681"),
        (date(1947, 4, 1), "2176892"),
    ]
    assert GDP_DATASET_ID == "bea.nipa.T10106.A191RX"
    assert "EA21" not in GDP_DATASET_ID
    assert GDP_DATASET_ID != "eurostat.namq_10_gdp.Q.CLV_I15.SCA.B1GQ.EA21"


def test_wrong_account_code_does_not_bind() -> None:
    with pytest.raises(ValueError, match="A191RX"):
        real_gross_domestic_product(_workbook(account="W875RX"))


def _workbook(account: str = "A191RX") -> bytes:
    rows = [
        ["Table 1.1.6. Real Gross Domestic Product, Chained Dollars"],
        ["[Millions of chained (2017) dollars] Seasonally adjusted at annual rates"],
        ["Quarterly data from 1947Q1 to 1947Q2"],
        ["Bureau of Economic Analysis"],
        ["Data published October 29, 2026"],
        [],
        [],
        ["Line", "", "", "1947Q1", "1947Q2"],
        ["1", "    Gross domestic product", account, "2182681", "2176892"],
    ]
    shared: list[str] = []
    index: dict[str, int] = {}

    def shared_index(value: str) -> str:
        if value not in index:
            index[value] = len(shared)
            shared.append(value)
        return str(index[value])

    cells: list[str] = []
    for row_number, row in enumerate(rows, start=1):
        for column, value in enumerate(row, start=1):
            if value == "":
                continue
            ref = f"{_column(column)}{row_number}"
            cells.append(f'<c r="{ref}" t="s"><v>{shared_index(value)}</v></c>')
        if row:
            # row wrapper is unnecessary; cells carry their own references
            pass
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<worksheet xmlns="{NS}"><sheetData>'
        + "".join(f"<row>{cell}</row>" for cell in cells)
        + "</sheetData></worksheet>"
    )
    strings = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<sst xmlns="{NS}">'
        + "".join(f"<si><t>{_xml(item)}</t></si>" for item in shared)
        + "</sst>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<workbook xmlns="{NS}" xmlns:r="{REL}">'
        '<sheets><sheet name="T10106-Q" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{PKG}">'
        '<Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("xl/workbook.xml", workbook)
        book.writestr("xl/_rels/workbook.xml.rels", rels)
        book.writestr("xl/sharedStrings.xml", strings)
        book.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


def _column(number: int) -> str:
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _xml(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
