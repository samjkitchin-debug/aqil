"""HTTP client that can call only the TradingView Data API host.

The credential is read at call time and is placed only on Authorization.
Successful JSON is cached so a replay does not open a socket.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote, urlencode

from aqil_research.etf.tradingview.budget import ALLOWED_ORIGIN, BudgetLedger, BudgetStop

Transport = Callable[[str, str], tuple[int, dict[str, str], bytes]]
ENV_FILE = Path(__file__).resolve().parents[4] / ".env"
MISSING_KEY_FILE = Path("workers/research/.env")


class TradingViewError(RuntimeError):
    """Raised when a call cannot be used. The message never includes the key."""


def load_api_key(env_file: Path | None = None) -> str:
    """Read TRADINGVIEW_API_KEY from the environment or the gitignored env file."""

    value = os.environ.get("TRADINGVIEW_API_KEY", "").strip()
    if value:
        return value
    path = env_file or ENV_FILE
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, raw = stripped.split("=", 1)
            if name.strip() == "TRADINGVIEW_API_KEY" and raw.strip():
                return raw.strip()
    raise TradingViewError(
        f"TRADINGVIEW_API_KEY is absent. Set it in {MISSING_KEY_FILE.as_posix()} "
        "or in the process environment. No request was sent."
    )


class TradingViewClient:
    """Coordinator-backed GET client. One instance owns the live calls."""

    def __init__(
        self,
        ledger: BudgetLedger,
        cache_dir: Path,
        *,
        api_key: str,
        transport: Transport | None = None,
    ) -> None:
        self.ledger = ledger
        self.cache_dir = cache_dir
        self._api_key = api_key
        self._transport = transport or _urllib_transport
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def search_market(self, phase: str, query: str) -> dict[str, object]:
        path = f"/api/search/market/{quote(query, safe='')}"
        return self.get_json(phase, path, {})

    def price(
        self,
        phase: str,
        symbol: str,
        *,
        adjustment: str,
        range_size: int,
        from_ts: int | None = None,
        to_ts: int | None = None,
    ) -> dict[str, object]:
        query: dict[str, str] = {
            "timeframe": "D",
            "type": "Japanese",
            "adjustment": adjustment,
            "range": str(range_size),
        }
        if from_ts is not None:
            query["from"] = str(from_ts)
        if to_ts is not None:
            query["to"] = str(to_ts)
        path = f"/api/price/{quote(symbol, safe=':')}"
        return self.get_json(phase, path, query)

    def get_json(self, phase: str, path: str, query: dict[str, str]) -> dict[str, object]:
        target = _url(path, query)
        cached = self._read_cache(target)
        if cached is not None:
            return cached
        reservation = self.ledger.reserve(phase, "GET", target)
        status, headers, body = self._transport(target, self._api_key)
        if status == 429:
            self.ledger.complete(reservation, http_status=429)
            self._sleep_retry(headers)
            reservation = self.ledger.reserve(phase, "GET", target)
            status, _headers, body = self._transport(target, self._api_key)
        if status != 200:
            self.ledger.complete(reservation, http_status=status)
            raise TradingViewError(f"HTTP {status} for {path}")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.ledger.complete(reservation, http_status=502)
            raise TradingViewError(f"the response for {path} was not JSON") from exc
        if not isinstance(payload, dict):
            self.ledger.complete(reservation, http_status=502)
            raise TradingViewError(f"the response for {path} was not an object")
        self._write_cache(target, payload)
        self.ledger.complete(reservation, http_status=200)
        return payload

    def _sleep_retry(self, headers: dict[str, str]) -> None:
        raw = headers.get("Retry-After") or headers.get("retry-after") or "1"
        try:
            seconds = float(raw)
        except ValueError:
            seconds = 1
        if seconds < 0:
            seconds = 0
        import time

        time.sleep(seconds)

    def _cache_path(self, target: str) -> Path:
        digest = hashlib.sha256(target.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, target: str) -> dict[str, object] | None:
        path = self._cache_path(target)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        body = payload.get("body") if isinstance(payload, dict) else None
        if not isinstance(body, dict):
            return None
        return body

    def _write_cache(self, target: str, body: dict[str, object]) -> None:
        path = self._cache_path(target)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"url": target, "body": body}, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporary, path)


def _url(path: str, query: dict[str, str]) -> str:
    if not path.startswith("/"):
        raise BudgetStop("only relative API paths are requested")
    suffix = f"?{urlencode(query)}" if query else ""
    return f"{ALLOWED_ORIGIN}{path}{suffix}"


def _urllib_transport(url: str, api_key: str) -> tuple[int, dict[str, str], bytes]:
    if not url.startswith(f"{ALLOWED_ORIGIN}/"):
        raise BudgetStop("requests may go only to https://api.tradingviewapi.com")
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()