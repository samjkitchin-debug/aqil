"""Parse BLS Employment Situation release schedule (official HTML table)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

SOURCE_ID = "bls_release_schedule"
DATASET_ID = "forward.bls.empsit.schedule"
SOURCE_LOCATOR = "https://www.bls.gov/schedule/news_release/empsit.htm"


@dataclass(frozen=True, slots=True)
class BlsEmploymentRelease:
    reference_month: str
    release_date: date
    release_time_local: str


def parse_empsit_schedule_html(html: str) -> list[BlsEmploymentRelease]:
    rows: list[BlsEmploymentRelease] = []
    pipe_row = (
        r"\|\s*([A-Za-z]+ \d{4})\s*\|\s*([A-Za-z]+\.\s+\d{1,2},\s+\d{4})\s*\|"
        r"\s*(\d{1,2}:\d{2}\s*[AP]M)\s*\|"
    )
    html_row = (
        r"<td>([A-Za-z]+ \d{4})</td>\s*<td>([A-Za-z]+\.\s+\d{1,2},\s+\d{4})</td>\s*"
        r"<td>(\d{1,2}:\d{2}\s*[AP]M)</td>"
    )
    patterns = (pipe_row, html_row)
    for pattern in patterns:
        for match in re.finditer(pattern, html, flags=re.I):
            ref_month = match.group(1).strip()
            release = _parse_us_date(match.group(2).strip())
            time_local = match.group(3).strip()
            rows.append(
                BlsEmploymentRelease(
                    reference_month=ref_month,
                    release_date=release,
                    release_time_local=time_local,
                ),
            )
    deduped = {release.release_date: release for release in rows}
    return list(deduped.values())


def _parse_us_date(text: str) -> date:
    cleaned = text.replace(".", "")
    return datetime.strptime(cleaned, "%b %d, %Y").date()


def release_event_id(release: BlsEmploymentRelease) -> str:
    return f"event:verified:bls:empsit:{release.release_date.isoformat()}"


def release_scheduled_at(release: BlsEmploymentRelease) -> datetime:
    hour = 8
    minute = 30
    m = re.match(r"(\d{1,2}):(\d{2})\s*([AP]M)", release.release_time_local, re.I)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        if m.group(3).upper() == "PM" and hour != 12:
            hour += 12
        if m.group(3).upper() == "AM" and hour == 12:
            hour = 0
    local = datetime(
        release.release_date.year,
        release.release_date.month,
        release.release_date.day,
        hour,
        minute,
        tzinfo=ZoneInfo("America/New_York"),
    )
    return local.astimezone(UTC)


def release_to_catalyst_payload(
    release: BlsEmploymentRelease,
    *,
    retrieved_at: datetime,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": release_event_id(release),
        "category": "us_employment_report",
        "subject_type": "economic_release",
        "subject_id": "dataset:bls:empsit",
        "title": f"US employment situation — {release.reference_month} reference month",
        "scheduled_at": release_scheduled_at(release).isoformat(),
        "timezone": "America/New_York",
        "date_precision": "confirmed",
        "status": "scheduled",
        "source_id": SOURCE_ID,
        "source_locator": SOURCE_LOCATOR,
        "evidence_class": "verified_schedule",
        "reference_month": release.reference_month,
        "retrieved_at": retrieved_at.isoformat(),
        "is_fixture": False,
    }
