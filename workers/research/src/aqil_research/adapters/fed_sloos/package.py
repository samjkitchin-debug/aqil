"""Read one SLOOS series from the Board's official data package."""

from __future__ import annotations

import io
import zipfile
from datetime import date
from xml.etree import ElementTree as ET

from aqil_research.adapters.fed_sloos.parse import SERIES_ID

_QUARTER_ENDS = {
    (3, 31): 1,
    (6, 30): 2,
    (9, 30): 3,
    (12, 31): 4,
}


class SloosPackageError(ValueError):
    """The official package did not contain a usable series."""


def observations_from_package(package: bytes) -> list[dict[str, str]]:
    """Return period and value rows for SUBLPDCILS_N.Q only."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(package))
    except zipfile.BadZipFile as exc:
        raise SloosPackageError("SLOOS package is not a zip file") from exc
    try:
        xml_name = next(name for name in archive.namelist() if name.endswith("SLOOS_data.xml"))
    except StopIteration as exc:
        raise SloosPackageError("SLOOS package has no data file") from exc
    return _observations_from_xml(archive.read(xml_name))


def _observations_from_xml(body: bytes) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for _event, element in ET.iterparse(io.BytesIO(body), events=("end",)):
        name = _local_name(element.tag)
        if name == "Series":
            if element.attrib.get("SERIES_NAME") == SERIES_ID:
                rows = []
                for child in list(element):
                    if _local_name(child.tag) != "Obs":
                        continue
                    item = _observation(child)
                    if item is not None:
                        rows.append(item)
            element.clear()
    if not rows:
        raise SloosPackageError(f"{SERIES_ID} was not in the SLOOS package")
    return rows


def _observation(element: ET.Element) -> dict[str, str] | None:
    period = _quarter_label(element.attrib.get("TIME_PERIOD", ""))
    value = element.attrib.get("OBS_VALUE", "").strip()
    if period is None or not value:
        return None
    return {"period": period, "value": value}


def _quarter_label(value: str) -> str | None:
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError:
        return None
    quarter = _QUARTER_ENDS.get((parsed.month, parsed.day))
    if quarter is None:
        return None
    return f"{parsed.year}-Q{quarter}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
