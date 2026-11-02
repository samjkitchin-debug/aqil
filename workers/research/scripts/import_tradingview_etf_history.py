"""Import ETF history from the TradingView Data API. Not collected by pytest."""

from __future__ import annotations

import sys
from pathlib import Path

from aqil_research.etf.tradingview.budget import HARD_CAP, BudgetLedger
from aqil_research.etf.tradingview.client import TradingViewClient, TradingViewError, load_api_key
from aqil_research.etf.tradingview.run import run_import


def main() -> int:
    try:
        api_key = load_api_key()
    except TradingViewError as exc:
        print(exc)
        return 2
    root = Path(__file__).resolve().parents[1] / ".local" / "tradingview"
    client = TradingViewClient(
        BudgetLedger(root / "ledger.json"),
        root / "cache",
        api_key=api_key,
    )
    report = run_import(client, root=root)
    print(f"calls_used={report.calls_used}")
    print(f"remaining_budget={HARD_CAP - report.calls_used}")
    print(f"halt={report.halt_reason or 'none'}")
    print(f"database={report.database_issue}")
    print(f"dividends={report.dividends_note}")
    print(f"saxo={report.saxo_check}")
    for row in report.rows:
        print(
            " | ".join(
                [
                    row.ticker,
                    row.isin,
                    row.symbol,
                    row.exchange_currency,
                    row.first_date,
                    row.last_date,
                    str(row.count),
                    row.adjustment,
                    row.validation,
                    str(row.db_count),
                    row.eligibility,
                    row.issue,
                ]
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())