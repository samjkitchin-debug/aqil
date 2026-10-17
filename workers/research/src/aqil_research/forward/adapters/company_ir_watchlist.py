"""Small company investor-relations watchlist.

Dates stay in the status the register records. Unknown is not promoted to
confirmed, and this module does not invent a future earnings date.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SOURCE_ID = "company_ir_watchlist"
DATASET_ID = "forward.company_ir.watchlist"
DATE_STATUSES = frozenset({"confirmed", "estimated", "unknown"})


class WatchlistIntegrityError(ValueError):
    """A watchlist row contradicts its own date status."""


@dataclass(frozen=True, slots=True)
class IrWatchlistEntry:
    issuer_id: str
    legal_name: str
    ticker: str
    ir_events_url: str
    date_status: str
    scheduled_date: str | None
    first_observed_at: str | None
    note: str


def load_watchlist(path: Path) -> list[IrWatchlistEntry]:
    document = json.loads(path.read_text(encoding="utf-8"))
    issuers = document.get("issuers")
    if not isinstance(issuers, list):
        raise WatchlistIntegrityError("watchlist issuers must be a list")
    entries: list[IrWatchlistEntry] = []
    for row in issuers:
        if not isinstance(row, dict):
            raise WatchlistIntegrityError("watchlist row must be an object")
        entry = IrWatchlistEntry(
            issuer_id=str(row.get("issuer_id", "")),
            legal_name=str(row.get("legal_name", "")),
            ticker=str(row.get("ticker", "")),
            ir_events_url=str(row.get("ir_events_url", "")),
            date_status=str(row.get("date_status", "")),
            scheduled_date=row.get("scheduled_date"),
            first_observed_at=row.get("first_observed_at"),
            note=str(row.get("note", "")),
        )
        _validate(entry)
        entries.append(entry)
    return entries


def entry_event_id(entry: IrWatchlistEntry) -> str:
    return f"event:watchlist:ir:{entry.issuer_id}"


def entry_to_catalyst_payload(
    entry: IrWatchlistEntry,
    *,
    retrieved_at: datetime,
) -> dict[str, object]:
    if entry.date_status == "confirmed":
        evidence_class = "curated_verified"
        provenance = "founder_curated"
        scheduled_at = f"{entry.scheduled_date}T00:00:00+00:00"
    else:
        evidence_class = "watchlist_unverified"
        provenance = "ir_watchlist"
        scheduled_at = None
    return {
        "schema_version": "1.0",
        "event_id": entry_event_id(entry),
        "category": "company_earnings_watchlist",
        "subject_type": "issuer",
        "subject_id": entry.issuer_id,
        "title": f"{entry.legal_name} earnings date {entry.date_status}",
        "scheduled_at": scheduled_at,
        "timezone": None,
        "date_precision": entry.date_status,
        "status": "scheduled",
        "source_id": SOURCE_ID,
        "source_locator": entry.ir_events_url,
        "evidence_class": evidence_class,
        "date_status": entry.date_status,
        "provenance": provenance,
        "first_observed_at": entry.first_observed_at,
        "note": entry.note,
        "retrieved_at": retrieved_at.isoformat(),
        "is_fixture": False,
        "etf_weight_linked": False,
    }


def _validate(entry: IrWatchlistEntry) -> None:
    if entry.date_status not in DATE_STATUSES:
        raise WatchlistIntegrityError(f"unsupported date status {entry.date_status}")
    if not entry.ir_events_url.startswith("https://"):
        raise WatchlistIntegrityError("IR URL must be https")
    if entry.date_status == "unknown" and entry.scheduled_date is not None:
        raise WatchlistIntegrityError("unknown status cannot carry a scheduled date")
    if entry.date_status == "confirmed" and (
        not entry.scheduled_date or not entry.first_observed_at
    ):
        raise WatchlistIntegrityError("confirmed status requires a date and first-observed time")
    if entry.date_status == "estimated" and entry.scheduled_date is None:
        raise WatchlistIntegrityError("estimated status requires the estimated date")
