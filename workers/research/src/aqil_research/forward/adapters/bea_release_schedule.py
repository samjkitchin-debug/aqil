"""Parse the BEA news-release schedule HTML table.

BEA states that most of its information is public domain and should be cited.
The schedule page lists a clock time. This adapter does not assign a timezone
when the page does not state one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

SOURCE_ID = "bea_release_schedule"
DATASET_ID = "forward.bea.news.schedule"
SOURCE_LOCATOR = "https://www.bea.gov/news/schedule"

_YEAR = re.compile(r"Year\s+(\d{4})", re.I)
_ROW = re.compile(
    r'<div class="release-date">\s*([A-Za-z]+ \d{1,2})\s*</div>\s*'
    r"<small[^>]*>\s*(\d{1,2}:\d{2}\s*[AP]M)\s*</small>.*?"
    r'<td class="release-title[^"]*"[^>]*>\s*([^<]+?)\s*</td>',
    re.I | re.S,
)


@dataclass(frozen=True, slots=True)
class BeaRelease:
    release_date: date
    published_clock: str
    release_type: str
    title: str


def parse_bea_schedule_html(html: str, *, year: int | None = None) -> list[BeaRelease]:
    header_year = _YEAR.search(html)
    resolved_year = int(header_year.group(1)) if header_year else year
    if resolved_year is None:
        return []
    releases: list[BeaRelease] = []
    for match in _ROW.finditer(html):
        month_day = datetime.strptime(
            f"{match.group(1)} {resolved_year}",
            "%B %d %Y",
        ).date()
        releases.append(
            BeaRelease(
                release_date=month_day,
                published_clock=re.sub(r"\s+", " ", match.group(2)).strip().upper(),
                release_type="news",
                title=re.sub(r"\s+", " ", match.group(3)).strip(),
            ),
        )
    return releases


def release_event_id(release: BeaRelease) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", release.title.lower()).strip("-")[:80]
    return f"event:verified:bea:{release.release_date.isoformat()}:{slug}"


def release_to_catalyst_payload(
    release: BeaRelease,
    *,
    retrieved_at: datetime,
) -> dict[str, object]:
    day_anchor = datetime(
        release.release_date.year,
        release.release_date.month,
        release.release_date.day,
        tzinfo=UTC,
    )
    return {
        "schema_version": "1.0",
        "event_id": release_event_id(release),
        "category": "us_national_accounts",
        "subject_type": "economic_release",
        "subject_id": "dataset:bea:news-schedule",
        "title": f"BEA {release.title}",
        "scheduled_at": day_anchor.isoformat(),
        "timezone": None,
        "date_precision": "confirmed",
        "status": "scheduled",
        "source_id": SOURCE_ID,
        "source_locator": SOURCE_LOCATOR,
        "evidence_class": "verified_schedule",
        "published_clock": release.published_clock,
        "clock_timezone_stated": False,
        "release_type": release.release_type,
        "retrieved_at": retrieved_at.isoformat(),
        "is_fixture": False,
    }
