"""One local request ledger for the TradingView Data API.

A reservation is written before the socket opens. Unused phase ceiling rolls
forward. The hard cap includes failures. The ledger stores no credential.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_ORIGIN = "https://api.tradingviewapi.com"
HARD_CAP = 60
PHASE_CEILINGS: tuple[tuple[str, int], ...] = (
    ("identity", 8),
    ("priority_history", 12),
    ("adjustment", 8),
    ("remaining", 22),
    ("exceptions", 10),
)
_COUNTED = frozenset({"reserved", "ok", "error"})


class BudgetStop(RuntimeError):
    """Raised when another HTTP call must not be made."""


@dataclass(frozen=True)
class Reservation:
    call_id: str
    phase: str
    method: str
    path: str


class BudgetLedger:
    """Persistent cap. One process is the coordinator."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self.path = path
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleep = sleeper or _default_sleep
        self._monotonic = monotonic
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"hard_cap": HARD_CAP, "halt_reason": None, "calls": []})

    def remaining(self, phase: str) -> int:
        state = self._read()
        return _remaining(state, phase)

    def used(self) -> int:
        state = self._read()
        return sum(1 for row in state["calls"] if row["status"] in _COUNTED)

    def reserve(self, phase: str, method: str, path: str) -> Reservation:
        """Count one call before it is sent. The path must stay on the API host."""

        _require_api_path(path)
        state = self._read()
        if state.get("halt_reason"):
            raise BudgetStop(str(state["halt_reason"]))
        if phase not in dict(PHASE_CEILINGS):
            raise BudgetStop(f"unknown phase {phase}")
        if _remaining(state, phase) < 1:
            raise BudgetStop(f"phase {phase} has no remaining request budget")
        call_id = f"{len(state['calls']) + 1:04d}"
        state["calls"].append(
            {
                "id": call_id,
                "phase": phase,
                "method": method,
                "path": path,
                "status": "reserved",
                "http_status": None,
                "reserved_at": self._clock().isoformat(),
                "finished_at": None,
            }
        )
        self._write(state)
        self._wait_turn(state)
        return Reservation(call_id, phase, method, path)

    def complete(self, reservation: Reservation, *, http_status: int) -> None:
        state = self._read()
        row = _find(state, reservation.call_id)
        row["status"] = "ok" if 200 <= http_status < 300 else "error"
        row["http_status"] = http_status
        row["finished_at"] = self._clock().isoformat()
        if http_status in {401, 403}:
            state["halt_reason"] = f"HTTP {http_status}; no retry"
        elif http_status >= 500:
            recent = [
                call
                for call in state["calls"]
                if call["status"] == "error" and (call.get("http_status") or 0) >= 500
            ]
            if len(recent) >= 2:
                state["halt_reason"] = "repeated HTTP 5xx"
        elif http_status == 429:
            prior = [
                call
                for call in state["calls"]
                if call["path"] == reservation.path and call.get("http_status") == 429
            ]
            if len(prior) >= 2:
                state["halt_reason"] = "HTTP 429 persisted after the budgeted retry"
        self._write(state)
        if state.get("halt_reason"):
            raise BudgetStop(str(state["halt_reason"]))

    def halt(self, reason: str) -> None:
        state = self._read()
        state["halt_reason"] = reason
        self._write(state)

    def halt_reason(self) -> str | None:
        reason = self._read().get("halt_reason")
        return str(reason) if reason else None

    def _wait_turn(self, state: dict[str, object]) -> None:
        calls = state["calls"]
        if not isinstance(calls, list) or len(calls) < 2:
            return
        previous = calls[-2]
        started = previous.get("reserved_at")
        if not isinstance(started, str):
            return
        elapsed = (self._clock() - _stamp(started)).total_seconds()
        if elapsed < 1:
            self._sleep(1 - elapsed)

    def _read(self) -> dict[str, object]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, state: dict[str, object]) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)


def _remaining(state: dict[str, object], phase: str) -> int:
    calls = state["calls"]
    if not isinstance(calls, list):
        return 0
    used = {name: 0 for name, _ceiling in PHASE_CEILINGS}
    total = 0
    for call in calls:
        if not isinstance(call, dict) or call.get("status") not in _COUNTED:
            continue
        name = str(call.get("phase"))
        if name in used:
            used[name] += 1
            total += 1
    if total >= HARD_CAP:
        return 0
    names = [name for name, _ceiling in PHASE_CEILINGS]
    index = names.index(phase)
    ceilings = dict(PHASE_CEILINGS)
    spent_earlier = sum(used[name] for name in names[:index])
    ceiling_earlier = sum(ceilings[name] for name in names[:index])
    rolled = max(0, ceiling_earlier - spent_earlier)
    phase_left = ceilings[phase] + rolled - used[phase]
    return max(0, min(phase_left, HARD_CAP - total))


def _find(state: dict[str, object], call_id: str) -> dict[str, object]:
    calls = state["calls"]
    if not isinstance(calls, list):
        raise BudgetStop("ledger calls are missing")
    for call in calls:
        if isinstance(call, dict) and call.get("id") == call_id:
            return call
    raise BudgetStop(f"reservation {call_id} is missing")


def _require_api_path(path: str) -> None:
    if path.startswith("/"):
        return
    parsed = urlparse(path)
    if parsed.scheme != "https" or parsed.hostname != "api.tradingviewapi.com":
        raise BudgetStop("requests may go only to https://api.tradingviewapi.com")
    if parsed.username or parsed.password:
        raise BudgetStop("the API URL must not carry user info")


def _stamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _default_sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)


def _default_monotonic() -> float:
    import time

    return time.monotonic()