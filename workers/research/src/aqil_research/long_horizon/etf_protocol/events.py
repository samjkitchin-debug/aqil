"""EVT-DEF-002 identification. Callers pass closes. This module does not read a database."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.etf_protocol.rules import (
    predictor_value,
    trailing_volatility_median,
)
from aqil_research.long_horizon.etf_protocol.specification import (
    EVENT_DEFINITION_V2,
    ProtocolError,
)
from aqil_research.long_horizon.events.identify import (
    EventRow,
    FamilyCount,
    running_drawdown,
    up_session_fraction,
)
from aqil_research.long_horizon.events.pilot_rule import month_end_indices
from aqil_research.long_horizon.money import decimal_text


def _rule(family: str) -> dict[str, object]:
    families = EVENT_DEFINITION_V2["families"]
    if not isinstance(families, dict) or family not in families:
        raise ProtocolError(f"{family} is not in EVT-DEF-002")
    rule = families[family]
    if not isinstance(rule, dict):
        raise ProtocolError(f"{family} is not an object")
    return rule


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _metrics(closes: Sequence[Decimal], start: int, end: int) -> tuple[str, str, str]:
    window = closes[start : end + 1]
    price_return = window[-1] / window[0] - 1
    return (
        decimal_text(price_return),
        decimal_text(running_drawdown(window)),
        decimal_text(up_session_fraction(window)),
    )


def _row(
    family: str,
    horizon: str,
    closes: Sequence[Decimal],
    start: int,
    end: int,
    confirmed: int | None,
    *,
    uses_later: bool,
    observable: bool,
    detail: str,
) -> EventRow:
    price_return, drawdown, fraction = _metrics(closes, start, end)
    return EventRow(
        family=family,
        horizon_label=horizon,
        start_index=start,
        end_index=end,
        label_confirmed_index=confirmed,
        label_uses_later_prices=uses_later,
        historically_observable_at_event_date=observable,
        price_return=price_return,
        max_intervening_drawdown=drawdown,
        up_session_fraction=fraction,
        detail=detail,
    )


def _running_rally(closes: Sequence[Decimal]) -> Decimal:
    trough = closes[0]
    best = Decimal(0)
    for price in closes:
        if price < trough:
            trough = price
        change = price / trough - 1
        if change > best:
            best = change
    return best


def _down_fraction(closes: Sequence[Decimal]) -> Decimal:
    steps = len(closes) - 1
    if steps <= 0:
        return Decimal(0)
    falls = sum(1 for left, right in zip(closes, closes[1:], strict=False) if right < left)
    return Decimal(falls) / Decimal(steps)


def sustained_declines(closes: Sequence[Decimal]) -> list[FamilyCount]:
    rules = _rule("sustained_decline")
    counts: list[FamilyCount] = []
    for horizon, raw in rules.items():
        if not isinstance(raw, dict):
            raise ProtocolError("a sustained-decline horizon is not an object")
        steps = int(raw["steps"])
        maximum = _decimal(raw["maximum_return"])
        rally_cap = _decimal(raw["maximum_rally"])
        down_floor = _decimal(raw["minimum_down_session_fraction"])
        qualifiers: list[int] = []
        events: list[EventRow] = []
        examined = 0
        last = len(closes) - 1
        index = 0
        while index + steps <= last:
            examined += 1
            window = closes[index : index + steps + 1]
            price_return = window[-1] / window[0] - 1
            rally = _running_rally(window)
            fraction = _down_fraction(window)
            if price_return <= maximum and rally <= rally_cap and fraction >= down_floor:
                qualifiers.append(index)
            index += 1
        cursor = 0
        while cursor + steps <= last:
            window = closes[cursor : cursor + steps + 1]
            price_return = window[-1] / window[0] - 1
            rally = _running_rally(window)
            fraction = _down_fraction(window)
            if price_return <= maximum and rally <= rally_cap and fraction >= down_floor:
                events.append(
                    _row(
                        "sustained_decline",
                        str(horizon),
                        closes,
                        cursor,
                        cursor + steps,
                        cursor + steps,
                        uses_later=True,
                        observable=False,
                        detail=(
                            "Earliest qualifying decline, then resume at the end session. "
                            "The magnitudes mirror sustained advance."
                        ),
                    )
                )
                cursor += steps
            else:
                cursor += 1
        counts.append(
            FamilyCount(
                family="sustained_decline",
                horizon_label=str(horizon),
                status="catalogued",
                reason="Mirrored from sustained advance. Overlapping qualifiers are counted once.",
                events=tuple(events),
                windows_examined=examined,
                qualifier_window_count=len(qualifiers),
                censored_count=0,
            )
        )
    return counts


def _confirmed_downswings(
    closes: Sequence[Decimal],
    decline: Decimal,
    rally: Decimal,
) -> tuple[list[tuple[int, int, int]], int]:
    if not closes:
        return [], 0
    peak = 0
    trough = 0
    seeking_rally = False
    found: list[tuple[int, int, int]] = []
    for index in range(1, len(closes)):
        price = closes[index]
        if not seeking_rally:
            if price >= closes[peak]:
                peak = index
                trough = index
                continue
            if price / closes[peak] - 1 <= -decline:
                seeking_rally = True
                trough = index
            continue
        if price <= closes[trough]:
            trough = index
        if price / closes[trough] - 1 >= rally:
            found.append((peak, trough, index))
            peak = index
            trough = index
            seeking_rally = False
    return found, 1 if seeking_rally else 0


def persistent_bears(closes: Sequence[Decimal]) -> FamilyCount:
    rule = _rule("persistent_bear")
    decline = _decimal(rule["minimum_decline"])
    rally = _decimal(rule["confirming_rally"])
    minimum_steps = int(rule["minimum_session_steps"])
    swings, censored = _confirmed_downswings(closes, decline, rally)
    events: list[EventRow] = []
    for peak, trough, confirm in swings:
        steps = trough - peak
        lost = closes[trough] / closes[peak] - 1
        if steps < minimum_steps or lost > -decline:
            continue
        events.append(
            _row(
                "persistent_bear",
                "20pct",
                closes,
                peak,
                trough,
                confirm,
                uses_later=True,
                observable=False,
                detail=(
                    "A 20 percent decline confirmed by a later 20 percent rally. "
                    "An unconfirmed terminal decline is censored."
                ),
            )
        )
    return FamilyCount(
        family="persistent_bear",
        horizon_label="20pct",
        status="catalogued",
        reason="Mirrored from persistent bull. The terminal unconfirmed decline is censored.",
        events=tuple(events),
        windows_examined=len(swings),
        qualifier_window_count=len(swings),
        censored_count=censored,
    )


def failed_recoveries(closes: Sequence[Decimal]) -> FamilyCount:
    rule = _rule("failed_recovery")
    decline = _decimal(rule["minimum_decline"])
    retracement = _decimal(rule["retracement"])
    events: list[EventRow] = []
    censored = 0
    if closes:
        peak = 0
        trough = 0
        in_drawdown = False
        half_touched = False
        trough_at_half = Decimal(0)
        for index in range(1, len(closes)):
            price = closes[index]
            if not in_drawdown:
                if price >= closes[peak]:
                    peak = index
                    trough = index
                elif price / closes[peak] - 1 <= -decline:
                    in_drawdown = True
                    trough = index
                    half_touched = False
                continue
            if not half_touched and price < closes[trough]:
                trough = index
            half = closes[trough] + (closes[peak] - closes[trough]) * retracement
            if not half_touched and half <= price < closes[peak]:
                half_touched = True
                trough_at_half = closes[trough]
            if half_touched and price <= trough_at_half:
                events.append(
                    _row(
                        "failed_recovery",
                        "15pct_half",
                        closes,
                        trough,
                        index,
                        index,
                        uses_later=True,
                        observable=False,
                        detail=(
                            "A drawdown retraced half the fall and then returned to the "
                            "trough before the old peak was regained."
                        ),
                    )
                )
                half_touched = False
                trough = index
                continue
            if price >= closes[peak]:
                in_drawdown = False
                half_touched = False
                peak = index
                trough = index
        if in_drawdown:
            censored = 1
    return FamilyCount(
        family="failed_recovery",
        horizon_label="15pct_half",
        status="catalogued",
        reason="A half retracement that returns to the trough before the old peak.",
        events=tuple(events),
        windows_examined=len(events) + censored,
        qualifier_window_count=len(events),
        censored_count=censored,
    )


def _trailing_return(closes: Sequence[Decimal], index: int, steps: int) -> Decimal | None:
    if index < steps:
        return None
    return closes[index] / closes[index - steps] - 1


def trend_reversals(dates: Sequence[date], closes: Sequence[Decimal]) -> FamilyCount:
    if len(dates) != len(closes):
        raise ProtocolError("trend reversal dates and closes differ in length")
    rule = _rule("trend_reversal")
    steps = int(rule["trailing_steps"])
    horizon = str(rule["horizon_label"])
    returns = [_trailing_return(closes, index, steps) for index in range(len(closes))]
    month_ends = month_end_indices(dates)
    events: list[EventRow] = []
    censored = 0
    for index in range(1, len(closes)):
        previous = returns[index - 1]
        current = returns[index]
        if previous is None or current is None or previous == 0 or current == 0:
            continue
        if (previous > 0) == (current > 0):
            continue
        new_positive = current > 0
        later = [point for point in month_ends if point > index]
        if not later:
            censored += 1
            continue
        confirm = later[0]
        held = returns[confirm]
        if held is None or held == 0 or (held > 0) != new_positive:
            continue
        events.append(
            _row(
                "trend_reversal",
                horizon,
                closes,
                index,
                confirm,
                confirm,
                uses_later=True,
                observable=False,
                detail=(
                    f"252-session trailing return changed sign to {decimal_text(current)}. "
                    "The next month-end still holds that sign. The confirmation uses a later close."
                ),
            )
        )
    return FamilyCount(
        family="trend_reversal",
        horizon_label=horizon,
        status="catalogued",
        reason=(
            "A 252-session sign change confirmed at the next month-end. "
            "Observable at the event date is false."
        ),
        events=tuple(events),
        windows_examined=max(len(closes) - steps, 0),
        qualifier_window_count=len(events),
        censored_count=censored,
    )


def _session_volatility(closes: Sequence[Decimal]) -> list[Decimal | None]:
    return [predictor_value(closes, index, "volatility_63") for index in range(len(closes))]


def volatility_transitions(closes: Sequence[Decimal]) -> FamilyCount:
    rule = _rule("volatility_transition")
    window = int(rule["median_sessions"])
    values = _session_volatility(closes)
    events: list[EventRow] = []
    previous_gap: Decimal | None = None
    for index, value in enumerate(values):
        if value is None or index + 1 < window:
            previous_gap = None
            continue
        sample = values[index - window + 1 : index + 1]
        if any(item is None for item in sample):
            previous_gap = None
            continue
        median = _median_ready(sample)
        gap = value - median
        if previous_gap is not None and previous_gap != 0 and gap != 0:
            if (previous_gap > 0) != (gap > 0):
                start = max(0, index - int(rule["volatility_steps"]))
                events.append(
                    _row(
                        "volatility_transition",
                        "63s",
                        closes,
                        start,
                        index,
                        index,
                        uses_later=False,
                        observable=True,
                        detail=(
                            f"63-session volatility {decimal_text(value)} crossed the trailing "
                            f"252-session median {decimal_text(median)}. The median is trailing."
                        ),
                    )
                )
        previous_gap = gap
    return FamilyCount(
        family="volatility_transition",
        horizon_label="63s",
        status="catalogued",
        reason="A 63-session volatility crossing its trailing 252-session median.",
        events=tuple(events),
        windows_examined=max(len(closes) - window, 0),
        qualifier_window_count=len(events),
        censored_count=0,
    )


def _median_ready(sample: Sequence[Decimal | None]) -> Decimal:
    numbers = [item for item in sample if item is not None]
    ordered = sorted(numbers)
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def catalogue_new_families(
    dates: Sequence[date],
    closes: Sequence[Decimal],
) -> tuple[FamilyCount, ...]:
    """The five families added by EVT-DEF-002. Version 1 families are not rebuilt."""
    if len(dates) != len(closes):
        raise ProtocolError("dates and closes differ in length")
    counts = [
        *sustained_declines(closes),
        persistent_bears(closes),
        failed_recoveries(closes),
        trend_reversals(dates, closes),
        volatility_transitions(closes),
    ]
    return tuple(counts)


def full_sample_median_refused(closes: Sequence[Decimal], index: int) -> None:
    """The volatility median at index must ignore sessions after index and a full-sample spike."""
    trailing = trailing_volatility_median(closes, index)
    if trailing is None:
        return
    spiked = list(closes) + [closes[-1] * Decimal(5)]
    if trailing_volatility_median(spiked, index) != trailing:
        raise ProtocolError("a later close entered the trailing volatility median")
