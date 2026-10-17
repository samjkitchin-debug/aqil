"""Parse SEC EDGAR submissions and companyfacts for completed US filings.

Completed forms are observations. This module does not estimate a future
earnings date or an analyst consensus. Live requests require a declared
User-Agent and stay under the SEC fair-access rate.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

SOURCE_ID = "sec_edgar_company_filings"
DATASET_ID = "forward.sec.edgar.completed_filings"
SOURCE_LOCATOR = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPLETED_FORMS = frozenset({"8-K", "10-Q", "10-K", "10-Q/A", "10-K/A"})
FAIR_ACCESS_MIN_INTERVAL_SECONDS = 0.2


class SecFairAccessError(RuntimeError):
    """Live EDGAR collection was refused because the declared identity is missing."""


@dataclass(frozen=True, slots=True)
class CompletedFiling:
    cik: str
    company_name: str
    form: str
    accession_number: str
    filing_date: str
    acceptance_time: datetime
    items: str
    primary_document: str


def sec_user_agent() -> str:
    value = os.environ.get("AQIL_SEC_USER_AGENT", "").strip()
    if "@" not in value:
        raise SecFairAccessError(
            "Set AQIL_SEC_USER_AGENT to a contact string that includes an email "
            "before live SEC collection.",
        )
    return value


def parse_submissions(document: dict[str, object]) -> list[CompletedFiling]:
    cik = str(document.get("cik", "")).zfill(10)
    name = str(document.get("name", ""))
    filings = document.get("filings")
    if not isinstance(filings, dict):
        return []
    recent = filings.get("recent")
    if not isinstance(recent, dict):
        return []
    forms = _column(recent, "form")
    accessions = _column(recent, "accessionNumber")
    filing_dates = _column(recent, "filingDate")
    acceptances = _column(recent, "acceptanceDateTime")
    items = _column(recent, "items")
    documents = _column(recent, "primaryDocument")
    count = min(
        len(forms),
        len(accessions),
        len(filing_dates),
        len(acceptances),
        len(items),
        len(documents),
    )
    parsed: list[CompletedFiling] = []
    for index in range(count):
        form = forms[index]
        if form not in COMPLETED_FORMS:
            continue
        acceptance = _parse_acceptance(acceptances[index])
        if acceptance is None:
            continue
        parsed.append(
            CompletedFiling(
                cik=cik,
                company_name=name,
                form=form,
                accession_number=accessions[index],
                filing_date=filing_dates[index],
                acceptance_time=acceptance,
                items=items[index],
                primary_document=documents[index],
            ),
        )
    return parsed


def latest_reported_period_end(companyfacts: dict[str, object]) -> str | None:
    """Return the latest period end already reported. Never a forecast date."""
    facts = companyfacts.get("facts")
    if not isinstance(facts, dict):
        return None
    us_gaap = facts.get("us-gaap")
    if not isinstance(us_gaap, dict):
        return None
    latest: str | None = None
    for concept in us_gaap.values():
        if not isinstance(concept, dict):
            continue
        units = concept.get("units")
        if not isinstance(units, dict):
            continue
        for observations in units.values():
            if not isinstance(observations, list):
                continue
            for observation in observations:
                if not isinstance(observation, dict):
                    continue
                end = observation.get("end")
                if isinstance(end, str) and (latest is None or end > latest):
                    latest = end
    return latest


def filing_event_id(filing: CompletedFiling) -> str:
    return f"event:verified:sec:{filing.accession_number}"


def filing_to_catalyst_payload(
    filing: CompletedFiling,
    *,
    retrieved_at: datetime,
    live: bool,
    reported_period_end: str | None = None,
) -> dict[str, object]:
    if live:
        evidence_class = "verified_announcement"
        locator = (
            "https://www.sec.gov/Archives/edgar/data/"
            f"{int(filing.cik)}/{filing.accession_number.replace('-', '')}/"
            f"{filing.primary_document}"
        )
    else:
        evidence_class = "synthetic_demonstration"
        locator = "synthetic://sec-edgar-fixture"
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "event_id": filing_event_id(filing),
        "category": "us_company_filing",
        "subject_type": "issuer",
        "subject_id": f"issuer:us:cik:{filing.cik}",
        "title": f"{filing.company_name} {filing.form} accepted {filing.filing_date}",
        "scheduled_at": filing.acceptance_time.astimezone(UTC).isoformat(),
        "timezone": "America/New_York",
        "date_precision": "confirmed",
        "status": "completed",
        "source_id": SOURCE_ID,
        "source_locator": locator,
        "evidence_class": evidence_class,
        "form": filing.form,
        "accession_number": filing.accession_number,
        "filing_items": filing.items,
        "acceptance_time_basis": "edgar_acceptance_datetime",
        "retrieved_at": retrieved_at.isoformat(),
        "is_fixture": not live,
    }
    if reported_period_end is not None:
        payload["reported_period_end"] = reported_period_end
    return payload


def _column(recent: dict[str, object], name: str) -> list[str]:
    values = recent.get(name, [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def _parse_acceptance(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
