"""Align a known signal with a later listing return. Missing sessions stay missing."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aqil_research.discovery.calendar import add_months
from aqil_research.discovery.guards import assert_signal_known
from aqil_research.discovery.outcomes import OutcomeError, listing_total_return


@dataclass(frozen=True, slots=True)
class AlignedPair:
    reference_month: date
    decision: date
    entry: date
    exit: date
    signal: Decimal
    forward_return: Decimal


@dataclass(frozen=True, slots=True)
class PairSet:
    pairs: tuple[AlignedPair, ...]
    missing_windows: int
    decision_to_entry_days: tuple[int, ...]


def first_on_or_after(sessions: tuple[date, ...], target: date) -> date | None:
    index = bisect_left(sessions, target)
    if index >= len(sessions):
        return None
    return sessions[index]


def non_overlapping_count(pairs: tuple[AlignedPair, ...] | list[AlignedPair]) -> int:
    """Windows whose entry is on or after the previous exit."""
    count = 0
    next_free: date | None = None
    for pair in sorted(pairs, key=lambda item: (item.entry, item.exit)):
        if next_free is None or pair.entry >= next_free:
            count += 1
            next_free = pair.exit
    return count


def align_forward_returns(
    signal: dict[date, Decimal],
    sessions: tuple[date, ...],
    prices: dict[date, Decimal],
    *,
    horizon_months: int,
    lag_months: int,
    quote_unit: str,
    distribution_policy: str,
    inception_bound: date | None,
    dividend: Decimal | None,
    maximum_gap_days: int,
) -> PairSet:
    """Pair each reference month with the next stored session, without jumping a long gap."""
    if maximum_gap_days < 0:
        raise ValueError("the decision-to-entry gap cannot be negative")
    aligned: list[AlignedPair] = []
    missing = 0
    gaps: list[int] = []
    for reference in sorted(signal):
        decision = add_months(reference, lag_months)
        assert_signal_known(reference, lag_months, decision)
        entry = first_on_or_after(sessions, decision)
        if entry is None or entry not in prices or (entry - decision).days > maximum_gap_days:
            missing += 1
            continue
        exit_session = first_on_or_after(sessions, add_months(entry, horizon_months))
        if exit_session is None or exit_session not in prices:
            missing += 1
            continue
        try:
            forward = listing_total_return(
                distribution_policy=distribution_policy,
                start_value=prices[entry],
                end_value=prices[exit_session],
                quote_unit=quote_unit,
                dividend=dividend,
                uses_adjusted_close=True,
                inception_bound=inception_bound,
                entry=entry,
                decision=decision,
            )
        except OutcomeError:
            missing += 1
            continue
        aligned.append(
            AlignedPair(
                reference_month=reference,
                decision=decision,
                entry=entry,
                exit=exit_session,
                signal=signal[reference],
                forward_return=forward,
            )
        )
        gaps.append((entry - decision).days)
    return PairSet(
        pairs=tuple(aligned), missing_windows=missing, decision_to_entry_days=tuple(gaps)
    )


def split_holdout(
    pairs: tuple[AlignedPair, ...],
    holdout_on_or_after: date,
) -> tuple[tuple[AlignedPair, ...], tuple[AlignedPair, ...]]:
    training = tuple(pair for pair in pairs if pair.decision < holdout_on_or_after)
    holdout = tuple(pair for pair in pairs if pair.decision >= holdout_on_or_after)
    return training, holdout
