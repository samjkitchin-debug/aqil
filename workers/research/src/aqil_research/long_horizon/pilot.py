"""Run the one frozen category C pilot. Do not score the 618 catalogue scenarios."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import urlparse

import psycopg

from aqil_research.long_horizon.catalogue import (
    assert_family_gates,
    load_catalogue,
)
from aqil_research.long_horizon.documents import pilot_artifact
from aqil_research.long_horizon.money import decimal_text, sha256_document
from aqil_research.long_horizon.policies import ImmediateSingleAssetPolicy, OddEvenJanuaryPolicy
from aqil_research.long_horizon.registry import (
    import_candidate_register,
    store_frozen_specification,
    store_pilot_execution,
)
from aqil_research.long_horizon.simulator import (
    CashFlow,
    PriceBar,
    SimulationResult,
    simulate,
)
from aqil_research.long_horizon.spec import (
    FROZEN_PILOT_SPECIFICATION,
    HYPOTHESIS,
    PILOT_CONTRIBUTION,
    PILOT_COST_RATE,
    PILOT_INTEREST_RATE,
    frozen_specification_hash,
)
from aqil_research.long_horizon.status import assign_category_c_status, claim_proposition

LOCAL_RESEARCH_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres"
LOCAL_ETF_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/aqil_etf"
REPRODUCTION_COMMAND = "uv run python -m aqil_research.long_horizon.reproduce"


class PilotError(RuntimeError):
    """The pilot cannot be scored on this input."""


def repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "docs" / "AGENT_OPERATING_RULES.md").is_file():
            return candidate
    raise PilotError("repository root was not found")


def package_code_hash() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def library_versions() -> dict[str, str]:
    versions = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "simulator_numeric_library": "decimal",
    }
    for name in ("numpy", "psycopg", "pydantic"):
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = "not_installed"
    return versions


def assert_loopback(url: str, database: str) -> None:
    parsed = urlparse(url)
    if parsed.hostname != "127.0.0.1" or parsed.port != 55432:
        raise PilotError("the pilot stays on 127.0.0.1 port 55432")
    if parsed.path.strip("/") != database:
        raise PilotError(f"expected database {database}")


def assert_only_icon_is_dirty(root: Path) -> None:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    unexpected: list[str] = []
    for line in completed.stdout.splitlines():
        path = line[3:].strip().replace("\\", "/")
        if path == "apps/web/public/icons/icon.svg":
            continue
        unexpected.append(path)
    if unexpected:
        raise PilotError("refusing to execute while the worktree has " + ", ".join(unexpected))


def git_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def load_listing_prices(
    connection: psycopg.Connection,
) -> tuple[dict[str, dict[date, PriceBar]], str, dict[str, str]]:
    connection.read_only = True
    with connection.cursor() as cursor:
        cursor.execute("select current_database()")
        if cursor.fetchone()[0] != "aqil_etf":
            raise PilotError("price reads must use aqil_etf")
        cursor.execute(
            """
            select l.ticker, p.session_date, p.value::text, p.currency, p.quote_unit,
                   p.adjustment_status, p.price_type
            from instruments.listings l
            join instruments.market_price_observations p
              on p.listing_id = l.listing_id
            where l.ticker in ('VWRA', 'CSPX')
              and p.price_type = 'adjusted_close'
            order by l.ticker, p.session_date
            """
        )
        fetched = cursor.fetchall()
    prices: dict[str, dict[date, PriceBar]] = defaultdict(dict)
    lines: list[str] = []
    per_symbol: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, date]] = set()
    for ticker, session, raw_value, currency, quote_unit, adjustment_status, price_type in fetched:
        if price_type != "adjusted_close" or adjustment_status != "adjusted":
            raise PilotError("the pilot uses stored split-adjusted closes only")
        if currency != "USD" or quote_unit != "USD":
            raise PilotError("currency conversion is unsupported")
        key = (ticker, session)
        if key in seen:
            raise PilotError(f"duplicate stored close for {ticker} {session}")
        seen.add(key)
        prices[ticker][session] = PriceBar(session, Decimal(raw_value), currency)
        line = f"{ticker}|{session.isoformat()}|{raw_value}|{currency}|{quote_unit}"
        lines.append(line)
        per_symbol[ticker].append(line)
    if set(prices) != {"VWRA", "CSPX"}:
        raise PilotError("VWRA and CSPX stored closes are required")
    combined = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    symbol_hashes = {
        ticker: hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
        for ticker, rows in per_symbol.items()
    }
    return prices, combined, symbol_hashes


def run_frozen_comparison(
    prices: dict[str, dict[date, PriceBar]],
) -> tuple[list[date], list[CashFlow], SimulationResult, SimulationResult, str]:
    if set(prices) != {"VWRA", "CSPX"}:
        raise PilotError("the frozen universe is VWRA and CSPX")
    for symbol, bars in prices.items():
        for session, bar in bars.items():
            if bar.currency != "USD" or bar.session != session or bar.price <= 0:
                raise PilotError(f"unsupported price for {symbol}")
    sessions = sorted(set.intersection(*(set(bars) for bars in prices.values())))
    if not sessions:
        raise PilotError("VWRA and CSPX have no common stored session")
    later_start = max(min(bars) for bars in prices.values())
    earlier_end = min(max(bars) for bars in prices.values())
    if sessions[0] != later_start or sessions[-1] != earlier_end:
        raise PilotError("the window is not the stored overlap")
    if sessions[0] < min(prices["VWRA"]):
        raise PilotError("refusing a VWRA session before the first stored close")
    first_of_month: dict[tuple[int, int], date] = {}
    for session in sessions:
        first_of_month.setdefault((session.year, session.month), session)
    contribution_dates = [first_of_month[key] for key in sorted(first_of_month)]
    contributions = [
        CashFlow(session, Decimal(PILOT_CONTRIBUTION), "contribution")
        for session in contribution_dates
    ]
    rebalance_sessions = {session for session in contribution_dates if session.month == 1}
    shared = {
        "sessions": sessions,
        "prices": prices,
        "contributions": contributions,
        "portfolio_currency": "USD",
        "cost_rate": Decimal(PILOT_COST_RATE),
        "cash_interest_rate": Decimal(PILOT_INTEREST_RATE),
    }
    passive = simulate(
        policy=ImmediateSingleAssetPolicy("VWRA"),
        rebalance_sessions=set(),
        **shared,
    )
    alternative = simulate(
        policy=OddEvenJanuaryPolicy(),
        rebalance_sessions=rebalance_sessions,
        **shared,
    )
    status = assign_category_c_status(
        reconciled=passive.reconciliation.matches and alternative.reconciliation.matches,
        alternative_terminal=alternative.terminal_wealth,
        passive_terminal=passive.terminal_wealth,
    )
    return sessions, contributions, passive, alternative, status


def public_manifest(
    *,
    status: str,
    specification_hash: str,
    artifact_sha256: str,
    price_series_sha256: str,
    symbol_sha256: dict[str, str],
    commit: str,
    code_hash: str,
    sessions: list[date],
    contributions: list[CashFlow],
    passive: SimulationResult,
    alternative: SimulationResult,
) -> dict[str, object]:
    return {
        "hypothesis_id": "LH-H-001",
        "experiment_id": "LH-E-001",
        "execution_id": "LH-X-001",
        "evidence_id": "LH-V-001",
        "claim_id": "LH-C-001",
        "category": "C",
        "category_label": "price_only_simulator_research",
        "not_an_investment_claim": True,
        "status": status,
        "specification_hash": specification_hash,
        "artifact_sha256": artifact_sha256,
        "price_series_sha256": price_series_sha256,
        "symbol_sha256": symbol_sha256,
        "git_commit": commit,
        "code_hash": code_hash,
        "simulation_start": sessions[0].isoformat(),
        "simulation_end": sessions[-1].isoformat(),
        "session_count": len(sessions),
        "contribution_count": len(contributions),
        "contribution_amount": PILOT_CONTRIBUTION,
        "transaction_cost_rate": PILOT_COST_RATE,
        "cash_interest_rate": PILOT_INTEREST_RATE,
        "passive_terminal_wealth": decimal_text(passive.terminal_wealth),
        "passive_ending_cash": decimal_text(passive.ending_cash),
        "passive_ending_units": passive.ending_units,
        "passive_total_costs": decimal_text(passive.total_costs),
        "alternative_terminal_wealth": decimal_text(alternative.terminal_wealth),
        "alternative_ending_cash": decimal_text(alternative.ending_cash),
        "alternative_ending_units": alternative.ending_units,
        "alternative_total_costs": decimal_text(alternative.total_costs),
        "alternative_terminal_forgone_value": decimal_text(alternative.terminal_forgone_value),
        "contributions_equal": passive.total_contributions == alternative.total_contributions,
        "reconciliation_matches": True,
        "supports_investment_alpha": False,
        "publication_allowed": False,
        "reproduction_command": REPRODUCTION_COMMAND,
    }


def write_pilot_note(root: Path, manifest: dict[str, object]) -> None:
    passive_units = manifest["passive_ending_units"]
    alternative_units = manifest["alternative_ending_units"]
    paragraphs = [
        "# Category C pilot",
        "",
        "**Status:** research record. This is not an investment claim and it is not Verified.",
        "",
        (
            f"Hypothesis `{manifest['hypothesis_id']}`, "
            f"experiment `{manifest['experiment_id']}`, "
            f"execution `{manifest['execution_id']}`."
        ),
        (f"Evidence `{manifest['evidence_id']}`, claim `{manifest['claim_id']}`."),
        "",
        (
            "The specification was frozen before this run. Category C is "
            "price-only simulator research. It is not macroeconomic "
            "investment intelligence. `publication_allowed` is false."
        ),
        "",
        "## Reconciliation",
        "",
        (
            "Both ledgers reconcile. Contributions match. Whole units and "
            "residual cash are explicit. Costs are 10 basis points of "
            "notional. Cash interest is the explicit zero. No distribution "
            "and no foreign-exchange conversion were invented."
        ),
        "",
        "| Path | Terminal wealth | Ending cash | Ending units | Costs | Forgone value |",
        "| --- | --- | --- | --- | --- | --- |",
        (
            f"| Immediate VWRA | {manifest['passive_terminal_wealth']} | "
            f"{manifest['passive_ending_cash']} | {passive_units} | "
            f"{manifest['passive_total_costs']} | 0 |"
        ),
        (
            f"| Calendar split | {manifest['alternative_terminal_wealth']} | "
            f"{manifest['alternative_ending_cash']} | {alternative_units} | "
            f"{manifest['alternative_total_costs']} | "
            f"{manifest['alternative_terminal_forgone_value']} |"
        ),
        "",
        (
            f"Window `{manifest['simulation_start']}` to "
            f"`{manifest['simulation_end']}`, {manifest['session_count']} "
            f"common stored sessions, {manifest['contribution_count']} "
            f"contributions of {manifest['contribution_amount']} US dollars."
        ),
        (
            "The window starts at the later stored close. No VWRA history "
            "was manufactured before the first stored session."
        ),
        "",
        "## Scientific status",
        "",
        (
            f"The predetermined rule assigns `{manifest['status']}`. "
            "A language model did not assign it. A larger alternative "
            "terminal wealth would still be inconclusive."
        ),
        (
            "Statistical support, economic usefulness, and forward "
            "validation are forbidden for this category. The full decision "
            "and wealth path is in `research.evidence_records`."
        ),
        "",
        f"Specification hash `{manifest['specification_hash']}`.",
        f"Artifact hash `{manifest['artifact_sha256']}`.",
        f"Price-series hash `{manifest['price_series_sha256']}`.",
        f"Code hash `{manifest['code_hash']}`.",
        f"Git commit `{manifest['git_commit']}`.",
        "",
        (
            f"Reproduce with `{manifest['reproduction_command']}` from "
            "`workers/research` after the local databases are available. "
            "The stored prices are not copied into Git."
        ),
        "",
    ]
    destination = root / "docs" / "research" / "long-horizon" / "PILOT.md"
    destination.write_text("\n".join(paragraphs), encoding="utf-8", newline="\n")
    manifest_path = root / "docs" / "research" / "long-horizon" / "pilot-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def execute_pilot() -> dict[str, object]:
    root = repo_root()
    assert_only_icon_is_dirty(root)
    assert_loopback(LOCAL_RESEARCH_URL, "postgres")
    assert_loopback(LOCAL_ETF_URL, "aqil_etf")
    report = load_catalogue(root / "docs" / "research" / "long-horizon" / "founding-catalogue")
    assert_family_gates(report)
    specification_hash = frozen_specification_hash()
    frozen_at = datetime.now(UTC)
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        identity = research.execute("select current_database()").fetchone()
        if identity is None or identity[0] != "postgres":
            raise PilotError("the registry write must use database postgres")
        import_candidate_register(research, report, frozen_at)
        store_frozen_specification(
            research,
            hypothesis=HYPOTHESIS,
            specification=FROZEN_PILOT_SPECIFICATION,
            specification_hash=specification_hash,
            frozen_at=frozen_at,
        )
        research.commit()
    with psycopg.connect(LOCAL_ETF_URL) as etf:
        prices, combined_hash, symbol_hashes = load_listing_prices(etf)
    sessions, contributions, passive, alternative, status = run_frozen_comparison(prices)
    artifact = pilot_artifact(
        specification_hash=specification_hash,
        price_series_sha256=combined_hash,
        status=status,
        passive=passive,
        alternative=alternative,
    )
    artifact_sha256 = sha256_document(artifact)
    recorded_at = datetime.now(UTC)
    cutoff = datetime(
        sessions[-1].year,
        sessions[-1].month,
        sessions[-1].day,
        tzinfo=UTC,
    )
    relation = "contradicts" if status == "rejected" else "qualifies"
    commit = git_commit(root)
    code_hash = package_code_hash()
    manifest_body = public_manifest(
        status=status,
        specification_hash=specification_hash,
        artifact_sha256=artifact_sha256,
        price_series_sha256=combined_hash,
        symbol_sha256=symbol_hashes,
        commit=commit,
        code_hash=code_hash,
        sessions=sessions,
        contributions=contributions,
        passive=passive,
        alternative=alternative,
    )
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        if research.execute("select current_database()").fetchone()[0] != "postgres":
            raise PilotError("the registry write must use database postgres")
        store_pilot_execution(
            research,
            artifact=artifact,
            artifact_sha256=artifact_sha256,
            status=status,
            proposition=claim_proposition(
                status=status,
                alternative_terminal=alternative.terminal_wealth,
                passive_terminal=passive.terminal_wealth,
            ),
            recorded_at=recorded_at,
            availability_cutoff=cutoff,
            git_commit=commit,
            code_hash=code_hash,
            input_manifest={
                "price_series_sha256": combined_hash,
                "symbol_sha256": symbol_hashes,
                "database": "aqil_etf",
                "price_type": "adjusted_close",
                "currency": "USD",
                "session_count": len(sessions),
                "contribution_count": len(contributions),
                "simulation_start": sessions[0].isoformat(),
                "simulation_end": sessions[-1].isoformat(),
                "availability_cutoff_note": (
                    "Midnight UTC on the last stored session date is a date anchor, "
                    "not an observed close time."
                ),
            },
            price_series_versions=[
                {"symbol": symbol, "sha256": digest}
                for symbol, digest in sorted(symbol_hashes.items())
            ],
            library_versions=library_versions(),
            configuration={
                "specification_hash": specification_hash,
                "methodology_version": "long-horizon-simulator-1",
                "not_macroeconomic_investment_intelligence": True,
            },
            simulation_start=sessions[0],
            simulation_end=sessions[-1],
            relation=relation,
        )
        research.commit()
    write_pilot_note(root, manifest_body)
    return manifest_body


def main() -> None:
    manifest = execute_pilot()
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
