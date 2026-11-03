"""Canonical text for exact decimal evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def decimal_text(value: Decimal) -> str:
    """Stable, non-scientific text. Trailing zeros after the point are removed."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-"}:
        return "0"
    return text


def canonical_json(document: object) -> str:
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        default=_encode,
    )


def _encode(value: Any) -> str:
    if isinstance(value, Decimal):
        return decimal_text(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"cannot canonicalise {type(value).__name__}")


def sha256_document(document: object) -> str:
    payload = canonical_json(document).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
