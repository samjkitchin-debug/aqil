"""ETF market-data foundation. No bar, ISIN, or approval is invented."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from aqil_research.etf.fx.gap import sgd_reference_fx_gap
from aqil_research.etf.governance import (
    GovernanceError,
    draft_approval,
    eligibility_is_not_approval,
)
from aqil_research.etf.holdings import top_ten_overlap
from aqil_research.etf.identity.collision import (
    listing_attachment_refusal,
    listings_share_a_cited_class,
)
from aqil_research.etf.performance.returns import simple_return, total_return
from aqil_research.etf.prices.adapter import (
    fetch_eodhd_bars,
    fetch_twelve_data_quote,
    parse_eodhd_bars,
    parse_twelve_data_bars,
)
from aqil_research.etf.prices.models import PriceObservation, ProviderBar, ProviderQuote
from aqil_research.etf.prices.persist import (
    apply_price_writes,
    mark_stale,
    plan_price_writes,
    storage_allowed,
)
from aqil_research.etf.prices.sample import SAMPLE_LISTINGS, candidate_listings
from aqil_research.etf.prices.validate import PriceValidationError, bars_to_observations
from aqil_research.etf.read.contract import (
    ApprovalRow,
    EligibilityRow,
    HoldingLine,
    build_read_model,
)
from aqil_research.etf.refresh.run import run_holdings_refresh_failure, run_price_refresh
from aqil_research.etf.saxo.probe import CHARTS, INFO_PRICES, probe_saxo_read
from aqil_research.sources.rights import RightsDecision, find_source_rights, load_source_rights

_WHEN = datetime(2026, 10, 30, 16, 35, tzinfo=UTC)
_RETRIEVED = datetime(2026, 10, 30, 18, 0, tzinfo=UTC)


class _Response:
    def __init__(self, status_code: int, body: object) -> None:
        self.status_code = status_code
        self._body = body
        self.text = ""

    def json(self) -> object:
        return self._body


def _bar(**overrides: object) -> ProviderBar:
    payload: dict[str, object] = {
        "ticker": "VWRA",
        "mic": "XLON",
        "session_date": date(2026, 10, 30),
        "close": Decimal("140.10"),
        "adjusted_close": Decimal("140.10"),
        "currency": "USD",
        "quote_unit": "USD",
        "adjustment_definition": "Provider adjusted_close is separate from close.",
        "observation_time": _WHEN,
        "volume": Decimal("1000"),
    }
    payload.update(overrides)
    return ProviderBar.model_validate(payload)


def _close(**overrides: object) -> PriceObservation:
    payload: dict[str, object] = {
        "listing_key": "XLON:VWRA:USD",
        "session_date": date(2026, 10, 30),
        "value": Decimal("140.10"),
        "currency": "USD",
        "quote_unit": "USD",
        "price_type": "close",
        "observation_time": _WHEN,
        "retrieved_at": _RETRIEVED,
        "delay_class": "end_of_day",
        "adjustment_status": "raw",
        "quality": "accepted",
        "source_id": "eodhd_global_etf_eod",
        "source_locator": "https://eodhd.com/api/eod/VWRA.LSE",
        "revision": 1,
    }
    payload.update(overrides)
    return PriceObservation.model_validate(payload)


def test_canadian_cndx_is_not_attached_to_the_london_ticker() -> None:
    refusal = listing_attachment_refusal(ticker="CNDX", mic="XTSE")
    assert refusal is not None
    assert listing_attachment_refusal(ticker="CNDX", mic="NEOE") is not None
    assert listing_attachment_refusal(ticker="CNDX", mic="XLON") is None
    assert (
        listings_share_a_cited_class(
            cited_isin="IE00B0000009",
            left_ticker="CNDX",
            left_mic="XLON",
            right_ticker="CNDX",
            right_mic="XTSE",
        )
        is False
    )
    assert (
        listings_share_a_cited_class(
            cited_isin=None,
            left_ticker="VWRA",
            left_mic="XLON",
            right_ticker="VWCE",
            right_mic="XETR",
        )
        is False
    )


def test_sample_listings_have_no_isin_and_keep_london_cndx() -> None:
    assert all(listing.cited_isin is None for listing in SAMPLE_LISTINGS)
    tickers = {(listing.ticker, listing.mic) for listing in candidate_listings()}
    assert ("CNDX", "XLON") in tickers
    assert ("CNDX", "XTSE") not in tickers
    assert ("VWRA", "XLON") in tickers
    assert ("VWCE", "XETR") in tickers


def test_gbx_is_not_stored_as_gbp() -> None:
    with pytest.raises(PriceValidationError, match="GBX"):
        bars_to_observations(
            _bar(quote_unit="GBX", currency="GBP", close=Decimal("12345")),
            listing_key="XLON:PENCE:GBP",
            source_id="eodhd_global_etf_eod",
            source_locator="synthetic://gbx",
            retrieved_at=_RETRIEVED,
            revision=1,
            stored_quote_unit="GBP",
        )


def test_raw_close_and_adjusted_close_stay_distinct() -> None:
    rows = bars_to_observations(
        _bar(),
        listing_key="XLON:VWRA:USD",
        source_id="eodhd_global_etf_eod",
        source_locator="synthetic://bars",
        retrieved_at=_RETRIEVED,
        revision=1,
    )
    kinds = {row.price_type: row for row in rows}
    assert kinds["close"].adjustment_status == "raw"
    assert kinds["adjusted_close"].adjustment_status == "adjusted"
    assert kinds["close"].value == Decimal("140.10")
    assert kinds["adjusted_close"].adjustment_definition


def test_nav_is_not_a_close() -> None:
    nav = _close(price_type="nav", listing_key="share-class", value=Decimal("141.00"))
    close = _close()
    assert nav.price_type != close.price_type
    assert nav.value != close.value


def test_negative_price_is_rejected() -> None:
    with pytest.raises(PriceValidationError, match="negative"):
        bars_to_observations(
            _bar(close=Decimal("-1"), adjusted_close=None),
            listing_key="XLON:VWRA:USD",
            source_id="eodhd_global_etf_eod",
            source_locator="synthetic://negative",
            retrieved_at=_RETRIEVED,
            revision=1,
        )


def test_missing_key_does_not_fabricate_bars() -> None:
    status, bars = fetch_eodhd_bars(ticker="VWRA", mic="XLON", token=None)
    assert status == "absent_key"
    assert bars == ()


def test_unauthorised_response_is_not_an_empty_success() -> None:
    status, bars = fetch_eodhd_bars(
        ticker="VWRA",
        mic="XLON",
        token="not-printed",
        transport=lambda _url: _Response(401, {}),
    )
    assert status == "unauthorised"
    assert bars == ()


def test_eodhd_parser_keeps_adjusted_close_separate_and_omits_missing_currency() -> None:
    bars = parse_eodhd_bars(
        [{"date": "2026-10-30", "close": "10.5", "adjusted_close": "10.4", "volume": "3"}],
        ticker="VWRA",
        mic="XLON",
    )
    assert bars[0].close == Decimal("10.5")
    assert bars[0].adjusted_close == Decimal("10.4")
    assert bars[0].currency is None


def test_twelve_data_parser_uses_meta_currency() -> None:
    bars = parse_twelve_data_bars(
        {"meta": {"currency": "USD"}, "values": [{"datetime": "2026-10-30", "close": "10"}]},
        ticker="VWRA",
        mic="XLON",
    )
    assert bars[0].currency == "USD"
    assert bars[0].adjusted_close is None


def test_quote_failure_is_not_a_stored_quote() -> None:
    status, quote = fetch_twelve_data_quote(
        ticker="VWRA",
        mic="XLON",
        token="not-printed",
        transport=lambda _url: _Response(403, {}),
    )
    assert status == "forbidden"
    assert quote is None


def test_stale_quote_keeps_its_type_and_original_row() -> None:
    quote = _close(
        price_type="last",
        delay_class="delayed",
        retrieved_at=_RETRIEVED,
        value=Decimal("140.20"),
    )
    marked = mark_stale((quote,), retrieved_at=_RETRIEVED + timedelta(hours=49))
    assert marked[0].quality == "stale"
    assert marked[0].price_type == "last"
    assert quote.quality == "accepted"


def test_second_refresh_is_idempotent_and_failure_keeps_the_close() -> None:
    first = run_price_refresh(
        existing=(),
        incoming=(_close(),),
        provider="eodhd",
        idempotency_key="prices-eodhd-2026-10-30",
        rights_allowed=True,
        provider_failed=False,
        market_closed=False,
        finished_at=_RETRIEVED,
    )
    assert first.status == "succeeded"
    assert len(first.prices) == 1
    second = run_price_refresh(
        existing=first.prices,
        incoming=(_close(revision=9),),
        provider="eodhd",
        idempotency_key="prices-eodhd-2026-10-30",
        rights_allowed=True,
        provider_failed=False,
        market_closed=False,
        finished_at=_RETRIEVED,
        previous_run=first,
    )
    assert second.prices == first.prices
    failed = run_price_refresh(
        existing=first.prices,
        incoming=(_close(value=Decimal("999")),),
        provider="eodhd",
        idempotency_key="prices-eodhd-retry",
        rights_allowed=True,
        provider_failed=True,
        market_closed=False,
        finished_at=_RETRIEVED,
    )
    assert failed.status == "failed"
    assert failed.prices[0].value == Decimal("140.10")
    holdings = run_holdings_refresh_failure(
        prices=first.prices,
        idempotency_key="holdings-failed",
    )
    assert holdings.dataset == "holdings"
    assert holdings.prices[0].price_type == "close"


def test_changed_close_appends_and_identical_close_does_not() -> None:
    existing = (_close(),)
    same = plan_price_writes(existing, (_close(revision=4),))
    assert same[0].action == "skip"
    assert apply_price_writes(existing, same) == existing
    changed = plan_price_writes(existing, (_close(value=Decimal("141")),))
    assert changed[0].action == "append"
    assert changed[0].observation.revision == 2
    stored = apply_price_writes(existing, changed)
    assert stored[0].value == Decimal("140.10")
    assert stored[1].value == Decimal("141")


def test_price_rows_are_blocked_until_rights_permit_display() -> None:
    records = load_source_rights()
    eodhd = find_source_rights(records, source_id="eodhd_global_etf_eod")
    twelve = find_source_rights(records, source_id="twelve_data_global_etf_eod")
    assert eodhd is not None and twelve is not None
    assert storage_allowed(eodhd, display_audience="any_signed_in") is False
    assert storage_allowed(twelve, display_audience="founder") is False
    vanguard = find_source_rights(records, source_id="vanguard_uk_vwra_holdings")
    ishares = find_source_rights(records, source_id="ishares_ucits_holdings")
    assert vanguard is not None and ishares is not None
    assert vanguard.automated_access == RightsDecision.PROHIBITED
    assert ishares.automated_access == RightsDecision.PROHIBITED


def test_fx_gap_stores_no_rate() -> None:
    gap = sgd_reference_fx_gap(load_source_rights())
    assert gap.usable is False
    assert "No rate is stored" in gap.reason or "no FX rate is stored" in gap.reason


def test_returns_guard_inception_units_and_dividends() -> None:
    inception = date(2020, 6, 1)
    market = simple_return(
        series_kind="market",
        start_value=Decimal("100"),
        end_value=Decimal("110"),
        start_unit="USD",
        end_unit="USD",
        inception=inception,
        period_start=date(2024, 1, 1),
    )
    nav = simple_return(
        series_kind="nav",
        start_value=Decimal("100"),
        end_value=Decimal("111"),
        start_unit="USD",
        end_unit="USD",
        inception=inception,
        period_start=date(2024, 1, 1),
    )
    assert market.accepted and nav.accepted
    assert market.value != nav.value
    early = simple_return(
        series_kind="market",
        start_value=Decimal("100"),
        end_value=Decimal("110"),
        start_unit="GBX",
        end_unit="GBX",
        inception=inception,
        period_start=date(2019, 1, 1),
    )
    assert early.accepted is False
    mixed = simple_return(
        series_kind="market",
        start_value=Decimal("10000"),
        end_value=Decimal("100"),
        start_unit="GBX",
        end_unit="GBP",
        inception=inception,
        period_start=date(2024, 1, 1),
    )
    assert mixed.accepted is False
    distributing = total_return(
        distribution_policy="distributing",
        start_value=Decimal("100"),
        end_value=Decimal("110"),
        start_unit="USD",
        end_unit="USD",
        dividend=None,
        uses_adjusted_close=False,
        inception=inception,
        period_start=date(2024, 1, 1),
    )
    assert distributing.accepted is False
    accumulating = total_return(
        distribution_policy="accumulating",
        start_value=Decimal("100"),
        end_value=Decimal("110"),
        start_unit="USD",
        end_unit="USD",
        dividend=Decimal("1"),
        uses_adjusted_close=True,
        inception=inception,
        period_start=date(2024, 1, 1),
    )
    assert accumulating.accepted is False


def test_partial_holdings_do_not_become_an_empty_overlap() -> None:
    overlap = top_ten_overlap(
        left_line_count=10,
        right_line_count=10,
        rights_cleared=False,
    )
    assert overlap["label"] == "partial"
    model = build_read_model(
        isin=None,
        cited=False,
        listings=(),
        eligibility=(),
        approvals=(),
        prices=(),
        fx_reason="No FX rate is stored.",
        holdings_completeness="partial",
        holdings_lines=(HoldingLine(name="Example"),),
        other_lines=(HoldingLine(name="Example"),),
    )
    assert model.shared_holding_count is None
    assert model.overlap_label == "unavailable"


def test_approval_history_is_separate_from_eligibility_and_not_autonomous() -> None:
    assert eligibility_is_not_approval("CORE") is True
    with pytest.raises(GovernanceError, match="autonomous"):
        draft_approval(
            decision="approved",
            actor="founder",
            rationale="not inserted by this programme",
            recorded_at=_RETRIEVED,
            autonomous=True,
        )
    model = build_read_model(
        isin=None,
        cited=False,
        listings=("XLON VWRA USD",),
        eligibility=(
            EligibilityRow(
                decision="insufficient",
                conditions="No permitted issuer citation is stored.",
                recorded_at=_RETRIEVED,
            ),
        ),
        approvals=(),
        prices=(_close(),),
        fx_reason="No FX rate is stored.",
        holdings_completeness="partial",
        as_of=date(2026, 10, 30),
    )
    assert model.approvals == ()
    assert model.eligibility[0].decision == "insufficient"
    assert model.latest_close is not None
    assert model.latest_close.price_type == "close"


def test_explicit_approval_requires_actor_and_is_not_called_here_as_founder() -> None:
    with pytest.raises(GovernanceError):
        draft_approval(
            decision="approved",
            actor="  ",
            rationale="missing actor",
            recorded_at=_RETRIEVED,
            autonomous=False,
        )
    draft = draft_approval(
        decision="restricted",
        actor="synthetic-actor",
        rationale="synthetic rationale for the append-only contract",
        recorded_at=_RETRIEVED,
        autonomous=False,
    )
    assert draft.actor == "synthetic-actor"
    row = ApprovalRow(
        decision=draft.decision,
        actor=draft.actor,
        rationale=draft.rationale,
        recorded_at=draft.recorded_at,
    )
    assert row.decision == "restricted"


def test_saxo_403_does_not_block_or_store() -> None:
    class _Saxo:
        status_code = 403

    result = probe_saxo_read(
        base_url="https://gateway.saxobank.com/sim/openapi",
        token="local-token",
        path=INFO_PRICES,
        transport=lambda _url: _Saxo(),
    )
    assert result.http_status == 403
    assert result.stored is False
    assert result.blocks_programme is False
    skipped = probe_saxo_read(
        base_url="https://gateway.saxobank.com/openapi",
        token="local-token",
        path=CHARTS,
    )
    assert skipped.stored is False
    assert "Production" in skipped.reason


def test_quote_rows_are_not_closes() -> None:
    rows = bars_to_observations(
        _bar(adjusted_close=None),
        listing_key="XLON:VWRA:USD",
        source_id="eodhd_global_etf_eod",
        source_locator="synthetic://close-only",
        retrieved_at=_RETRIEVED,
        revision=1,
    )
    quote = ProviderQuote(
        ticker="VWRA",
        mic="XLON",
        bid=Decimal("140"),
        ask=Decimal("140.2"),
        last=Decimal("140.1"),
        currency="USD",
        quote_unit="USD",
        delay_class="delayed",
        observation_time=_WHEN,
    )
    from aqil_research.etf.prices.validate import quote_to_observations

    quoted = quote_to_observations(
        quote,
        listing_key="XLON:VWRA:USD",
        source_id="twelve_data_global_etf_eod",
        source_locator="synthetic://quote",
        session_date=date(2026, 10, 30),
        retrieved_at=_RETRIEVED,
        revision=1,
    )
    assert {row.price_type for row in rows} == {"close"}
    assert {row.price_type for row in quoted} == {"bid", "ask", "last"}


def test_primary_is_unresolved_until_the_saxo_proof_records_entitlement(tmp_path: Path) -> None:
    from aqil_research.etf.prices.registry import (
        SAXO_SOURCE_ID,
        UNRESOLVED_PRIMARY,
        current_primary,
        resolve_primary,
    )

    missing = current_primary(tmp_path / "missing.md")
    assert missing.provider_id == UNRESOLVED_PRIMARY
    assert missing.infoprices_entitled is None
    tested = current_primary()
    assert tested.provider_id == UNRESOLVED_PRIMARY
    assert tested.infoprices_entitled is False
    assert tested.daily_charts_entitled is False
    assert tested.retention_permitted is False
    assert "simulation" in tested.reason
    assert "HTTP 401" in tested.reason
    assert "not suitable" in tested.reason
    assert "not be stored as LIVE" in tested.reason
    assert "SAXO_MARKET_DATA_PROOF_2026-11-02.md" in tested.reason
    denied = resolve_primary(
        "InfoPrices HTTP 403\nDaily charts HTTP 403\nRetention is not permitted\n"
    )
    assert denied.provider_id == UNRESOLVED_PRIMARY
    assert denied.infoprices_entitled is False
    silent = resolve_primary("A probe was started. No price is stored.\n")
    assert silent.provider_id == UNRESOLVED_PRIMARY
    assert silent.infoprices_entitled is None
    entitled = resolve_primary("InfoPrices entitled\nDaily charts entitled\nRetention permitted\n")
    assert entitled.provider_id == SAXO_SOURCE_ID
