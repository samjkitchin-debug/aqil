"""Read a Federal Register notice. The document body is not stored."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.manual.rights_gate import RegistrationBlocked, require_rights
from aqil_research.sources.rights import RightsOperation, SourceRightsRecord

USTR_NOTICE_URL = "https://www.govinfo.gov/content/pkg/FR-2026-10-07/html/2026-20510.htm"
USTR_TITLE = (
    "Continuation of Actions: China's Acts, Policies, and Practices Related to "
    "Technology Transfer, Intellectual Property, and Innovation"
)
USTR_EVENT_KEY = "ustr_section_301_china_continuation_2026"
USTR_CLUSTER_KEY = "fr-2026-20510"
USTR_CLAIM = (
    "USTR states that the 6 July 2018 and 23 August 2018 Section 301 actions "
    "concerning China did not terminate on 6 July 2026 and 23 August 2026 and "
    "remain in effect, subject to possible further modification."
)
USTR_PUBLISHED_ON = date(2026, 10, 7)
USTR_EVENT_ON = date(2026, 8, 23)
USTR_CHANNEL_NOTE = "CPI-U and industrial production are plausible channels, not a measured effect."
USTR_CHANNELS = ("bls_cpi_u_all_items", "federal_reserve_g17_total_ip")
USTR_EVENT_DATES = "6 July 2026 and 23 August 2026"
_CLAIM_PHRASES = (
    "Section 301",
    "China",
    "6 July 2018",
    "23 August 2018",
    "did not terminate",
    "6 July 2026",
    "23 August 2026",
    "remain in effect",
    "modification",
)


@dataclass(frozen=True, slots=True)
class SuppliedUstrNotice:
    """Operator-supplied fields. This object is not a fetched document."""

    title: str
    canonical_url: str
    published_at: datetime
    event_dates: str
    summary: str
    event_on: date


def parse_supplied_ustr_notice(
    *,
    title: str,
    canonical_url: str,
    published_at: str,
    event_dates: str,
    summary: str,
) -> SuppliedUstrNotice:
    """Check a no-fetch registration. This function does not open a network connection."""
    clean_title = title.strip()
    if clean_title != USTR_TITLE:
        raise RegistrationBlocked("title is not the Federal Register notice title")
    if canonical_url.strip() != USTR_NOTICE_URL:
        raise RegistrationBlocked("canonical URL is not Federal Register notice 2026-20510")
    published = _parse_published_at(published_at)
    if published.date() != USTR_PUBLISHED_ON:
        raise RegistrationBlocked("published_at is not 7 October 2026")
    dates = " ".join(event_dates.split())
    if "6 July 2026" not in dates or "23 August 2026" not in dates:
        raise RegistrationBlocked("event dates must state 6 July 2026 and 23 August 2026")
    if _latest_uk_date(dates) != USTR_EVENT_ON:
        raise RegistrationBlocked("event date is not 23 August 2026")
    clean_summary = " ".join(summary.split())
    if not _short_continuation(clean_summary):
        raise RegistrationBlocked("summary is not the short continuation claim")
    return SuppliedUstrNotice(
        title=clean_title,
        canonical_url=USTR_NOTICE_URL,
        published_at=published,
        event_dates=dates,
        summary=clean_summary,
        event_on=USTR_EVENT_ON,
    )


def supplied_fields_from_args(args: object) -> SuppliedUstrNotice | None:
    """Return a notice when every no-fetch field is present. A partial set is refused."""
    values = (
        getattr(args, "title", None),
        getattr(args, "canonical_url", None),
        getattr(args, "published_at", None),
        getattr(args, "event_dates", None),
        getattr(args, "summary", None),
    )
    present = [value is not None and str(value).strip() != "" for value in values]
    if not any(present):
        return None
    if not all(present):
        raise RegistrationBlocked(
            "The no-fetch path needs a title, canonical URL, published time, "
            "event dates, and a short summary.",
        )
    return parse_supplied_ustr_notice(
        title=str(values[0]),
        canonical_url=str(values[1]),
        published_at=str(values[2]),
        event_dates=str(values[3]),
        summary=str(values[4]),
    )


def _parse_published_at(value: str) -> datetime:
    text = value.strip()
    if len(text) == 10:
        try:
            day = date.fromisoformat(text)
        except ValueError as exc:
            raise RegistrationBlocked("published_at is not a date") from exc
        return datetime(day.year, day.month, day.day, tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RegistrationBlocked("published_at is not a date") from exc
    if parsed.tzinfo is None:
        raise RegistrationBlocked("published_at must include a time zone")
    return parsed.astimezone(UTC)


def _latest_uk_date(text: str) -> date:
    months = {
        name: index
        for index, name in enumerate(
            (
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ),
            start=1,
        )
    }
    found: list[date] = []
    for day, month, year in re.findall(r"\b(\d{1,2}) ([A-Z][a-z]+) (\d{4})\b", text):
        month_number = months.get(month)
        if month_number is None:
            continue
        try:
            found.append(date(int(year), month_number, int(day)))
        except ValueError as exc:
            raise RegistrationBlocked("event dates are not dates") from exc
    if not found:
        raise RegistrationBlocked("event dates are not stated")
    return max(found)


def _short_continuation(summary: str) -> bool:
    if not 40 <= len(summary) <= 500:
        return False
    if any(token in summary for token in ("<", ">", "SUPPLEMENTARY", "new tariff")):
        return False
    return all(phrase in summary for phrase in _CLAIM_PHRASES)


def visible_text(body: str) -> str:
    text = re.sub(r"(?is)<script\b.*?>.*?</script>", " ", body)
    text = re.sub(r"(?is)<style\b.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&#160;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _section(text: str, start: str, ends: tuple[str, ...]) -> str:
    start_at = text.find(start)
    if start_at < 0:
        return ""
    body = text[start_at + len(start) :]
    end_at = min((body.find(marker) for marker in ends if body.find(marker) >= 0), default=-1)
    if end_at >= 0:
        body = body[:end_at]
    return body


def notice_supports_ustr_claim(body: str) -> bool:
    """True only when SUMMARY and DATES support the continuation claim."""
    text = visible_text(body)
    summary = _section(text, "SUMMARY:", ("DATES:",))
    dates = _section(text, "DATES:", ("FOR FURTHER INFORMATION", "ADDRESSES:", "SUPPLEMENTARY"))
    if not summary or not dates:
        return False
    summary_ok = (
        "have not terminated" in summary
        and "remain in effect" in summary
        and "modification" in summary
    )
    dates_ok = all(
        phrase in dates
        for phrase in (
            "July 6, 2018",
            "August 23, 2018",
            "did not terminate on July 6, 2026",
            "did not terminate on August 23, 2026",
            "remain in effect",
        )
    )
    identity_ok = all(
        phrase in text
        for phrase in (
            "Section 301",
            "China",
            "Office of the United States Trade Representative",
            "October 7, 2026",
        )
    )
    return summary_ok and dates_ok and identity_ok


def fetch_ustr_notice(rights: SourceRightsRecord) -> str:
    """One GET. Refuses unless automated access and retention are permitted."""
    require_rights(
        rights,
        (RightsOperation.AUTOMATED_ACCESS, RightsOperation.RAW_DATA_RETENTION),
    )
    parsed = urlparse(USTR_NOTICE_URL)
    if parsed.scheme != "https" or parsed.hostname != "www.govinfo.gov":
        raise RegistrationBlocked("notice URL is not the govinfo host")
    if parsed.path != "/content/pkg/FR-2026-10-07/html/2026-20510.htm":
        raise RegistrationBlocked("notice path is not document 2026-20510")
    try:
        with httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=False
        ) as client:
            response = client.get(
                USTR_NOTICE_URL,
                headers={"User-Agent": AQIL_RETRIEVAL_USER_AGENT},
            )
    except httpx.HTTPError as exc:
        raise RegistrationBlocked("govinfo notice could not be fetched") from exc
    if response.status_code != 200:
        raise RegistrationBlocked(f"govinfo returned HTTP {response.status_code}")
    return response.text
