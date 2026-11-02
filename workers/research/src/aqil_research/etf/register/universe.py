"""Load and check the frozen 3 November 2026 ETF register.

Identity fields come from the founder artifact. They are not re-fetched from
an issuer in this module, so a loaded row is not an issuer citation. Listing
substitutions named in the artifact are refused. No price is loaded.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

REGISTER_VERSION = "ETF_UNIVERSE_V1_2026-11-03"
DECISION_DATE = "2026-11-03"
TARGET_START = "2016-11-03"
TARGET_END = "2026-11-02"

_EXCHANGE_MIC = {
    "LSE": "XLON",
    "Euronext Amsterdam": "XAMS",
    "Xetra": "XETR",
}

_FORBIDDEN_ATTACHMENTS = (
    ("VWRA", "VWRP"),
    ("VWRA", "VWCE"),
    ("IJPA", "SJPA"),
    ("SPEQ", "SPEX"),
    ("RBOT", "RBTX"),
    ("IWQU", "IWFQ"),
)


class RegisterError(ValueError):
    """The artifact does not match the frozen V1 register."""


class UniverseInstrument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    research_symbol: str
    share_class_name: str
    issuer: str
    isin: str = Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    research_status: str = Field(pattern="^(Approved|Conditional|Comparator)$")
    asset_class: str
    primary_exposure: str
    distribution_policy: str = Field(pattern="^(Accumulating|Distributing)$")
    domicile: str
    inception_year: str
    preferred_listing_ticker: str
    preferred_exchange: str
    listing_currency: str = Field(pattern=r"^[A-Z]{3}$")
    issuer_source_url: str
    identity_notes: str = ""
    register_version: str
    founder_decision_date: str
    investment_permission: str
    mic: str
    investment_approved: bool


def register_json_path() -> Path:
    """Path of the frozen JSON artifact inside this repository."""

    return (
        Path(__file__).resolve().parents[6]
        / "docs"
        / "sources"
        / "etf"
        / "register"
        / "aqil_etf_universe_v1_2026-11-03.json"
    )


def artifact_sha256(path: Path | None = None) -> str:
    """Checksum of the frozen JSON. A changed file is a different register."""

    source = path or register_json_path()
    return sha256(source.read_bytes()).hexdigest()


def load_universe_v1(path: Path | None = None) -> tuple[UniverseInstrument, ...]:
    """Load the frozen register. Counts and forbidden listings are enforced."""

    source = path or register_json_path()
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("version") != REGISTER_VERSION:
        raise RegisterError("register version is not ETF_UNIVERSE_V1_2026-11-03")
    if payload.get("decision_date") != DECISION_DATE:
        raise RegisterError("founder decision date is not 2026-11-03")
    rows = payload.get("instruments")
    if not isinstance(rows, list):
        raise RegisterError("instruments must be a list")
    loaded = tuple(_row(item) for item in rows)
    _counts(loaded)
    _identities(loaded)
    return loaded


def _row(item: object) -> UniverseInstrument:
    if not isinstance(item, dict):
        raise RegisterError("an instrument row must be an object")
    exchange = str(item.get("preferred_exchange", ""))
    mic = _EXCHANGE_MIC.get(exchange)
    if mic is None:
        raise RegisterError(f"exchange {exchange} has no MIC in the frozen map")
    status = str(item.get("research_status", ""))
    return UniverseInstrument(
        category=str(item["category"]),
        research_symbol=str(item["research_symbol"]),
        share_class_name=str(item["share_class_name"]),
        issuer=str(item["issuer"]),
        isin=str(item["isin"]),
        research_status=status,  # type: ignore[arg-type]
        asset_class=str(item["asset_class"]),
        primary_exposure=str(item["primary_exposure"]),
        distribution_policy=str(item["distribution_policy"]),  # type: ignore[arg-type]
        domicile=str(item["domicile"]),
        inception_year=str(item["inception_year"]),
        preferred_listing_ticker=str(item["preferred_listing_ticker"]),
        preferred_exchange=exchange,
        listing_currency=str(item["listing_currency"]),
        issuer_source_url=str(item["issuer_source_url"]),
        identity_notes=str(item.get("identity_notes") or ""),
        register_version=str(item["register_version"]),
        founder_decision_date=str(item["founder_decision_date"]),
        investment_permission=str(item["investment_permission"]),
        mic=mic,
        investment_approved=status == "Approved",
    )


def _counts(rows: tuple[UniverseInstrument, ...]) -> None:
    approved = sum(1 for row in rows if row.research_status == "Approved")
    conditional = sum(1 for row in rows if row.research_status == "Conditional")
    comparator = sum(1 for row in rows if row.research_status == "Comparator")
    if (approved, conditional, comparator, len(rows)) != (18, 1, 1, 20):
        raise RegisterError("the frozen register is 18 approved, 1 conditional, 1 comparator")
    symbols = [row.research_symbol for row in rows]
    if len(symbols) != len(set(symbols)):
        raise RegisterError("research symbols must be unique")
    isins = [row.isin for row in rows]
    if len(isins) != len(set(isins)):
        raise RegisterError("ISINs must be unique")


def _identities(rows: tuple[UniverseInstrument, ...]) -> None:
    by_symbol = {row.research_symbol: row for row in rows}
    expected = {
        "VWRA": ("IE00BK5BQT80", "XLON", "USD", "VWRA"),
        "IWDA": ("IE00B4L5Y983", "XLON", "USD", "IWDA"),
        "CNDX": ("IE00B53SZB19", "XLON", "USD", "CNDX"),
        "IJPA": ("IE00B4L5YX21", "XLON", "USD", "IJPA"),
        "ICHN": ("IE00BJ5JPG56", "XAMS", "USD", "ICHN"),
        "SMH": ("IE00BMC38736", "XLON", "USD", "SMH"),
        "SPEQ": ("IE00BNGJJT35", "XLON", "USD", "SPEQ"),
        "EUNA": ("IE00BDBRDM35", "XETR", "EUR", "EUNA"),
        "INRG": ("IE00B1XNHC34", "XLON", "USD", "INRG"),
    }
    for symbol, (isin, mic, currency, ticker) in expected.items():
        row = by_symbol.get(symbol)
        if row is None:
            raise RegisterError(f"{symbol} is missing from the frozen register")
        if (row.isin, row.mic, row.listing_currency, row.preferred_listing_ticker) != (
            isin,
            mic,
            currency,
            ticker,
        ):
            raise RegisterError(f"{symbol} does not match the frozen listing identity")
    inrg = by_symbol["INRG"]
    if inrg.investment_approved or inrg.distribution_policy != "Distributing":
        raise RegisterError("INRG stays conditional and distributing")
    euna = by_symbol["EUNA"]
    if euna.investment_approved or euna.asset_class != "Fixed income":
        raise RegisterError("EUNA stays a research comparator and is not an equity approval")
    for symbol, substitute in _FORBIDDEN_ATTACHMENTS:
        if by_symbol[symbol].preferred_listing_ticker == substitute:
            raise RegisterError(f"{symbol} must not use the {substitute} listing")
    if by_symbol["ICHN"].preferred_exchange == "LSE":
        raise RegisterError("ICHN is not a London listing")


def listing_is_forbidden_substitute(*, research_symbol: str, ticker: str, mic: str) -> bool:
    """True when a ticker or venue must not be stored as this research symbol."""

    symbol = research_symbol.strip().upper()
    offered = ticker.strip().upper()
    venue = mic.strip().upper()
    if symbol == "CNDX" and venue in {"XTSE", "XTSX", "NEOE"}:
        return True
    if symbol == "ICHN" and venue == "XLON":
        return True
    if symbol == "SMH" and venue in {"XNYS", "XNAS", "ARCX"}:
        return True
    return any(symbol == left and offered == right for left, right in _FORBIDDEN_ATTACHMENTS)
