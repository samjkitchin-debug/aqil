"""Parse the official BLS selected-release iCalendar feed.

The HTML schedule states that calendar times are Eastern Time. The feed at
https://www.bls.gov/schedule/news_release/bls.ics is the primary adapter.
Zulu timestamps in the feed are stored as absolute instants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

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


def parse_bls_ics(text: str) -> list[BlsIcsRelease]:
    releases: list[BlsIcsRelease] = []
    for block in _event_blocks(_unfold(text)):
        fields = _fields(block)
        uid = fields.get("UID", "").strip()
        summary = fields.get("SUMMARY", "").strip()
        start_raw = fields.get("DTSTART", "").strip()
        if not uid or not summary or not start_raw:
            continue
        starts_at = _parse_dtstart(start_raw)
        if starts_at is None:
            continue
        releases.append(
            BlsIcsRelease(
                uid=uid,
                summary=summary,
                starts_at=starts_at,
                status=fields.get("STATUS", "CONFIRMED").strip() or "CONFIRMED",
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
        "feed_stamp_basis": "utc" if release.starts_at.tzinfo is not None else "unspecified",
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


def _parse_dtstart(raw: str) -> datetime | None:
    stamp = raw.strip()
    if stamp.endswith("Z") and "T" in stamp:
        try:
            return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        except ValueError:
            return None
    if re.fullmatch(r"\d{8}", stamp):
        parsed = datetime.strptime(stamp, "%Y%m%d").replace(tzinfo=UTC)
        return parsed
    return None
