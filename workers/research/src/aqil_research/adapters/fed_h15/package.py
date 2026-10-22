"""Read one monthly series from the Board H.15 package."""

from __future__ import annotations

import calendar
import io
import zipfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from aqil_research.adapters.fed_h15.series import (
    DATASET_CODE,
    MONTHLY_FREQUENCY,
    ND_SENTINEL,
    SERIES_NAMESPACE,
    UNIT_CODE,
    H15Series,
)


class H15PackageError(ValueError):
    """The H.15 file did not repeat the monthly series description."""


@dataclass(frozen=True, slots=True)
class H15Row:
    period_start: date
    period_end: date
    value: str


@dataclass(frozen=True, slots=True)
class H15Extract:
    """Rows whose description was repeated by the downloaded file."""

    series: H15Series
    long_description: str
    frequency_code: str
    unit_code: str
    rows: tuple[H15Row, ...]
    omitted_periods: tuple[str, ...]

    @property
    def description_lines(self) -> tuple[str, str]:
        """The file lines that confirmed the preview code."""
        series_line = (
            f'SERIES_NAME="{self.series.series_name}" '
            f'FREQ="{self.frequency_code}" UNIT="{self.unit_code}"'
        )
        description_line = f"Long Description: {self.long_description}"
        return (series_line, description_line)


def read_h15_series(package: bytes, series: H15Series) -> H15Extract:
    """Return monthly observations for one series, or refuse to bind it."""
    handle, archive = _open_xml(package)
    try:
        try:
            return _read_open_xml(handle, series)
        except ET.ParseError as exc:
            raise H15PackageError("H.15 file is not XML") from exc
    finally:
        handle.close()
        if archive is not None:
            archive.close()


def _read_open_xml(root_source: io.BytesIO | zipfile.ZipExtFile, series: H15Series) -> H15Extract:
    dataset_id = ""
    frequency_code = ""
    unit_code = ""
    long_description = ""
    rows: list[H15Row] = []
    omitted: list[str] = []
    seen: set[date] = set()
    matched = False

    for event, element in ET.iterparse(root_source, events=("start", "end")):
        if event == "start" and _local(element.tag) == "DataSet":
            dataset_id = element.attrib.get("id", "")
            continue
        if event != "end" or _local(element.tag) != "Series":
            continue
        if element.attrib.get("SERIES_NAME") != series.series_name:
            element.clear()
            continue
        if matched:
            element.clear()
            raise H15PackageError(f"{series.series_name} appears more than once")
        matched = True
        _require_series_namespace(element, series)
        frequency_code = element.attrib.get("FREQ", "")
        unit_code = element.attrib.get("UNIT", "")
        long_description = _long_description(element)
        _require_binding(series, dataset_id, frequency_code, unit_code, long_description)
        for child in list(element):
            if _local(child.tag) != "Obs":
                continue
            period = child.attrib.get("TIME_PERIOD", "").strip()
            status = child.attrib.get("OBS_STATUS", "").strip()
            value = child.attrib.get("OBS_VALUE", "").strip()
            if _is_omitted(status, value):
                omitted.append(period or "(missing period)")
                continue
            parsed = _month_end(period)
            if parsed is None:
                omitted.append(period or "(missing period)")
                continue
            try:
                number = Decimal(value)
            except InvalidOperation as exc:
                element.clear()
                raise H15PackageError(f"{period} is not a decimal") from exc
            if not number.is_finite():
                element.clear()
                raise H15PackageError(f"{period} is not a finite rate")
            if parsed in seen:
                element.clear()
                raise H15PackageError(f"duplicate month {parsed.isoformat()}")
            seen.add(parsed)
            rows.append(H15Row(parsed, date.fromisoformat(period), value))
        element.clear()

    if not matched:
        raise H15PackageError(f"{series.series_name} was not in the H.15 package")
    if not rows:
        raise H15PackageError(f"{series.series_name} had no usable monthly observations")
    return H15Extract(
        series=series,
        long_description=long_description,
        frequency_code=frequency_code,
        unit_code=unit_code,
        rows=tuple(rows),
        omitted_periods=tuple(omitted),
    )


def _open_xml(package: bytes) -> tuple[io.BytesIO | zipfile.ZipExtFile, zipfile.ZipFile | None]:
    buffer = io.BytesIO(package)
    if not zipfile.is_zipfile(buffer):
        buffer.seek(0)
        return buffer, None
    buffer.seek(0)
    archive = zipfile.ZipFile(buffer)
    try:
        name = next(item for item in archive.namelist() if item.endswith("H15_data.xml"))
    except StopIteration as exc:
        archive.close()
        raise H15PackageError("H.15 package has no data file") from exc
    return archive.open(name), archive


def _require_series_namespace(element: ET.Element, series: H15Series) -> None:
    namespace = element.tag.partition("}")[0].removeprefix("{")
    if namespace != SERIES_NAMESPACE:
        raise H15PackageError(f"{series.series_name} is not in the H15_H15 schema")


def _require_binding(
    series: H15Series,
    dataset_id: str,
    frequency_code: str,
    unit_code: str,
    long_description: str,
) -> None:
    """Store nothing until the file repeats the monthly description."""
    if dataset_id != DATASET_CODE:
        raise H15PackageError(f"H.15 dataset id was {dataset_id or 'missing'}")
    if frequency_code != MONTHLY_FREQUENCY:
        raise H15PackageError(f"{series.series_name} is not the monthly frequency")
    if unit_code != UNIT_CODE:
        raise H15PackageError(f"{series.series_name} is not per cent per year")
    if _normalise(long_description) != series.long_description:
        raise H15PackageError(
            f"{series.series_name} description was not repeated by the H.15 file",
        )


def _long_description(element: ET.Element) -> str:
    for child in list(element):
        if _local(child.tag) != "Annotations":
            continue
        for note in list(child):
            kind = ""
            text = ""
            for part in list(note):
                if _local(part.tag) == "AnnotationType":
                    kind = (part.text or "").strip()
                elif _local(part.tag) == "AnnotationText":
                    text = part.text or ""
            if kind == "Long Description":
                return text.strip()
    return ""


def _is_omitted(status: str, value: str) -> bool:
    """ND is an omitted period. The Board sentinel -9999 is not a rate and not zero."""
    return status != "A" or value in {"", ND_SENTINEL}


def _month_end(value: str) -> date | None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    last_day = calendar.monthrange(parsed.year, parsed.month)[1]
    if parsed.day != last_day:
        return None
    return date(parsed.year, parsed.month, 1)


def _normalise(value: str) -> str:
    return " ".join(value.split())


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
