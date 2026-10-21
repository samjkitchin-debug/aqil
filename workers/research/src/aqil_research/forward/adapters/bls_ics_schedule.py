"""Parse the official BLS selected-release iCalendar feed.

The HTML schedule states that calendar times are Eastern Time. The feed at
https://www.bls.gov/schedule/news_release/bls.ics is the primary adapter.
Zulu timestamps in the feed are stored as absolute instants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

SOURCE_ID = "bls_ics_schedule"
DATASET_ID = "forward.bls.selected_releases.schedule"
SOURCE_LOCATOR = "https://www.bls.gov/schedule/news_release/bls.ics"
CALENDAR_TIMEZONE = "America/New_York"


@dataclass(frozen=True, slots=True)
class BlsIcsRelease:
    uid: str
    summary: str
    starts_at: datetime
    status: str
    stamp_basis: str


def parse_bls_ics(text: str) -> list[BlsIcsRelease]:
    releases: list[BlsIcsRelease] = []
    for block in _event_blocks(_unfold(text)):
        fields = _fields(block)
        uid = fields.get("UID", "").strip()
        summary = fields.get("SUMMARY", "").strip()
        start_line = _line_named(block, "DTSTART")
        if not uid or not summary or start_line is None:
            continue
        parsed = _parse_dtstart_line(start_line)
        if parsed is None:
            continue
        starts_at, stamp_basis = parsed
        status = fields.get("STATUS", "").strip()
        releases.append(
            BlsIcsRelease(
                uid=uid,
                summary=summary,
                starts_at=starts_at,
                status=status or "CONFIRMED",
                stamp_basis=stamp_basis,
            ),
        )
    return releases


def release_event_id(release: BlsIcsRelease) -> str:
    return f"event:verified:bls:ics:{release.uid}"


def release_to_catalyst_payload(
    release: BlsIcsRelease,
    *,
    retrieved_at: datetime,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": release_event_id(release),
        "category": _category(release.summary),
        "subject_type": "economic_release",
        "subject_id": f"dataset:bls:ics:{release.uid}",
        "title": release.summary,
        "scheduled_at": release.starts_at.astimezone(UTC).isoformat(),
        "timezone": CALENDAR_TIMEZONE,
        "date_precision": "confirmed",
        "status": "scheduled" if release.status.upper() == "CONFIRMED" else "tentative",
        "source_id": SOURCE_ID,
        "source_locator": SOURCE_LOCATOR,
        "evidence_class": "verified_schedule",
        "feed_stamp_basis": release.stamp_basis,
        "calendar_timezone_note": "BLS HTML schedule states all times are Eastern Time.",
        "retrieved_at": retrieved_at.isoformat(),
        "is_fixture": False,
    }


def _category(summary: str) -> str:
    lowered = summary.lower()
    if "employment situation" in lowered:
        return "us_employment_report"
    if "consumer price" in lowered or "producer price" in lowered:
        return "us_inflation_report"
    return "us_labor_release"


def _unfold(text: str) -> str:
    return re.sub(r"\r?\n[ \t]", "", text.replace("\r\n", "\n"))


def _event_blocks(text: str) -> list[str]:
    return re.findall(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", text, flags=re.S)


def _fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in block.split("\n"):
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        key = name.split(";", 1)[0].upper()
        fields[key] = value.replace("\\,", ",").replace("\\n", " ")
    return fields


_EASTERN = ZoneInfo("America/New_York")
_TZID_ZONES = {
    "US-EASTERN": _EASTERN,
    "AMERICA/NEW_YORK": _EASTERN,
}


def _line_named(block: str, name: str) -> str | None:
    prefix = f"{name.upper()}"
    for line in block.split("\n"):
        head = line.split(":", 1)[0].split(";", 1)[0].upper()
        if head == prefix:
            return line
    return None


def _parse_dtstart_line(line: str) -> tuple[datetime, str] | None:
    """Return a stated instant. A date with no time or an unknown zone is omitted."""
    if ":" not in line:
        return None
    name, value = line.split(":", 1)
    params: dict[str, str] = {}
    for part in name.split(";")[1:]:
        if "=" not in part:
            continue
        key, raw = part.split("=", 1)
        params[key.upper()] = raw
    stamp = value.strip()
    if stamp.endswith("Z") and "T" in stamp:
        try:
            parsed = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        except ValueError:
            return None
        return parsed, "utc"
    tzid = params.get("TZID")
    if tzid and "T" in stamp:
        zone = _TZID_ZONES.get(tzid.upper())
        if zone is None:
            return None
        try:
            naive = datetime.strptime(stamp, "%Y%m%dT%H%M%S")
        except ValueError:
            return None
        return naive.replace(tzinfo=zone), "us-eastern"
    return None
