"""Price-event identification. Callers pass closes. This module does not read a database."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from aqil_research.long_horizon.events.definition import EVENT_DEFINITION, VWRA_FIRST_SESSION
from aqil_research.long_horizon.money import decimal_text


class EventDefinitionError(ValueError):
    """A series or a rule breach that must not be repaired silently."""


@dataclass(frozen=True)
class EventRow:
    family: str
    horizon_label: str
    start_index: int
    end_index: int
    label_confirmed_index: int | None
    label_uses_later_prices: bool
    historically_observable_at_event_date: bool
    price_return: str
    max_intervening_drawdown: str
    up_session_fraction: str
    detail: str = ""


@dataclass(frozen=True)
class FamilyCount:
    family: str
    horizon_label: str
    status: str
    reason: str
    events: tuple[EventRow, ...]
    windows_examined: int
    qualifier_window_count: int | None
    censored_count: int


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _definition() -> dict[str, object]:
    return EVENT_DEFINITION


def assert_listing_series(
    symbol: str,
    dates: Sequence[date],
    closes: Sequence[Decimal],
    currency: str,
    quote_unit: str,
) -> None:
    if len(dates) != len(closes):
        raise EventDefinitionError(f"{symbol} dates and closes differ in length")
    if quote_unit != currency:
        raise EventDefinitionError(f"{symbol} quote unit {quote_unit} is not {currency}")
    previous: date | None = None
    for session, price in zip(dates, closes, strict=True):
        if previous is not None and session <= previous:
            raise EventDefinitionError(f"{symbol} sessions are not strictly increasing")
        if price <= 0:
            raise EventDefinitionError(f"{symbol} has a non-positive close")
        previous = session
    if symbol == "VWRA":
        first = date.fromisoformat(VWRA_FIRST_SESSION)
        for session in dates:
            if session < first:
                raise EventDefinitionError(
                    "VWRA observations before 2019-07-25 are refused and are not manufactured"
                )


def running_drawdown(closes: Sequence[Decimal]) -> Decimal:
    """Most negative close-over-running-peak return. Zero when the path never falls."""
    if not closes:
        raise EventDefinitionError("drawdown is undefined for an empty path")
    peak = closes[0]
    worst = Decimal(0)
    for price in closes:
        if price > peak:
            peak = price
        change = price / peak - 1
        if change < worst:
            worst = change
    return worst


def up_session_fraction(closes: Sequence[Decimal]) -> Decimal:
    steps = len(closes) - 1
    if steps <= 0:
        return Decimal(0)
    rises = sum(1 for left, right in zip(closes, closes[1:], strict=False) if right > left)
    return Decimal(rises) / Decimal(steps)


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
    observable_at_event_date: bool,
    detail: str = "",
) -> EventRow:
    price_return, drawdown, fraction = _metrics(closes, start, end)
    return EventRow(
        family=family,
        horizon_label=horizon,
        start_index=start,
        end_index=end,
        label_confirmed_index=confirmed,
        label_uses_later_prices=uses_later,
        historically_observable_at_event_date=observable_at_event_date,
        price_return=price_return,
        max_intervening_drawdown=drawdown,
        up_session_fraction=fraction,
        detail=detail,
    )


def sustained_advances(closes: Sequence[Decimal]) -> list[FamilyCount]:
    rules = _definition()["sustained_advance"]
    assert isinstance(rules, dict)
    counts: list[FamilyCount] = []
    for horizon, raw in rules.items():
        assert isinstance(raw, dict)
        steps = int(raw["steps"])
        minimum = _decimal(raw["minimum_return"])
        cap = _decimal(raw["maximum_drawdown"])
        up_floor = _decimal(raw["minimum_up_session_fraction"])
        qualifiers: list[int] = []
        events: list[EventRow] = []
        examined = 0
        index = 0
        last = len(closes) - 1
        while index + steps <= last:
            examined += 1
            window = closes[index : index + steps + 1]
            price_return = window[-1] / window[0] - 1
            drawdown = running_drawdown(window)
            fraction = up_session_fraction(window)
            qualifies = price_return >= minimum and drawdown >= -cap and fraction >= up_floor
            if qualifies:
                qualifiers.append(index)
            index += 1
        cursor = 0
        while cursor + steps <= last:
            window = closes[cursor : cursor + steps + 1]
            price_return = window[-1] / window[0] - 1
            drawdown = running_drawdown(window)
            fraction = up_session_fraction(window)
            if price_return >= minimum and drawdown >= -cap and fraction >= up_floor:
                events.append(
                    _row(
                        "sustained_advance",
                        horizon,
                        closes,
                        cursor,
                        cursor + steps,
                        cursor + steps,
                        uses_later=True,
                        observable_at_event_date=False,
                    )
                )
                cursor += steps
            else:
                cursor += 1
        counts.append(
            FamilyCount(
                family="sustained_advance",
                horizon_label=horizon,
                status="catalogued",
                reason=(
                    "Earliest qualifying window, then resume at the end session. "
                    "Overlapping qualifiers are counted and are not separate events."
                ),
                events=tuple(events),
                windows_examined=examined,
                qualifier_window_count=len(qualifiers),
                censored_count=0,
            )
        )
    return counts


@dataclass(frozen=True)
class _Swing:
    trough_index: int
    peak_index: int
    confirm_index: int


def confirmed_upswings(
    closes: Sequence[Decimal],
    rise: Decimal,
    fall: Decimal,
) -> tuple[list[_Swing], int]:
    """Barrier upswings. A terminal rise without the confirming fall is censored."""
    if len(closes) == 0:
        return [], 0
    trough = 0
    peak = 0
    seeking_fall = False
    found: list[_Swing] = []
    for index in range(1, len(closes)):
        price = closes[index]
        if not seeking_fall:
            if price <= closes[trough]:
                trough = index
                peak = index
                continue
            if price / closes[trough] - 1 >= rise:
                seeking_fall = True
                peak = index
            continue
        if price >= closes[peak]:
            peak = index
        if price / closes[peak] - 1 <= -fall:
            found.append(_Swing(trough, peak, index))
            trough = index
            peak = index
            seeking_fall = False
    censored = 1 if seeking_fall else 0
    return found, censored


def persistent_and_early_bulls(closes: Sequence[Decimal]) -> list[FamilyCount]:
    rule = _definition()["persistent_bull"]
    early = _definition()["early_bull"]
    assert isinstance(rule, dict)
    assert isinstance(early, dict)
    rise = _decimal(rule["minimum_rise"])
    fall = _decimal(rule["confirming_decline"])
    minimum_steps = int(rule["minimum_session_steps"])
    early_steps = int(early["session_steps"])
    swings, censored = confirmed_upswings(closes, rise, fall)
    bulls: list[EventRow] = []
    early_rows: list[EventRow] = []
    for swing in swings:
        steps = swing.peak_index - swing.trough_index
        gained = closes[swing.peak_index] / closes[swing.trough_index] - 1
        if steps < minimum_steps or gained < rise:
            continue
        bulls.append(
            _row(
                "persistent_bull",
                "20pct",
                closes,
                swing.trough_index,
                swing.peak_index,
                swing.confirm_index,
                uses_later=True,
                observable_at_event_date=False,
            )
        )
        early_end = swing.trough_index + early_steps
        if early_end < swing.peak_index:
            early_rows.append(
                _row(
                    "early_bull",
                    "63s",
                    closes,
                    swing.trough_index,
                    early_end,
                    swing.confirm_index,
                    uses_later=True,
                    observable_at_event_date=False,
                )
            )
    return [
        FamilyCount(
            family="persistent_bull",
            horizon_label="20pct",
            status="catalogued",
            reason=(
                "A 20 percent rise confirmed by a later 20 percent decline. "
                "An unconfirmed terminal rise is censored and is not a bull event."
            ),
            events=tuple(bulls),
            windows_examined=len(swings),
            qualifier_window_count=len(swings),
            censored_count=censored,
        ),
        FamilyCount(
            family="early_bull",
            horizon_label="63s",
            status="catalogued",
            reason=(
                "The first 63 sessions of a persistent bull, and only when that "
                "slice ends before the peak. The label uses the later confirmation."
            ),
            events=tuple(early_rows),
            windows_examined=len(bulls),
            qualifier_window_count=len(early_rows),
            censored_count=0,
        ),
    ]


def recoveries(closes: Sequence[Decimal]) -> list[FamilyCount]:
    rule = _definition()["drawdown_recovery"]
    early_rule = _definition()["early_recovery"]
    assert isinstance(rule, dict)
    assert isinstance(early_rule, dict)
    decline = _decimal(rule["minimum_decline"])
    retracement = _decimal(early_rule["retracement"])
    early_steps = int(early_rule["session_steps"])
    recoveries_found: list[EventRow] = []
    early_rows: list[EventRow] = []
    peak_index = 0
    trough_index = 0
    in_drawdown = False
    if closes:
        for index in range(1, len(closes)):
            price = closes[index]
            if not in_drawdown:
                if price >= closes[peak_index]:
                    peak_index = index
                    trough_index = index
                elif price / closes[peak_index] - 1 <= -decline:
                    in_drawdown = True
                    trough_index = index
                continue
            if price < closes[trough_index]:
                trough_index = index
            if price >= closes[peak_index]:
                recoveries_found.append(
                    _row(
                        "drawdown_recovery",
                        "15pct",
                        closes,
                        trough_index,
                        index,
                        index,
                        uses_later=True,
                        observable_at_event_date=False,
                    )
                )
                half = (
                    closes[trough_index] + (closes[peak_index] - closes[trough_index]) * retracement
                )
                cap = min(trough_index + early_steps, index - 1)
                chosen: int | None = None
                if cap > trough_index:
                    for cursor in range(trough_index + 1, cap + 1):
                        if closes[cursor] >= half:
                            chosen = cursor
                            break
                    if chosen is None:
                        chosen = cap
                if chosen is not None and trough_index < chosen < index:
                    early_rows.append(
                        _row(
                            "early_recovery",
                            "63s_or_half",
                            closes,
                            trough_index,
                            chosen,
                            index,
                            uses_later=True,
                            observable_at_event_date=False,
                        )
                    )
                in_drawdown = False
                peak_index = index
                trough_index = index
    censored = 1 if in_drawdown else 0
    return [
        FamilyCount(
            family="drawdown_recovery",
            horizon_label="15pct",
            status="catalogued",
            reason=(
                "A decline of at least 15 percent from a peak, then the first close "
                "back at that peak. An open drawdown is censored, not a recovery."
            ),
            events=tuple(recoveries_found),
            windows_examined=len(recoveries_found) + censored,
            qualifier_window_count=len(recoveries_found),
            censored_count=censored,
        ),
        FamilyCount(
            family="early_recovery",
            horizon_label="63s_or_half",
            status="catalogued",
            reason=(
                "The earlier of 63 sessions and a 50 percent retracement, inside a "
                "completed recovery, and strictly before the full recovery."
            ),
            events=tuple(early_rows),
            windows_examined=len(recoveries_found),
            qualifier_window_count=len(early_rows),
            censored_count=0,
        ),
    ]


def sideways_then_advance(closes: Sequence[Decimal]) -> FamilyCount:
    rule = _definition()["sideways_then_advance"]
    assert isinstance(rule, dict)
    side = int(rule["sideways_steps"])
    advance = int(rule["advance_steps"])
    max_abs = _decimal(rule["maximum_absolute_return"])
    max_range = _decimal(rule["maximum_range_over_start"])
    max_dd = _decimal(rule["maximum_drawdown"])
    minimum = _decimal(rule["minimum_advance_return"])
    events: list[EventRow] = []
    examined = 0
    span = side + advance
    cursor = 0
    last = len(closes) - 1
    while cursor + span <= last:
        examined += 1
        sideways = closes[cursor : cursor + side + 1]
        start = sideways[0]
        absolute = abs(sideways[-1] / start - 1)
        width = (max(sideways) - min(sideways)) / start
        drawdown = abs(running_drawdown(sideways))
        later = closes[cursor + span] / closes[cursor + side] - 1
        if absolute <= max_abs and width <= max_range and drawdown <= max_dd and later >= minimum:
            events.append(
                _row(
                    "sideways_then_advance",
                    "126s_then_63s",
                    closes,
                    cursor,
                    cursor + span,
                    cursor + span,
                    uses_later=True,
                    observable_at_event_date=False,
                )
            )
            cursor += span
        else:
            cursor += 1
    overlapping = 0
    probe = 0
    while probe + span <= last:
        sideways = closes[probe : probe + side + 1]
        start = sideways[0]
        absolute = abs(sideways[-1] / start - 1)
        width = (max(sideways) - min(sideways)) / start
        drawdown = abs(running_drawdown(sideways))
        later = closes[probe + span] / closes[probe + side] - 1
        if absolute <= max_abs and width <= max_range and drawdown <= max_dd and later >= minimum:
            overlapping += 1
        probe += 1
    return FamilyCount(
        family="sideways_then_advance",
        horizon_label="126s_then_63s",
        status="catalogued",
        reason=(
            "A 126-session sideways window followed by a 63-session advance of at "
            "least 10 percent. The catalogue keeps the earliest window."
        ),
        events=tuple(events),
        windows_examined=examined,
        qualifier_window_count=overlapping,
        censored_count=0,
    )


def failed_rallies(closes: Sequence[Decimal]) -> FamilyCount:
    rule = _definition()["failed_rally"]
    assert isinstance(rule, dict)
    attempt = _decimal(rule["attempt_rise"])
    failure = _decimal(rule["failure_decline_from_attempt_peak"])
    success = _decimal(rule["not_failed_if_rise_reaches"])
    events: list[EventRow] = []
    if closes:
        trough = 0
        peak = 0
        in_attempt = False
        for index in range(1, len(closes)):
            price = closes[index]
            if not in_attempt:
                if price <= closes[trough]:
                    trough = index
                    peak = index
                    continue
                rise = price / closes[trough] - 1
                if rise >= success:
                    trough = index
                    peak = index
                    continue
                if rise >= attempt:
                    in_attempt = True
                    peak = index
                continue
            if price >= closes[peak]:
                peak = index
                if closes[peak] / closes[trough] - 1 >= success:
                    in_attempt = False
                    trough = index
                    peak = index
                    continue
            if price / closes[peak] - 1 <= -failure:
                rise = closes[peak] / closes[trough] - 1
                if rise < success and price <= closes[trough]:
                    events.append(
                        _row(
                            "failed_rally",
                            "8pct",
                            closes,
                            trough,
                            index,
                            index,
                            uses_later=True,
                            observable_at_event_date=False,
                        )
                    )
                in_attempt = False
                trough = index
                peak = index
    return FamilyCount(
        family="failed_rally",
        horizon_label="8pct",
        status="catalogued",
        reason=(
            "An 8 percent rise that falls 8 percent back to or below its trough "
            "before the rise reaches 15 percent. The confirmation uses later prices."
        ),
        events=tuple(events),
        windows_examined=max(len(closes) - 1, 0),
        qualifier_window_count=len(events),
        censored_count=0,
    )


def negative_and_flat(closes: Sequence[Decimal]) -> list[FamilyCount]:
    flat_rule = _definition()["flat_market"]
    assert isinstance(flat_rule, dict)
    steps = int(flat_rule["steps"])
    band = _decimal(flat_rule["absolute_return_at_most"])
    flat_rows: list[EventRow] = []
    negative_rows: list[EventRow] = []
    examined = 0
    cursor = 0
    last = len(closes) - 1
    while cursor + steps <= last:
        examined += 1
        end = cursor + steps
        price_return = closes[end] / closes[cursor] - 1
        if abs(price_return) <= band:
            flat_rows.append(
                _row(
                    "flat_market",
                    "6m",
                    closes,
                    cursor,
                    end,
                    end,
                    uses_later=True,
                    observable_at_event_date=False,
                )
            )
        elif price_return < 0:
            negative_rows.append(
                _row(
                    "negative_market",
                    "6m",
                    closes,
                    cursor,
                    end,
                    end,
                    uses_later=True,
                    observable_at_event_date=False,
                )
            )
        cursor += steps
    return [
        FamilyCount(
            family="negative_market",
            horizon_label="6m",
            status="catalogued",
            reason=(
                "Fixed 126-session grid from the first session. A window inside "
                "the flat band is not also counted as negative."
            ),
            events=tuple(negative_rows),
            windows_examined=examined,
            qualifier_window_count=len(negative_rows),
            censored_count=0,
        ),
        FamilyCount(
            family="flat_market",
            horizon_label="6m",
            status="catalogued",
            reason=(
                "Fixed 126-session grid. Absolute price return of at most 3 percent "
                "is flat, including a small negative return."
            ),
            events=tuple(flat_rows),
            windows_examined=examined,
            qualifier_window_count=len(flat_rows),
            censored_count=0,
        ),
    ]


def _blocked(family: str, reason: str) -> FamilyCount:
    return FamilyCount(
        family=family,
        horizon_label="not_applicable",
        status="blocked",
        reason=reason,
        events=(),
        windows_examined=0,
        qualifier_window_count=None,
        censored_count=0,
    )


def single_listing_counts(closes: Sequence[Decimal]) -> list[FamilyCount]:
    blocked = _definition()["blocked_families"]
    assert isinstance(blocked, list)
    total = _definition()["total_return_block_reason"]
    rally = _definition()["rally_despite_deterioration"]
    assert isinstance(rally, dict)
    counts: list[FamilyCount] = []
    counts.extend(sustained_advances(closes))
    counts.extend(persistent_and_early_bulls(closes))
    counts.extend(recoveries(closes))
    counts.append(sideways_then_advance(closes))
    counts.append(failed_rallies(closes))
    counts.extend(negative_and_flat(closes))
    counts.append(_blocked("total_return_advance", str(total)))
    counts.append(_blocked("rally_despite_deterioration", str(rally["reason"])))
    return counts


def session_on_or_before(
    dates: Sequence[date],
    day: date,
    tolerance_days: int,
) -> int | None:
    found: int | None = None
    for index, session in enumerate(dates):
        if session <= day and (day - session) <= timedelta(days=tolerance_days):
            found = index
        elif session > day:
            break
    return found


def _peer_return(
    dates: Sequence[date],
    closes: Sequence[Decimal],
    day: date,
    steps: int,
    tolerance_days: int,
) -> Decimal | None:
    index = session_on_or_before(dates, day, tolerance_days)
    if index is None or index < steps:
        return None
    return closes[index] / closes[index - steps] - 1


def _median(values: Sequence[Decimal]) -> Decimal:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        raise EventDefinitionError("median is undefined for an empty list")
    mid = count // 2
    if count % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal(2)


@dataclass(frozen=True)
class ListingSeries:
    symbol: str
    currency: str
    dates: tuple[date, ...]
    closes: tuple[Decimal, ...]


def relative_and_leadership(
    listings: Sequence[ListingSeries],
) -> dict[str, list[FamilyCount]]:
    relative_rule = _definition()["relative_outperformance"]
    lead_rule = _definition()["leadership_transition"]
    assert isinstance(relative_rule, dict)
    assert isinstance(lead_rule, dict)
    steps = int(relative_rule["steps"])
    excess_floor = _decimal(relative_rule["minimum_excess_over_peer_median"])
    peers_required = int(relative_rule["minimum_peers"])
    tolerance = int(relative_rule["peer_tolerance_days"])
    peer_currency = str(relative_rule["peer_currency"])
    lead_gap = _decimal(lead_rule["minimum_excess_over_previous_leader"])
    lead_names = int(lead_rule["minimum_eligible_symbols"])
    by_symbol = {item.symbol: item for item in listings}
    usd = [item for item in listings if item.currency == peer_currency]
    result: dict[str, list[FamilyCount]] = {}
    for listing in listings:
        if listing.currency != peer_currency:
            result[listing.symbol] = [
                _blocked(
                    "relative_outperformance",
                    (
                        f"{listing.symbol} is {listing.currency}. Cross-currency "
                        "relative performance is blocked because no foreign-exchange "
                        "conversion is applied."
                    ),
                ),
                _blocked(
                    "leadership_transition",
                    (
                        f"{listing.symbol} is {listing.currency}. Leadership inside "
                        "the US-dollar listings is not extended by a conversion."
                    ),
                ),
            ]
            continue
        events: list[EventRow] = []
        examined = 0
        end = steps
        while end < len(listing.closes):
            examined += 1
            day = listing.dates[end]
            own = listing.closes[end] / listing.closes[end - steps] - 1
            peer_returns: list[Decimal] = []
            for peer in usd:
                if peer.symbol == listing.symbol:
                    continue
                peer_value = _peer_return(peer.dates, peer.closes, day, steps, tolerance)
                if peer_value is not None:
                    peer_returns.append(peer_value)
            if len(peer_returns) >= peers_required and own - _median(peer_returns) >= excess_floor:
                events.append(
                    _row(
                        "relative_outperformance",
                        "12m",
                        listing.closes,
                        end - steps,
                        end,
                        end,
                        uses_later=True,
                        observable_at_event_date=False,
                    )
                )
            end += steps
        result.setdefault(listing.symbol, []).append(
            FamilyCount(
                family="relative_outperformance",
                horizon_label="12m",
                status="catalogued",
                reason=(
                    "Fixed 252-session grid. Excess is over the median of at least "
                    "three other US-dollar listings, using each listing's own sessions."
                ),
                events=tuple(events),
                windows_examined=examined,
                qualifier_window_count=len(events),
                censored_count=0,
            )
        )
    transitions: dict[str, list[EventRow]] = {item.symbol: [] for item in usd}
    month_ends: dict[tuple[int, int], date] = {}
    for listing in usd:
        for session in listing.dates:
            key = (session.year, session.month)
            if key not in month_ends or session > month_ends[key]:
                month_ends[key] = session
    previous: str | None = None
    for key in sorted(month_ends):
        day = month_ends[key]
        returns: dict[str, Decimal] = {}
        for listing in usd:
            value = _peer_return(listing.dates, listing.closes, day, steps, tolerance)
            if value is not None:
                returns[listing.symbol] = value
        if len(returns) < lead_names:
            continue
        best = max(returns.values())
        leader = min(symbol for symbol, value in returns.items() if value == best)
        if previous is None:
            previous = leader
            continue
        if (
            leader != previous
            and previous in returns
            and returns[leader] - returns[previous] >= lead_gap
        ):
            listing = by_symbol[leader]
            index = session_on_or_before(listing.dates, day, tolerance)
            if index is None:
                raise EventDefinitionError("leader session disappeared")
            start = index - steps
            spread = returns[leader] - returns[previous]
            transitions[leader].append(
                _row(
                    "leadership_transition",
                    "12m",
                    listing.closes,
                    start,
                    index,
                    index,
                    uses_later=False,
                    observable_at_event_date=True,
                    detail=(
                        f"previous_leader={previous}; excess={decimal_text(spread)}; not a signal"
                    ),
                )
            )
        previous = leader
    for listing in usd:
        rows = tuple(transitions[listing.symbol])
        result[listing.symbol].append(
            FamilyCount(
                family="leadership_transition",
                horizon_label="12m",
                status="catalogued",
                reason=(
                    "Month-end leader among US-dollar listings with a 252-session "
                    "price return. Ties use alphabetical ticker. The spread uses "
                    "only closes on or before the month-end. It is still not a signal."
                ),
                events=rows,
                windows_examined=len(month_ends),
                qualifier_window_count=len(rows),
                censored_count=0,
            )
        )
    return result


def catalogue_listing(
    listing: ListingSeries,
    cross_listing: list[FamilyCount],
) -> list[FamilyCount]:
    assert_listing_series(
        listing.symbol,
        listing.dates,
        listing.closes,
        listing.currency,
        listing.currency,
    )
    counts = single_listing_counts(listing.closes)
    counts.extend(cross_listing)
    return counts
