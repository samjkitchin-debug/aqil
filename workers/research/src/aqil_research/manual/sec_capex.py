"""Two annual Microsoft capital-expenditure facts from SEC companyfacts.

The JSON body is not stored. microsoft.com and secondary compilers are not used.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse

import httpx

from aqil_research.manual.rights_gate import RegistrationBlocked, require_rights
from aqil_research.sources.rights import RightsOperation, SourceRightsRecord

COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json"
MICROSOFT_CIK = "789019"
CONCEPT = "PaymentsToAcquirePropertyPlantAndEquipment"
SEC_SOURCE_ID = "sec_edgar_company_filings"
MAX_RESPONSE_BYTES = 25_000_000

THEME_DOES_NOT_ESTABLISH = (
    "This does not establish AI-only spending, forecast spending, demand, adoption, "
    "revenue, earnings, equity prices, or whether the theme is accelerating."
)


@dataclass(frozen=True, slots=True)
class AnnualCapexFact:
    amount: str
    unit: str
    period_start: date
    period_end: date
    filed_at: date
    filing_url: str
    form: str
    accession: str
    entity_name: str


def _decimal_text(value: object) -> str | None:
    try:
        number = Decimal(str(value))
    except Exception:
        return None
    if not number.is_finite() or number <= 0:
        return None
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or None


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def filing_index_url(cik: str, accession: str) -> str:
    digits = str(int(cik))
    compact = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{digits}/{compact}/{accession}-index.html"


def extract_annual_capex(payload: object) -> tuple[AnnualCapexFact, AnnualCapexFact] | None:
    """Two comparable FY facts, same entity and unit, each covering one year."""
    if not isinstance(payload, dict):
        return None
    cik = str(payload.get("cik", "")).lstrip("0")
    entity = payload.get("entityName")
    if cik != MICROSOFT_CIK or not isinstance(entity, str) or not entity.strip():
        return None
    facts = payload.get("facts")
    if not isinstance(facts, dict):
        return None
    gaap = facts.get("us-gaap")
    if not isinstance(gaap, dict):
        return None
    concept = gaap.get(CONCEPT)
    if not isinstance(concept, dict):
        return None
    units = concept.get("units")
    if not isinstance(units, dict):
        return None
    chosen: list[AnnualCapexFact] | None = None
    for unit_name in sorted(units, key=lambda name: (name != "USD", name)):
        rows = units.get(unit_name)
        if not isinstance(rows, list):
            continue
        picked = _pick_annual(rows, str(unit_name), entity.strip(), cik)
        if picked is not None:
            chosen = picked
            break
    if chosen is None:
        return None
    return chosen[0], chosen[1]


def _pick_annual(
    rows: list[object],
    unit: str,
    entity: str,
    cik: str,
) -> list[AnnualCapexFact] | None:
    by_period: dict[tuple[date, date], AnnualCapexFact] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("fp") != "FY" or row.get("form") not in {"10-K", "10-K/A"}:
            continue
        start = _parse_date(row.get("start"))
        end = _parse_date(row.get("end"))
        filed = _parse_date(row.get("filed"))
        accession = row.get("accn")
        amount = _decimal_text(row.get("val"))
        if start is None or end is None or filed is None or amount is None:
            continue
        if not isinstance(accession, str) or not accession:
            continue
        duration = (end - start).days
        if duration < 364 or duration > 366:
            continue
        fact = AnnualCapexFact(
            amount=amount,
            unit=unit,
            period_start=start,
            period_end=end,
            filed_at=filed,
            filing_url=filing_index_url(cik, accession),
            form=str(row.get("form")),
            accession=accession,
            entity_name=entity,
        )
        current = by_period.get((start, end))
        if current is None or _prefer(fact, current):
            by_period[(start, end)] = fact
    ordered = sorted(by_period.values(), key=lambda item: item.period_end, reverse=True)
    if len(ordered) < 2:
        return None
    latest = ordered[:2]
    if latest[0].unit != latest[1].unit:
        return None
    return latest


def _prefer(candidate: AnnualCapexFact, current: AnnualCapexFact) -> bool:
    if candidate.form == "10-K" and current.form != "10-K":
        return True
    if candidate.form != "10-K" and current.form == "10-K":
        return False
    return candidate.filed_at > current.filed_at


def fetch_company_facts(rights: SourceRightsRecord) -> dict[str, object]:
    """One GET. Does not invent a contact email."""
    agent = os.environ.get("AQIL_SEC_USER_AGENT", "").strip()
    if not agent or any(char in agent for char in "\r\n"):
        raise RegistrationBlocked("AQIL_SEC_USER_AGENT is not set")
    require_rights(
        rights,
        (RightsOperation.AUTOMATED_ACCESS, RightsOperation.RAW_DATA_RETENTION),
    )
    parsed = urlparse(COMPANY_FACTS_URL)
    if parsed.scheme != "https" or parsed.hostname != "data.sec.gov":
        raise RegistrationBlocked("companyfacts URL is not data.sec.gov")
    try:
        with httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0), follow_redirects=False
        ) as client:
            response = client.get(
                COMPANY_FACTS_URL,
                headers={"User-Agent": agent, "Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise RegistrationBlocked("SEC companyfacts could not be fetched") from exc
    if response.status_code != 200:
        raise RegistrationBlocked(f"SEC companyfacts returned HTTP {response.status_code}")
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise RegistrationBlocked("SEC companyfacts response is too large")
    try:
        payload = json.loads(response.content)
    except json.JSONDecodeError as exc:
        raise RegistrationBlocked("SEC companyfacts response was not JSON") from exc
    if not isinstance(payload, dict):
        raise RegistrationBlocked("SEC companyfacts response was not an object")
    return payload
