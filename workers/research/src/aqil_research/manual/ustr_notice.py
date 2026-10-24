"""Read a Federal Register notice. The document body is not stored."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.manual.rights_gate import RegistrationBlocked, require_rights
from aqil_research.sources.rights import RightsOperation, SourceRightsRecord

USTR_NOTICE_URL = "https://www.govinfo.gov/content/pkg/FR-2026-10-07/html/2026-20510.htm"
USTR_EVENT_KEY = "ustr_section_301_china_continuation_2026"
USTR_CLUSTER_KEY = "fr-2026-20510"
USTR_CLAIM = (
    "USTR states that the 6 July 2018 and 23 August 2018 Section 301 actions "
    "concerning China did not terminate on 6 July 2026 and 23 August 2026 and "
    "remain in effect, subject to possible further modification."
)
USTR_CHANNEL_NOTE = "CPI-U and industrial production are plausible channels, not a measured effect."
USTR_CHANNELS = ("bls_cpi_u_all_items", "federal_reserve_g17_total_ip")
USTR_EVENT_DATES = "6 July 2026 and 23 August 2026"


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
