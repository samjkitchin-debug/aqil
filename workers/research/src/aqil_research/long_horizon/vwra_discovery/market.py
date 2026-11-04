"""Trailing market transforms from closes on or before the anchor."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from aqil_research.long_horizon.money import decimal_text
from aqil_research.long_horizon.state_atlas.features import (
    _persistence,
    sample_standard_deviation,
)


def _window(closes: Sequence[Decimal], index: int, steps: int) -> Sequence[Decimal] | None:
    if index < 0 or index >= len(closes) or index < steps:
        return None
    return closes[: index + 1][index - steps : index + 1]


def downside_volatility(closes: Sequence[Decimal], index: int, steps: int) -> str | None:
    """Sample standard deviation of strictly negative simple returns in the window.

    Fewer than two negative returns is insufficient. No later close is used.
    """
    window = _window(closes, index, steps)
    if window is None:
        return None
    returns = [right / left - 1 for left, right in zip(window, window[1:], strict=False)]
    negative = [item for item in returns if item < 0]
    deviation = sample_standard_deviation(negative)
    if deviation is None:
        return None
    return decimal_text(deviation)


def trend_persistence(closes: Sequence[Decimal], index: int, steps: int) -> str | None:
    """The atlas persistence run on closes inside the trailing window."""
    window = _window(closes, index, steps)
    if window is None:
        return None
    value = _persistence(window)
    return value.value
