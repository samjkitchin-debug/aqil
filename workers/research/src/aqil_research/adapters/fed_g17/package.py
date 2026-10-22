"""Read one G.17 series from a Board preformatted package."""

from __future__ import annotations

import csv
import io
import re
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.fed_g17.parse import SERIES_ID, SERIES_NAME, is_omitted_token

_HEADER = (
    "Description:",
    "Unit:",
    "Multiplier:",
    "Currency:",
    "Unique Identifier:",
    "Series Name:",
)
_MONTH = re.compile(r"^\d{4}-\d{2}$")


class G17PackageError(ValueError):
    """The official package did not contain a usable series."""


def extract_total_index(text: str) -> dict[str, object]:
    """Return the seasonally adjusted total industrial production index only."""
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise G17PackageError("G.17 package has no header") from exc
    _require_header(header)
    matched: list[str] | None = None
    for row in reader:
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) != len(header):
            raise G17PackageError("G.17 series row length does not match the header")
        if row[4].strip() != SERIES_ID:
            continue
        matched = row
        break
    if matched is None:
        raise G17PackageError(f"{SERIES_ID} was not in the G.17 package")
    _require_confirmed_description(matched)
    observations, omitted = _cells(header, matched)
    if not observations:
        raise G17PackageError("no usable total industrial production observations")
    return {
        "series_id": SERIES_ID,
        "series_name": SERIES_NAME,
        "description": matched[0].strip(),
        "unit_label": matched[1].strip(),
        "observations": observations,
        "omitted_periods": omitted,
    }


def _require_header(header: list[str]) -> None:
    labels = tuple(cell.strip() for cell in header[:6])
    if labels != _HEADER:
        raise G17PackageError("G.17 package header does not match the Board series-row layout")
    if len(header) <= 6:
        raise G17PackageError("G.17 package has no period columns")
    for cell in header[6:]:
        period = cell.strip()
        if _MONTH.match(period) is None:
            raise G17PackageError(f"unexpected period column {period}")
        year_text, month_text = period.split("-")
        month = int(month_text)
        if int(year_text) < 1900 or month < 1 or month > 12:
            raise G17PackageError(f"unexpected period column {period}")


def _require_confirmed_description(row: list[str]) -> None:
    description = row[0].strip()
    unit = row[1].strip()
    multiplier = row[2].strip()
    series_name = row[5].strip()
    if series_name != SERIES_NAME:
        raise G17PackageError("series name does not match the bound G.17 code")
    if multiplier != "1":
        raise G17PackageError("G.17 multiplier is not 1")
    if not _description_confirms_total_index(description, unit):
        raise G17PackageError(
            "series text did not confirm a seasonally adjusted total industry index",
        )


def _description_confirms_total_index(description: str, unit: str) -> bool:
    folded = description.casefold()
    if "n.s.a" in folded or "not seasonally" in folded:
        return False
    seasonal = "s.a." in folded or "seasonally adjusted" in folded
    total = (
        "total industrial production" in folded
        or "total industry" in folded
        or (folded.startswith("total index") and "ip" in folded)
    )
    return seasonal and total and unit.casefold().startswith("index")


def _cells(
    header: list[str],
    row: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    observations: list[dict[str, str]] = []
    omitted: list[dict[str, str]] = []
    for label, raw in zip(header[6:], row[6:], strict=True):
        period = label.strip()
        token = raw.strip()
        if is_omitted_token(token):
            omitted.append({"period": period, "token": token})
            continue
        try:
            Decimal(token)
        except InvalidOperation as exc:
            raise G17PackageError(f"{period}: non-numeric value") from exc
        observations.append({"period": period, "value": token})
    return observations, omitted
