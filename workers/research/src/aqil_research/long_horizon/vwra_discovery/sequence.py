"""The one frozen sequence. Thresholds are not retuned on a result."""

from __future__ import annotations

from decimal import Decimal

from aqil_research.long_horizon.etf_protocol.rules import conjunction_status
from aqil_research.long_horizon.vwra_discovery.specification import (
    ADVANCE_MINIMUM,
    SEQUENCE,
    sequence_finding,
)


def deceleration_flags(year_on_year: list[str | None]) -> list[bool]:
    """A negative change in the year-on-year ratio. Not a percentage-point change."""
    flags = [False] * len(year_on_year)
    for index in range(1, len(year_on_year)):
        current = year_on_year[index]
        previous = year_on_year[index - 1]
        if current is None or previous is None:
            continue
        flags[index] = Decimal(current) < Decimal(previous)
    return flags


def sequence_flags(
    year_on_year: list[str | None],
    momentum: list[str | None],
) -> list[bool]:
    """True at the confirmation month-end, one to three month-ends after deceleration."""
    slowed = deceleration_flags(year_on_year)
    follow = tuple(int(item) for item in SEQUENCE["follow_month_ends"])
    flags = [False] * len(year_on_year)
    for index, value in enumerate(momentum):
        if value is None or Decimal(value) <= 0:
            continue
        for lag in follow:
            earlier = index - lag
            if earlier >= 0 and slowed[earlier]:
                flags[index] = True
                break
    return flags


def advance_flags(returns: list[str | None]) -> list[bool | None]:
    floor = Decimal(ADVANCE_MINIMUM)
    labelled: list[bool | None] = []
    for value in returns:
        if value is None:
            labelled.append(None)
        else:
            labelled.append(Decimal(value) >= floor)
    return labelled


def sequence_counts(
    *,
    sequence: list[bool],
    deceleration: list[bool],
    momentum_positive: list[bool],
    advances: list[bool | None],
) -> dict[str, int | str]:
    """Compare the sequence with each leg. The outcome is not an input."""
    eligible = 0
    pair_count = 0
    pair_advances = 0
    false_positives = 0
    missed = 0
    decel_count = 0
    decel_advances = 0
    momentum_count = 0
    momentum_advances = 0
    advance_count = 0
    for flag, slowed, moving, advance in zip(
        sequence, deceleration, momentum_positive, advances, strict=True
    ):
        if advance is None:
            continue
        eligible += 1
        if advance:
            advance_count += 1
        if flag:
            pair_count += 1
            if advance:
                pair_advances += 1
            else:
                false_positives += 1
        elif advance:
            missed += 1
        if slowed:
            decel_count += 1
            if advance:
                decel_advances += 1
        if moving:
            momentum_count += 1
            if advance:
                momentum_advances += 1
    status = conjunction_status(
        eligible=eligible,
        pair_count=pair_count,
        pair_advances=pair_advances,
        drawdown_count=decel_count,
        drawdown_advances=decel_advances,
        volatility_count=momentum_count,
        volatility_advances=momentum_advances,
        advances=advance_count,
    )
    return {
        "eligible": eligible,
        "pair_count": pair_count,
        "pair_advances": pair_advances,
        "false_positives": false_positives,
        "missed_advances": missed,
        "deceleration_count": decel_count,
        "deceleration_advances": decel_advances,
        "momentum_count": momentum_count,
        "momentum_advances": momentum_advances,
        "advances": advance_count,
        "comparison_status": status,
        "finding_class": sequence_finding(status),
    }
