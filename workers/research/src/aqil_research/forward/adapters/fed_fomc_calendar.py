"""Parse Federal Reserve FOMC meeting calendar (official HTML)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

SOURCE_ID = "federal_reserve_fomc_calendar"
DATASET_ID = "forward.fomc.schedule"
SOURCE_LOCATOR = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan/feb": 1,
    "apr/may": 4,
    "oct/nov": 10,
}


@dataclass(frozen=True, slots=True)
class FomcMeeting:
    year: int
    month: int
    start_day: int
    end_day: int
    tentative: bool
    notation_vote: bool


def _meeting_end_date(meeting: FomcMeeting) -> date:
    return date(meeting.year, meeting.month, meeting.end_day)


def meeting_event_id(meeting: FomcMeeting) -> str:
    end = _meeting_end_date(meeting)
    return f"event:verified:fed:fomc:{end.isoformat()}"


def meeting_scheduled_at(meeting: FomcMeeting) -> datetime:
    """Policy statement day (last day of meeting), 14:00 US/Eastern, stored as UTC."""
    end = _meeting_end_date(meeting)
    local = datetime(
        end.year,
        end.month,
        end.day,
        14,
        0,
        tzinfo=ZoneInfo("America/New_York"),
    )
    return local.astimezone(UTC)


def parse_fomc_calendar_html(
    html: str,
    *,
    min_year: int,
    max_year: int | None = None,
) -> list[FomcMeeting]:
    """Extract FOMC meetings from the official calendar page HTML."""
    max_year = max_year or min_year + 2
    meetings: list[FomcMeeting] = []
    year_blocks = re.split(
        r"(\d{4})\s+FOMC Meetings(?:</a>)?</h4>",
        html,
        flags=re.I,
    )
    if len(year_blocks) < 2:
        year_blocks = re.split(r"####\s*(\d{4})\s+FOMC Meetings", html)

    for idx in range(1, len(year_blocks), 2):
        year = int(year_blocks[idx])
        if year < min_year or year > max_year:
            continue
        block = year_blocks[idx + 1] if idx + 1 < len(year_blocks) else ""
        block = re.split(r"\d{4}\s+FOMC Meetings", block, maxsplit=1)[0]
        meetings.extend(_parse_structured_year_block(year, block))
        if not meetings:
            meetings.extend(_parse_year_block(year, block))

    return sorted(meetings, key=_meeting_end_date)


def _parse_structured_year_block(year: int, block: str) -> list[FomcMeeting]:
    found: list[FomcMeeting] = []
    pattern = re.compile(
        r"fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?"
        r"fomc-meeting__date[^>]*>\s*([^<]+)\s*</div>",
        flags=re.I | re.DOTALL,
    )
    for match in pattern.finditer(block):
        month_key = match.group(1).strip().lower()
        month = _MONTHS.get(month_key)
        if month is None:
            continue
        date_text = match.group(2).strip()
        tentative = "*" in date_text
        date_text = date_text.replace("*", "").strip()
        if "-" in date_text:
            start_s, end_s = date_text.split("-", 1)
            start_day = int(start_s)
            end_day = int(end_s)
        else:
            start_day = end_day = int(date_text)
        notation = "notation vote" in block[match.start() : match.end() + 120].lower()
        found.append(
            FomcMeeting(
                year=year,
                month=month,
                start_day=start_day,
                end_day=end_day,
                tentative=tentative,
                notation_vote=notation,
            ),
        )
    deduped: dict[tuple[int, int, int], FomcMeeting] = {}
    for meeting in found:
        deduped[(meeting.year, meeting.month, meeting.end_day)] = meeting
    return list(deduped.values())


def _parse_year_block(year: int, block: str) -> list[FomcMeeting]:
    found: list[FomcMeeting] = []
    plain = re.sub(r"<[^>]+>", "\n", block)
    plain = re.sub(r"\s+", " ", plain)

    for match in re.finditer(
        r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan/Feb|Apr/May|Oct/Nov)\s+"
        r"(\d{1,2})(?:-(\d{1,2}))?",
        plain,
        flags=re.I,
    ):
        month_key = match.group(1).lower()
        month = _MONTHS.get(month_key)
        if month is None:
            continue
        start_day = int(match.group(2))
        end_day = int(match.group(3)) if match.group(3) else start_day
        snippet = plain[match.start() : match.end() + 40].lower()
        notation = "notation vote" in snippet
        tentative = "*" in snippet or "tentative" in snippet
        found.append(
            FomcMeeting(
                year=year,
                month=month,
                start_day=start_day,
                end_day=end_day,
                tentative=tentative,
                notation_vote=notation,
            ),
        )

    compact = re.finditer(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
        r"(\d{1,2})-(\d{1,2})\*?",
        plain,
        flags=re.I,
    )
    for match in compact:
        month_key = match.group(1).lower()
        month = _MONTHS[month_key]
        tentative = "*" in match.group(0)
        found.append(
            FomcMeeting(
                year=year,
                month=month,
                start_day=int(match.group(2)),
                end_day=int(match.group(3)),
                tentative=tentative,
                notation_vote=False,
            ),
        )

    deduped: dict[tuple[int, int, int], FomcMeeting] = {}
    for meeting in found:
        deduped[(meeting.year, meeting.month, meeting.end_day)] = meeting
    return list(deduped.values())


def meeting_to_catalyst_payload(
    meeting: FomcMeeting, *, retrieved_at: datetime
) -> dict[str, object]:
    end = _meeting_end_date(meeting)
    start = date(meeting.year, meeting.month, meeting.start_day)
    precision = "tentative" if meeting.tentative else "confirmed"
    status = "scheduled" if not meeting.notation_vote else "notation_vote"
    title = (
        "FOMC notation vote — longer-run goals and strategy"
        if meeting.notation_vote
        else "FOMC meeting — federal funds rate decision"
    )
    return {
        "schema_version": "1.0",
        "event_id": meeting_event_id(meeting),
        "category": "central_bank_meeting",
        "subject_type": "central_bank",
        "subject_id": "issuer:us:federal_reserve:fomc",
        "title": title,
        "scheduled_at": meeting_scheduled_at(meeting).isoformat(),
        "timezone": "America/New_York",
        "date_precision": precision,
        "status": status,
        "source_id": SOURCE_ID,
        "source_locator": SOURCE_LOCATOR,
        "evidence_class": "verified_schedule",
        "meeting_start_date": start.isoformat(),
        "meeting_end_date": end.isoformat(),
        "retrieved_at": retrieved_at.isoformat(),
        "is_fixture": False,
    }
