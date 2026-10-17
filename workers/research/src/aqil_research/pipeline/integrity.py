"""Deterministic research-run payload hashing."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def analytical_payload_hash(payload: dict[str, Any]) -> str:
    """Hash reproducible analytical content; excludes run identity and wall-clock time."""
    excluded = {
        "run_id",
        "executed_at",
        "analytical_payload_hash",
    }
    canonical = {key: value for key, value in sorted(payload.items()) if key not in excluded}
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8",
    )
    return hashlib.sha256(encoded).hexdigest()


def verify_analytical_payload_hash(payload: dict[str, Any]) -> bool:
    """Recompute digest from a saved payload (excluding the stored hash field)."""
    expected = payload.get("analytical_payload_hash", "")
    if not expected:
        return False
    return analytical_payload_hash(payload) == expected
