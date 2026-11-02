"""Price validation. Missing stays missing. GBX is not divided into GBP."""

from __future__ import annotations

from decimal import Decimal

from aqil_research.etf.identity.collision import listing_attachment_refusal
from aqil_research.etf.prices.models import PriceObservation, ProviderBar, ProviderQuote


class PriceValidationError(Exception):
    """Raised when a price must not be stored."""


def refuse_quote_unit_rewrite(*, observed_unit: str, stored_unit: str) -> str | None:
    """Refuse a unit change. GBX stored as GBP is the case this guards."""

    observed = observed_unit.strip().upper()
    stored = stored_unit.strip().upper()
    if observed == stored:
        return None
    if observed == "GBX" and stored == "GBP":
        return "GBX must stay GBX and must not be stored as GBP"
    return f"quote unit {observed} must not be stored as {stored}"


def assert_listing_may_be_stored(*, ticker: str, mic: str) -> None:
    refusal = listing_attachment_refusal(ticker=ticker, mic=mic)
    if refusal is not None:
        raise PriceValidationError(refusal)


def bars_to_observations(
    bar: ProviderBar,
    *,
    listing_key: str,
    source_id: str,
    source_locator: str,
    retrieved_at,
    revision: int,
    quality: str = "accepted",
    stored_quote_unit: str | None = None,
) -> tuple[PriceObservation, ...]:
    """Build a raw close and, separately, an adjusted close.

    A missing currency, a missing close, or a negative value produces nothing.
    The adjusted close is never written into the close row.
    """

    assert_listing_may_be_stored(ticker=bar.ticker, mic=bar.mic)
    if bar.currency is None or bar.quote_unit is None or bar.observation_time is None:
        raise PriceValidationError("currency, quote unit, or observation time is missing")
    stored_unit = stored_quote_unit or bar.quote_unit
    unit_refusal = refuse_quote_unit_rewrite(
        observed_unit=bar.quote_unit,
        stored_unit=stored_unit,
    )
    if unit_refusal is not None:
        raise PriceValidationError(unit_refusal)
    bar = bar.model_copy(update={"quote_unit": stored_unit})
    rows: list[PriceObservation] = []
    if bar.close is not None:
        rows.append(
            _row(
                bar,
                listing_key=listing_key,
                value=bar.close,
                price_type="close",
                adjustment_status="raw",
                adjustment_definition=None,
                source_id=source_id,
                source_locator=source_locator,
                retrieved_at=retrieved_at,
                revision=revision,
                quality=quality,
            )
        )
    if bar.adjusted_close is not None:
        if not bar.adjustment_definition:
            raise PriceValidationError("an adjusted close needs the provider adjustment definition")
        rows.append(
            _row(
                bar,
                listing_key=listing_key,
                value=bar.adjusted_close,
                price_type="adjusted_close",
                adjustment_status="adjusted",
                adjustment_definition=bar.adjustment_definition,
                source_id=source_id,
                source_locator=source_locator,
                retrieved_at=retrieved_at,
                revision=revision,
                quality=quality,
            )
        )
    if not rows:
        raise PriceValidationError("the provider row has no close")
    return tuple(rows)


def quote_to_observations(
    quote: ProviderQuote,
    *,
    listing_key: str,
    source_id: str,
    source_locator: str,
    session_date,
    retrieved_at,
    revision: int,
) -> tuple[PriceObservation, ...]:
    """Store bid, ask, and last as separate rows. None of them is a close."""

    assert_listing_may_be_stored(ticker=quote.ticker, mic=quote.mic)
    if quote.currency is None or quote.quote_unit is None or quote.observation_time is None:
        raise PriceValidationError("quote currency, quote unit, or observation time is missing")
    rows: list[PriceObservation] = []
    for price_type, value in (("bid", quote.bid), ("ask", quote.ask), ("last", quote.last)):
        if value is None:
            continue
        rows.append(
            PriceObservation(
                listing_key=listing_key,
                session_date=session_date,
                value=value,
                currency=quote.currency,
                quote_unit=quote.quote_unit,
                price_type=price_type,  # type: ignore[arg-type]
                observation_time=quote.observation_time,
                retrieved_at=retrieved_at,
                delay_class=quote.delay_class,
                adjustment_status="not_applicable",
                quality="accepted",
                source_id=source_id,
                source_locator=source_locator,
                revision=revision,
            )
        )
    if not rows:
        raise PriceValidationError("the quote has no bid, ask, or last")
    return tuple(rows)


def _row(
    bar: ProviderBar,
    *,
    listing_key: str,
    value: Decimal,
    price_type: str,
    adjustment_status: str,
    adjustment_definition: str | None,
    source_id: str,
    source_locator: str,
    retrieved_at,
    revision: int,
    quality: str,
) -> PriceObservation:
    if value < 0:
        raise PriceValidationError("a negative price is rejected")
    if bar.currency is None or bar.quote_unit is None or bar.observation_time is None:
        raise PriceValidationError("currency, quote unit, or observation time is missing")
    return PriceObservation(
        listing_key=listing_key,
        session_date=bar.session_date,
        value=value,
        currency=bar.currency,
        quote_unit=bar.quote_unit,
        price_type=price_type,  # type: ignore[arg-type]
        observation_time=bar.observation_time,
        retrieved_at=retrieved_at,
        delay_class="end_of_day",
        adjustment_status=adjustment_status,  # type: ignore[arg-type]
        adjustment_definition=adjustment_definition,
        quality=quality,  # type: ignore[arg-type]
        source_id=source_id,
        source_locator=source_locator,
        revision=revision,
    )
