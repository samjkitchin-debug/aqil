"""Read one H.8 series from the Board data package.

B1001NCBAM carries the same short description at a monthly frequency. This
reader keeps only weekly B1001NCBA and does not resample either series.
"""

from __future__ import annotations

import io
import zipfile
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from aqil_research.adapters.fed_h8.parse import (
    EXPECTED_DESCRIPTION,
    SERIES_ID,
    WEEKLY_WEDNESDAY_CODE,
)

_MISSING_TOKENS = frozenset({"", "ND", "NA", "NC", "N.A.", "N/A", "."})
_MISSING_STATUS = frozenset({"ND", "NA", "NC"})


class H8PackageError(ValueError):
    """The official package did not contain the bound bank-credit series."""


def series_from_h8_bytes(body: bytes) -> dict[str, object]:
    """Return the weekly bank-credit series from a zip package or an XML excerpt."""
    if body.startswith(b"PK"):
        try:
            archive = zipfile.ZipFile(io.BytesIO(body))
        except zipfile.BadZipFile as exc:
            raise H8PackageError("H.8 package is not a zip file") from exc
        names = [name for name in archive.namelist() if name.endswith("H8_data.xml")]
        if len(names) != 1:
            raise H8PackageError("H.8 package has no data file")
        with archive.open(names[0]) as handle:
            return _series_from_stream(handle)
    if not body.lstrip().startswith(b"<"):
        raise H8PackageError("H.8 payload is neither a zip package nor XML")
    return _series_from_stream(io.BytesIO(body))


def _series_from_stream(handle: io.BufferedIOBase) -> dict[str, object]:
    for _event, element in ET.iterparse(handle, events=("end",)):
        if _local_name(element.tag) != "Series":
            continue
        if element.attrib.get("SERIES_NAME") != SERIES_ID:
            element.clear()
            continue
        payload = _bound_series(element)
        element.clear()
        return payload
    raise H8PackageError(f"{SERIES_ID} was not in the H.8 package")


def _bound_series(element: ET.Element) -> dict[str, object]:
    description = _short_description(element)
    if description != EXPECTED_DESCRIPTION:
        raise H8PackageError(
            f"{SERIES_ID} description was {description!r}, not the bank-credit line",
        )
    _require_attribute(element, "FREQ", WEEKLY_WEDNESDAY_CODE)
    _require_attribute(element, "SA", "SA")
    _require_attribute(element, "UNIT_MULT", "1000000")
    _require_attribute(element, "CURRENCY", "USD")
    _require_attribute(element, "UNIT", "Currency")
    _require_attribute(element, "H8_UNITS", "LEVEL")
    _require_attribute(element, "BG", "CB")
    _require_attribute(element, "ITEM", "1001")

    rows: list[dict[str, str]] = []
    omitted: list[str] = []
    for child in list(element):
        if _local_name(child.tag) != "Obs":
            continue
        period = child.attrib.get("TIME_PERIOD", "").strip()
        if not period:
            continue
        value = child.attrib.get("OBS_VALUE", "").strip()
        status = child.attrib.get("OBS_STATUS", "").strip().upper()
        if _is_missing(value, status):
            omitted.append(period)
            continue
        rows.append({"period": period, "value": value})
    if not rows:
        raise H8PackageError(f"{SERIES_ID} had no numeric observations")
    return {
        "series_id": SERIES_ID,
        "description": description,
        "observations": rows,
        "omitted_periods": omitted,
    }


def _is_missing(value: str, status: str) -> bool:
    if status in _MISSING_STATUS or value.upper() in _MISSING_TOKENS:
        return True
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return True
    return not parsed.is_finite()


def _short_description(element: ET.Element) -> str:
    for node in element.iter():
        if _local_name(node.tag) != "Annotation":
            continue
        kind = ""
        text = ""
        for part in list(node):
            name = _local_name(part.tag)
            if name == "AnnotationType":
                kind = (part.text or "").strip()
            elif name == "AnnotationText":
                text = (part.text or "").strip()
        if kind == "Short Description":
            return text
    return ""


def _require_attribute(element: ET.Element, name: str, expected: str) -> None:
    actual = element.attrib.get(name, "")
    if actual != expected:
        raise H8PackageError(f"{SERIES_ID} {name} was {actual!r}, expected {expected}")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
