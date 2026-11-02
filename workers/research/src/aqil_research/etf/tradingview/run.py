"""Run the bounded historical import. Network access stays inside the client."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from aqil_research.etf.contracts.rights import load_etf_rights_fragment
from aqil_research.etf.history.manifest import dataset_manifest
from aqil_research.etf.prices.models import PriceObservation
from aqil_research.etf.prices.persist import storage_allowed
from aqil_research.etf.register.universe import UniverseInstrument, load_universe_v1
from aqil_research.etf.tradingview.budget import BudgetStop
from aqil_research.etf.tradingview.client import TradingViewClient, TradingViewError
from aqil_research.etf.tradingview.identity import MatchedSymbol, MatchFailure, match_search_payload
from aqil_research.etf.tradingview.persist import PriceStoreError, store_observations
from aqil_research.etf.tradingview.series import (
    SPLITS_SOURCE,
    observations_for,
    parse_price_payload,
)

PRIORITY = ("VWRA", "EIMI", "CNDX", "IUIT", "IWMO")
WINDOW_FROM = int(datetime(2016, 11, 3, tzinfo=UTC).timestamp())
WINDOW_TO = int(datetime(2026, 11, 3, tzinfo=UTC).timestamp())
PROBE_FROM = int(datetime(2026, 10, 20, tzinfo=UTC).timestamp())
LOCAL_ETF_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/aqil_etf"
RIGHTS_FRAGMENT = (
    Path(__file__).resolve().parents[6]
    / "docs"
    / "sources"
    / "etf"
    / "fragments"
    / "tradingview_data_api.csv"
)


@dataclass
class CoverageRow:
    ticker: str
    isin: str
    symbol: str
    exchange_currency: str
    first_date: str
    last_date: str
    count: int
    adjustment: str
    validation: str
    db_count: int
    eligibility: str
    issue: str


@dataclass
class ImportReport:
    calls_used: int = 0
    remaining_budget: int = 0
    halt_reason: str | None = None
    database_issue: str = "not attempted"
    rows: list[CoverageRow] = field(default_factory=list)
    saxo_check: str = "no Saxo bar archive was compared; no Saxo row was inserted"
    dividends_note: str = "not requested"


def run_import(client: TradingViewClient, *, root: Path) -> ImportReport:
    """Discover, download, validate, and try to store. Cache hits are free."""

    instruments = {row.research_symbol: row for row in load_universe_v1()}
    report = ImportReport()
    matched: dict[str, MatchedSymbol] = {}
    payloads: dict[str, list[dict[str, object]]] = {symbol: [] for symbol in instruments}
    retrieved_at = datetime.now(UTC)

    for symbol in PRIORITY:
        _search(client, instruments[symbol], "identity", matched, report)
    vwra = matched.get("VWRA")
    page_size = 3000
    if vwra is not None:
        probe = _price_call(
            client,
            vwra,
            "priority_history",
            adjustment="splits",
            range_size=5,
            from_ts=PROBE_FROM,
            report=report,
        )
        if probe is not None:
            payloads["VWRA"].append(probe)
            _note_probe(root, probe)
        page_size = _discover_page_size(client, vwra, report) or page_size
    priority_matches = [matched[symbol] for symbol in PRIORITY if symbol in matched]
    _walk(client, priority_matches, "priority_history", "splits", page_size, payloads, report)
    _dividends(client, matched.get("VWRA"), payloads, report)
    others = [instruments[symbol] for symbol in instruments if symbol not in PRIORITY]
    for instrument in others:
        _search(client, instrument, "remaining", matched, report)
    _walk(
        client,
        [matched[symbol] for symbol in matched if symbol not in PRIORITY],
        "remaining",
        "splits",
        page_size,
        payloads,
        report,
    )
    _finish(client, instruments, matched, payloads, retrieved_at, root, report)
    return report


def _search(
    client: TradingViewClient,
    instrument: UniverseInstrument,
    phase: str,
    matched: dict[str, MatchedSymbol],
    report: ImportReport,
) -> None:
    if client.ledger.remaining(phase) < 1 or client.ledger.halt_reason():
        return
    try:
        payload = client.search_market(phase, instrument.isin)
    except (BudgetStop, TradingViewError) as exc:
        report.halt_reason = str(exc)
        return
    result = match_search_payload(payload, instrument)
    if isinstance(result, MatchedSymbol):
        matched[instrument.research_symbol] = result
        return
    issue = result.issue if isinstance(result, MatchFailure) else "unmatched"
    report.rows.append(_gap(instrument, issue))


def _price_call(
    client: TradingViewClient,
    symbol: MatchedSymbol,
    phase: str,
    *,
    adjustment: str,
    range_size: int,
    from_ts: int,
    report: ImportReport,
) -> dict[str, object] | None:
    if client.ledger.remaining(phase) < 1 or client.ledger.halt_reason():
        return None
    try:
        return client.price(
            phase,
            symbol.tv_symbol,
            adjustment=adjustment,
            range_size=range_size,
            from_ts=from_ts,
        )
    except (BudgetStop, TradingViewError) as exc:
        report.halt_reason = str(exc)
        return None


def _discover_page_size(
    client: TradingViewClient,
    symbol: MatchedSymbol,
    report: ImportReport,
) -> int | None:
    if client.ledger.remaining("priority_history") < 1:
        return None
    try:
        payload = client.price(
            "priority_history",
            symbol.tv_symbol,
            adjustment="splits",
            range_size=3000,
            from_ts=WINDOW_FROM,
        )
    except TradingViewError as exc:
        report.halt_reason = str(exc)
        if "HTTP 400" in str(exc):
            return 400
        return None
    except BudgetStop as exc:
        report.halt_reason = str(exc)
        return None
    history = _history(payload)
    if history and _max_time(history) is not None:
        # The caller stores this page by repeating the same URL, which is a cache hit.
        return 3000 if len(history) < 3000 else 3000
    return 3000


def _walk(
    client: TradingViewClient,
    symbols: list[MatchedSymbol],
    phase: str,
    adjustment: str,
    page_size: int,
    payloads: dict[str, list[dict[str, object]]],
    report: ImportReport,
) -> None:
    cursors = {symbol.research_symbol: WINDOW_FROM for symbol in symbols}
    while cursors and client.ledger.remaining(phase) > 0 and not client.ledger.halt_reason():
        for symbol in list(symbols):
            if symbol.research_symbol not in cursors or client.ledger.remaining(phase) < 1:
                continue
            payload = _price_call(
                client,
                symbol,
                phase,
                adjustment=adjustment,
                range_size=page_size,
                from_ts=cursors[symbol.research_symbol],
                report=report,
            )
            if payload is None:
                cursors.pop(symbol.research_symbol, None)
                continue
            payloads[symbol.research_symbol].append(payload)
            times = [row.get("time") for row in _history(payload) if isinstance(row, dict)]
            numeric = [int(value) for value in times if isinstance(value, int)]
            if not numeric or max(numeric) + 1 <= cursors[symbol.research_symbol]:
                cursors.pop(symbol.research_symbol, None)
                continue
            if len(numeric) < page_size or max(numeric) >= WINDOW_TO:
                cursors.pop(symbol.research_symbol, None)
                continue
            cursors[symbol.research_symbol] = max(numeric) + 1


def _dividends(
    client: TradingViewClient,
    symbol: MatchedSymbol | None,
    payloads: dict[str, list[dict[str, object]]],
    report: ImportReport,
) -> None:
    if symbol is None:
        report.dividends_note = (
            "VWRA identity was not matched, so no dividends sample was requested"
        )
        return
    payload = _price_call(
        client,
        symbol,
        "adjustment",
        adjustment="dividends",
        range_size=20,
        from_ts=PROBE_FROM,
        report=report,
    )
    if payload is None:
        report.dividends_note = "the dividends sample was not returned"
        return
    payloads.setdefault("VWRA-dividends", []).append(payload)
    report.dividends_note = (
        "VWRA dividends sample is a separate series. The docs describe it as splits "
        "plus cash dividends, not as a total-return index."
    )


def _finish(
    client: TradingViewClient,
    instruments: dict[str, UniverseInstrument],
    matched: dict[str, MatchedSymbol],
    payloads: dict[str, list[dict[str, object]]],
    retrieved_at: datetime,
    root: Path,
    report: ImportReport,
) -> None:
    validated_dir = root / "validated"
    validated_dir.mkdir(parents=True, exist_ok=True)
    rights = _founder_storage_allowed()
    observations_by_symbol: dict[str, tuple[PriceObservation, ...]] = {}
    for symbol, instrument in instruments.items():
        already = any(
            row.ticker == instrument.preferred_listing_ticker and row.issue for row in report.rows
        )
        if already:
            continue
        identity = matched.get(symbol)
        if identity is None:
            if not any(row.ticker == instrument.preferred_listing_ticker for row in report.rows):
                report.rows.append(_gap(instrument, "identity was not requested or not matched"))
            continue
        series_payloads = payloads.get(symbol, [])
        candles_observations: list[PriceObservation] = []
        finding_notes: list[str] = []
        for payload in series_payloads:
            parsed = parse_price_payload(
                payload,
                mic=instrument.mic,
                expected_currency=instrument.listing_currency,
                inception_year=int(instrument.inception_year),
                retrieved_at=retrieved_at,
                adjustment="splits",
            )
            finding_notes.extend(parsed.findings)
            candles_observations.extend(
                observations_for(
                    parsed,
                    listing_key=f"{instrument.mic}:{instrument.preferred_listing_ticker}",
                    adjustment="splits",
                    retrieved_at=retrieved_at,
                    locator=_locator(identity.tv_symbol, "splits"),
                )
            )
        deduped = _dedupe_observations(candles_observations)
        observations_by_symbol[symbol] = deduped
        _write_validated(validated_dir / f"{symbol}.json", deduped)
        db_count = 0
        issue = _eligibility_issue(instrument)
        if finding_notes:
            issue = "; ".join(dict.fromkeys([*([issue] if issue else []), *finding_notes[:8]]))
        report.rows.append(
            CoverageRow(
                ticker=instrument.preferred_listing_ticker,
                isin=instrument.isin,
                symbol=identity.tv_symbol if deduped or identity else "",
                exchange_currency=f"{identity.exchange}/{identity.currency}",
                first_date=deduped[0].session_date.isoformat() if deduped else "",
                last_date=deduped[-1].session_date.isoformat() if deduped else "",
                count=len(deduped),
                adjustment="splits" if deduped else "",
                validation=_validation(deduped, finding_notes),
                db_count=db_count,
                eligibility=instrument.research_status,
                issue=issue,
            )
        )
    dividend_rows = payloads.get("VWRA-dividends", [])
    if dividend_rows and "VWRA" in matched:
        instrument = instruments["VWRA"]
        identity = matched["VWRA"]
        dividend_observations: list[PriceObservation] = []
        for payload in dividend_rows:
            parsed = parse_price_payload(
                payload,
                mic=instrument.mic,
                expected_currency=instrument.listing_currency,
                inception_year=int(instrument.inception_year),
                retrieved_at=retrieved_at,
                adjustment="dividends",
            )
            dividend_observations.extend(
                observations_for(
                    parsed,
                    listing_key=f"{instrument.mic}:{instrument.preferred_listing_ticker}",
                    adjustment="dividends",
                    retrieved_at=retrieved_at,
                    locator=_locator(identity.tv_symbol, "dividends"),
                )
            )
        dividend_observations = list(_dedupe_observations(dividend_observations))
        _write_validated(validated_dir / "VWRA-dividends.json", tuple(dividend_observations))
        splits = observations_by_symbol.get("VWRA", ())
        report.dividends_note = _compare_adjustments(
            splits,
            dividend_observations,
            report.dividends_note,
        )
    stored, database_issue = _store_all(observations_by_symbol, instruments, matched, rights)
    report.database_issue = database_issue
    for row in report.rows:
        row.db_count = stored.get(row.isin, 0)
    order = {symbol: index for index, symbol in enumerate(instruments)}
    report.rows.sort(key=lambda row: order.get(row.ticker, len(order)))
    report.calls_used = client.ledger.used()
    report.remaining_budget = 60 - report.calls_used
    report.halt_reason = report.halt_reason or client.ledger.halt_reason()
    _write_manifest(root, instruments, report, stored)


def _store_all(
    observations_by_symbol: dict[str, tuple[PriceObservation, ...]],
    instruments: dict[str, UniverseInstrument],
    matched: dict[str, MatchedSymbol],
    rights_allowed: bool,
) -> tuple[dict[str, int], str]:
    if not rights_allowed:
        return {}, "founder retention is not permitted by the loaded rights fragment"
    url = os.environ.get("ETF_DATABASE_URL", "").strip() or LOCAL_ETF_URL
    parsed = urlparse(url)
    if (parsed.hostname or "") not in {"127.0.0.1", "localhost"}:
        return {}, "ETF database URL is not a loopback address; hosted writes were not attempted"
    if parsed.path.lstrip("/").split("/")[0] == "postgres":
        return {}, "refusing to write the preserved database postgres"
    try:
        import psycopg
    except ImportError:
        return {}, "psycopg is not installed; database write blocked"
    try:
        with psycopg.connect(url, connect_timeout=3) as conn:
            counts: dict[str, int] = {}
            for symbol, observations in observations_by_symbol.items():
                instrument = instruments[symbol]
                identity = matched[symbol]
                try:
                    result = store_observations(
                        conn,
                        observations,
                        isin=instrument.isin,
                        mic=instrument.mic,
                        ticker=identity.ticker,
                        currency=instrument.listing_currency,
                    )
                except PriceStoreError as exc:
                    conn.rollback()
                    return counts, str(exc)
                if result.issue:
                    return counts, result.issue
                counts[instrument.isin] = result.inserted
            conn.commit()
            return counts, "stored on the local ETF database"
    except Exception as exc:
        message = str(exc).replace(url, "ETF database URL")
        return {}, f"database write blocked: {type(exc).__name__}: {message[:180]}"


def _founder_storage_allowed() -> bool:
    if not RIGHTS_FRAGMENT.is_file():
        return False
    record = load_etf_rights_fragment(RIGHTS_FRAGMENT)
    return storage_allowed(record, display_audience="founder")


def _gap(instrument: UniverseInstrument, issue: str) -> CoverageRow:
    extra = _eligibility_issue(instrument)
    combined = issue if not extra else f"{issue}; {extra}"
    return CoverageRow(
        ticker=instrument.preferred_listing_ticker,
        isin=instrument.isin,
        symbol="",
        exchange_currency=f"{instrument.preferred_exchange}/{instrument.listing_currency}",
        first_date="",
        last_date="",
        count=0,
        adjustment="",
        validation="not validated",
        db_count=0,
        eligibility=instrument.research_status,
        issue=combined,
    )


def _eligibility_issue(instrument: UniverseInstrument) -> str:
    if instrument.research_symbol == "INRG":
        return "total return stays insufficient without a distribution series"
    if instrument.research_symbol == "EUNA":
        return "research comparator; not an equity approval"
    return ""


def _validation(
    observations: list[PriceObservation] | tuple[PriceObservation, ...],
    findings: list[str],
) -> str:
    blocking = [
        item
        for item in findings
        if "currency" in item or "GBX" in item or "not positive" in item or "high/low" in item
    ]
    if blocking and not observations:
        return "failed"
    if not observations:
        return "no bars"
    if findings:
        return "passed with notes"
    return "passed"


def _dedupe_observations(rows: list[PriceObservation]) -> tuple[PriceObservation, ...]:
    kept: dict[tuple[str, str], PriceObservation] = {}
    for row in rows:
        key = (row.source_id, row.session_date.isoformat())
        kept[key] = row
    return tuple(sorted(kept.values(), key=lambda row: (row.source_id, row.session_date)))


def _compare_adjustments(
    splits: tuple[PriceObservation, ...],
    dividends: list[PriceObservation],
    note: str,
) -> str:
    splits_by_day = {
        row.session_date: row.value for row in splits if row.source_id == SPLITS_SOURCE
    }
    same = 0
    different = 0
    for row in dividends:
        other = splits_by_day.get(row.session_date)
        if other is None:
            continue
        if other == row.value:
            same += 1
        else:
            different += 1
    return (
        f"{note} Sample overlap: {same} equal closes, {different} different closes. "
        "Equal closes in a short window are not a total-return index."
    )


def _locator(symbol: str, adjustment: str) -> str:
    return (
        "https://api.tradingviewapi.com/api/price/"
        f"{symbol}?timeframe=D&type=Japanese&adjustment={adjustment}"
    )


def _history(payload: dict[str, object]) -> list[object]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    history = data.get("history")
    if not isinstance(history, list):
        return []
    return history


def _max_time(history: list[object]) -> int | None:
    times = [row.get("time") for row in history if isinstance(row, dict)]
    numeric = [int(value) for value in times if isinstance(value, int)]
    return max(numeric) if numeric else None


def _note_probe(root: Path, payload: dict[str, object]) -> None:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    info = data.get("info") if isinstance(data, dict) and isinstance(data.get("info"), dict) else {}
    history = data.get("history") if isinstance(data, dict) else None
    if not isinstance(history, list):
        history = []
    summary = {
        "symbol": data.get("symbol") if isinstance(data, dict) else None,
        "currency": info.get("currency_code") if isinstance(info, dict) else None,
        "history_count": len(history),
        "history_keys": sorted({key for row in history if isinstance(row, dict) for key in row}),
        "has_adjusted_close_field": any(
            isinstance(row, dict) and "adjusted_close" in row for row in history
        ),
    }
    (root / "probe_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _write_validated(path: Path, rows: tuple[PriceObservation, ...]) -> None:
    payload = [
        {
            "session_date": row.session_date.isoformat(),
            "value": str(row.value),
            "currency": row.currency,
            "price_type": row.price_type,
            "adjustment_definition": row.adjustment_definition,
            "source_id": row.source_id,
        }
        for row in rows
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_manifest(
    root: Path,
    instruments: dict[str, UniverseInstrument],
    report: ImportReport,
    stored: dict[str, int],
) -> None:
    histories = {}
    for row in report.rows:
        histories[row.ticker] = "cached" if row.count else "not ingested"
    total = sum(stored.values())
    licensed = "not established" if total == 0 else "founder retention stored"
    manifest = dataset_manifest(
        tuple(instruments[symbol] for symbol in instruments),
        stored_price_observations=total,
        licensed_storage=licensed,
        histories=histories,
    )
    destination = (
        Path(__file__).resolve().parents[6]
        / "docs"
        / "sources"
        / "etf"
        / "history"
        / "aqil_etf_history_v1_2026-11.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (root / "coverage.json").write_text(
        json.dumps(
            {
                "calls_used": report.calls_used,
                "remaining_budget": report.remaining_budget,
                "halt_reason": report.halt_reason,
                "database_issue": report.database_issue,
                "saxo_check": report.saxo_check,
                "dividends_note": report.dividends_note,
                "rows": [row.__dict__ for row in report.rows],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
