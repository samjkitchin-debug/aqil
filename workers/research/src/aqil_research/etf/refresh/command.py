"""ETF refresh commands. The macro refresh module is not imported."""

from __future__ import annotations

import argparse
import os
import sys

from aqil_research.etf.fx.gap import sgd_reference_fx_gap
from aqil_research.etf.prices.adapter import (
    EODHD_SOURCE_ID,
    TWELVE_DATA_SOURCE_ID,
    fetch_eodhd_bars,
    fetch_twelve_data_bars,
)
from aqil_research.etf.prices.persist import storage_allowed
from aqil_research.etf.prices.registry import (
    SAXO_SOURCE_ID,
    UNRESOLVED_PRIMARY,
    current_primary,
)
from aqil_research.etf.prices.sample import candidate_listings
from aqil_research.sources.rights import find_source_rights, load_source_rights


def register_etf_refresh_parsers(sub: argparse._SubParsersAction) -> None:
    refresh = sub.add_parser(
        "etf-refresh",
        help="Refresh one ETF dataset. This does not run the macro refresh.",
    )
    refresh.add_argument("--dataset", required=True, choices=["prices", "nav", "holdings", "fx"])
    refresh.add_argument(
        "--provider",
        default=UNRESOLVED_PRIMARY,
        choices=[UNRESOLVED_PRIMARY, "saxo", "eodhd", "twelve_data"],
    )
    refresh.add_argument(
        "--live",
        action="store_true",
        help="Call the provider when a server-side key is already set. Does not buy a plan.",
    )
    status = sub.add_parser(
        "etf-refresh-status",
        help="Report ETF refresh health without changing the macro schedule.",
    )
    status.add_argument("--dataset", default="prices", choices=["prices", "nav", "holdings", "fx"])


def run_etf_refresh(args: argparse.Namespace) -> int:
    records = load_source_rights()
    if args.dataset == "fx":
        gap = sgd_reference_fx_gap(records)
        print(gap.reason)
        return 0
    if args.dataset == "holdings":
        print("blocked: issuer holdings automation stays prohibited and was not fetched")
        return 0
    if args.dataset == "nav":
        print("blocked: no rights-cleared NAV source is configured")
        return 0
    return _prices(args, records)


def run_etf_refresh_status(args: argparse.Namespace) -> int:
    records = load_source_rights()
    if args.dataset == "fx":
        print(sgd_reference_fx_gap(records).reason)
        return 0
    if args.dataset == "holdings":
        print("holdings: blocked. The prohibited issuer rows were not changed.")
        return 0
    if args.dataset == "nav":
        print("nav: blocked. No NAV source is cleared.")
        return 0
    slot = current_primary()
    print(
        f"prices: primary {slot.provider_id}. {slot.reason} "
        "No feed was purchased. No price was invented."
    )
    return 0


def _prices(args: argparse.Namespace, records) -> int:
    slot = current_primary()
    if args.provider == UNRESOLVED_PRIMARY:
        print(f"blocked: primary {slot.provider_id}. {slot.reason}")
        return 0
    if args.provider == "saxo":
        if slot.provider_id != SAXO_SOURCE_ID:
            print(f"blocked: Saxo is not the primary. {slot.reason}")
            return 0
        print("blocked: Saxo is recorded as entitled, and this command does not invent a bar")
        return 0
    source_id = EODHD_SOURCE_ID if args.provider == "eodhd" else TWELVE_DATA_SOURCE_ID
    record = find_source_rights(records, source_id=source_id)
    allowed = storage_allowed(record, display_audience="any_signed_in")
    env_name = "EODHD_API_TOKEN" if args.provider == "eodhd" else "TWELVE_DATA_API_KEY"
    token = os.environ.get(env_name)
    if not args.live:
        print("blocked: live retrieval was not requested, so no bars were fetched or stored")
        return 0
    if not token:
        print(f"blocked: {env_name} is absent, so no bars were fetched or stored")
        return 0
    if not allowed:
        print("blocked: the price source is not permitted for retention and display")
        return 0
    listing = candidate_listings()[0]
    if args.provider == "eodhd":
        status, bars = fetch_eodhd_bars(ticker=listing.ticker, mic=listing.mic, token=token)
    else:
        status, bars = fetch_twelve_data_bars(ticker=listing.ticker, mic=listing.mic, token=token)
    print(
        f"provider status {status}; bars {len(bars)}; stored 0 pending a permitted database write"
    )
    if status != "ok":
        print("a provider refusal is not an empty price", file=sys.stderr)
        return 1
    return 0
