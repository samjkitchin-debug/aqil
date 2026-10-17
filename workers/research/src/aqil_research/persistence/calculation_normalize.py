"""Normalize method calculation payloads loaded from PostgreSQL JSONB."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any


def _decimal_field(key: str, value: object) -> str:
    parsed = Decimal(str(value))
    if key in ("three_month_average", "prior_twelve_month_low_of_average"):
        return str(parsed.quantize(Decimal("0.01")))
    if key.endswith("percentage_points"):
        return str(parsed.quantize(Decimal("0.01")))
    return str(parsed)


def normalize_calculation_payload(calculation: dict[str, Any] | None) -> dict[str, Any] | None:
    """Stable comparison shape after JSONB round-trip (floats, key order, list types)."""
    if calculation is None:
        return None
    payload = json.loads(json.dumps(calculation, sort_keys=True, default=str))
    for key in (
        "three_month_average",
        "prior_twelve_month_low_of_average",
        "gap_percentage_points",
        "threshold_percentage_points",
    ):
        if key in payload and payload[key] is not None:
            payload[key] = _decimal_field(key, payload[key])
    for list_key in (
        "months_used_for_average",
        "months_used_for_lookback",
        "observation_ids",
        "assumptions",
        "limitations",
    ):
        if list_key in payload and isinstance(payload[list_key], list):
            payload[list_key] = sorted(str(item) for item in payload[list_key])
    for bool_key in ("triggered", "threshold_met", "threshold_crossed"):
        if bool_key in payload:
            payload[bool_key] = bool(payload[bool_key])
    if "evaluation_period" in payload:
        payload["evaluation_period"] = str(payload["evaluation_period"])
    return payload
