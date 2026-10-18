"""Pre-release Sahm assessment for one Employment Situation release.

This does not forecast the unemployment rate. It records the published baseline
and the one-decimal rate that would make the published Sahm gap reach 0.50.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.sahm import (
    SAHM_METHOD_ID,
    SAHM_METHOD_VERSION,
    SahmConfig,
    SahmMethodError,
    _add_months,
    run_sahm,
)

# 6 November 2026, 08:30 US Eastern standard time (daylight saving ended 1 November 2026).
OCTOBER_2026_RELEASE_AT = datetime(2026, 11, 6, 13, 30, tzinfo=UTC)
OCTOBER_2026_PERIOD = "2026-10-01"
NO_FORECAST_STATEMENT = "No directional unemployment-rate forecast was made."


class ProspectiveAssessmentError(Exception):
    """The assessment cannot be frozen or evaluated."""


def october_rate_that_reaches_threshold(
    by_period: dict,
    evaluation_period,
    config: SahmConfig = SAHM_PUBLISHED,
) -> Decimal:
    """Smallest one-decimal unemployment rate that makes the Sahm gap at least 0.50.

    The search respects the implementation's rounding. It does not interpolate a rate
    the published series cannot print.
    """
    from datetime import date

    if not isinstance(evaluation_period, date):
        raise ProspectiveAssessmentError("evaluation_period must be a date")
    prior_months = {month: row for month, row in by_period.items() if month != evaluation_period}
    if evaluation_period not in by_period and len(prior_months) == len(by_period):
        template = next(iter(by_period.values()))
    else:
        template = by_period[evaluation_period]

    found: Decimal | None = None
    candidate = Decimal("0.0")
    while candidate <= Decimal("30.0"):
        trial = dict(prior_months)
        trial[evaluation_period] = template.model_copy(
            update={"period_start": evaluation_period, "raw_value": format(candidate, "f")}
        )
        try:
            result = run_sahm(trial, evaluation_period, config)
        except SahmMethodError:
            candidate += Decimal("0.1")
            continue
        if result.triggered and (found is None or candidate < found):
            found = candidate
            break
        candidate += Decimal("0.1")
    if found is None:
        raise ProspectiveAssessmentError(
            "no one-decimal rate within 0.0 to 30.0 reaches the threshold"
        )
    return found


def assert_before_release(now: datetime, release_at: datetime = OCTOBER_2026_RELEASE_AT) -> None:
    if now.tzinfo is None or release_at.tzinfo is None:
        raise ProspectiveAssessmentError("timestamps must be timezone-aware")
    if now.astimezone(UTC) >= release_at.astimezone(UTC):
        raise ProspectiveAssessmentError("freeze rejected: the release instant has passed")


def payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_baseline_only_payload(
    *,
    baseline: dict[str, object],
    missing_reason: str,
    observations: list[dict[str, str]],
    retrieved_at: str,
    source_uri: str,
    schedule_verification: str,
) -> dict[str, Any]:
    """A pre-event record that does not invent a Sahm threshold."""
    if schedule_verification not in {"verified", "unverified", "source_unavailable"}:
        raise ProspectiveAssessmentError("unknown schedule verification state")
    return {
        "evidence_class": "verified_real_event",
        "assessment_kind": "baseline_only",
        "event_id": "bls:empsit:2026-10",
        "series_id": "LNS14000000",
        "method_id": SAHM_METHOD_ID,
        "method_version": SAHM_METHOD_VERSION,
        "config_id": SAHM_PUBLISHED.config_id,
        "release_at": OCTOBER_2026_RELEASE_AT.isoformat(),
        "schedule_verification": schedule_verification,
        "evaluation_period": OCTOBER_2026_PERIOD,
        "statement": NO_FORECAST_STATEMENT,
        "no_directional_forecast": True,
        "sahm_threshold_available": False,
        "sahm_unavailable_reason": missing_reason,
        "october_rate_that_reaches_0_50": None,
        "baseline": baseline,
        "observations": observations,
        "retrieved_at": retrieved_at,
        "source_uri": source_uri,
        "limitations": [
            "This is not a forecast of the October unemployment rate.",
            "The Sahm threshold was not calculated because an official input is missing.",
            "A later release cannot turn this record into a prospective Sahm forecast.",
            "This record does not change strategic allocation targets and names no ETF.",
        ],
    }


def build_assessment_payload(
    *,
    baseline: dict[str, object],
    threshold_rate: str,
    observations: list[dict[str, str]],
    retrieved_at: str,
    source_uri: str,
) -> dict[str, Any]:
    return {
        "evidence_class": "verified_real_event",
        "event_id": "bls:empsit:2026-10",
        "series_id": "LNS14000000",
        "method_id": SAHM_METHOD_ID,
        "method_version": SAHM_METHOD_VERSION,
        "config_id": SAHM_PUBLISHED.config_id,
        "release_at": OCTOBER_2026_RELEASE_AT.isoformat(),
        "evaluation_period": OCTOBER_2026_PERIOD,
        "statement": NO_FORECAST_STATEMENT,
        "no_directional_forecast": True,
        "sahm_threshold_available": True,
        "baseline": baseline,
        "october_rate_that_reaches_0_50": threshold_rate,
        "observations": observations,
        "retrieved_at": retrieved_at,
        "source_uri": source_uri,
        "limitations": [
            "This is not a forecast of the October unemployment rate.",
            "Crossing the Sahm threshold is not proof of forecasting skill.",
            "This record does not change strategic allocation targets and names no ETF.",
            "Release instant is 08:30 US Eastern on 6 November 2026 (13:30 UTC).",
            "The BLS schedule HTML page was not parsed in this session.",
        ],
    }


def latest_complete_baseline(by_period: dict, evaluation_period) -> tuple:
    prior = _add_months(evaluation_period, -1)
    result = run_sahm(by_period, prior, SAHM_PUBLISHED)
    rate = by_period[prior].raw_value
    return prior, rate, result


def assessment_from_official_payload(
    payload: dict[str, Any],
    *,
    retrieved_at: datetime,
    source_uri: str,
    schedule_verification: str,
) -> dict[str, Any]:
    """Build a pre-event record from one BLS API payload. Missing inputs stay missing."""
    from datetime import date

    from aqil_research.adapters.bls.adapter import ADAPTER_VERSION
    from aqil_research.adapters.bls.parse import parse_bls_payload

    if str(payload.get("status", "")) != "REQUEST_SUCCEEDED":
        raise ProspectiveAssessmentError("BLS payload did not succeed")
    parsed = parse_bls_payload(
        payload,
        adapter_version=ADAPTER_VERSION,
        retrieved_at=retrieved_at,
        collection_vintage_date=retrieved_at.date(),
    )
    by_period = {row.period_start: row for row in parsed.observations}
    latest_period = max(by_period)
    latest = by_period[latest_period]
    notes = _missing_footnotes(payload)
    observations = [
        {"period": row.period_start.isoformat(), "value": row.raw_value}
        for row in sorted(by_period.values(), key=lambda item: item.period_start)
    ]
    try:
        prior, rate, result = latest_complete_baseline(
            by_period, date.fromisoformat(OCTOBER_2026_PERIOD)
        )
    except SahmMethodError as exc:
        reason = str(exc)
        if notes:
            reason = f"{reason} Official footnote: {'; '.join(notes)}"
        return build_baseline_only_payload(
            baseline={
                "period": latest.period_start.isoformat(),
                "unemployment_rate": latest.raw_value,
            },
            missing_reason=reason,
            observations=observations,
            retrieved_at=retrieved_at.isoformat(),
            source_uri=source_uri,
            schedule_verification=schedule_verification,
        )
    threshold = october_rate_that_reaches_threshold(
        by_period, date.fromisoformat(OCTOBER_2026_PERIOD)
    )
    return build_assessment_payload(
        baseline={
            "period": prior.isoformat(),
            "unemployment_rate": str(rate),
            "gap_percentage_points": str(result.gap_percentage_points),
        },
        threshold_rate=str(threshold),
        observations=observations,
        retrieved_at=retrieved_at.isoformat(),
        source_uri=source_uri,
    )


def _missing_footnotes(payload: dict[str, Any]) -> list[str]:
    results = payload.get("Results")
    if not isinstance(results, dict):
        return []
    series_list = results.get("series")
    if not isinstance(series_list, list):
        return []
    notes: list[str] = []
    for series in series_list:
        if not isinstance(series, dict):
            continue
        data = series.get("data")
        if not isinstance(data, list):
            continue
        for point in data:
            raw_value = str(point.get("value", "")).strip() if isinstance(point, dict) else ""
            if not isinstance(point, dict) or raw_value not in {"", "-"}:
                continue
            footnotes = point.get("footnotes")
            if not isinstance(footnotes, list):
                continue
            for footnote in footnotes:
                if isinstance(footnote, dict) and footnote.get("text"):
                    notes.append(
                        f"{point.get('year')}-{point.get('period')}: {footnote['text']}"
                    )
    return notes


def evaluate_release(
    assessment: dict[str, Any],
    *,
    observed_rate: str,
    published_at: datetime,
    retrieved_at: datetime,
) -> dict[str, Any]:
    if assessment.get("statement") != NO_FORECAST_STATEMENT:
        raise ProspectiveAssessmentError("assessment is missing the no-forecast statement")
    release_at = datetime.fromisoformat(str(assessment["release_at"]))
    if published_at < release_at:
        raise ProspectiveAssessmentError("publication is before the release instant")
    if retrieved_at < release_at:
        raise ProspectiveAssessmentError("outcome cannot be stored before the release")
    observed = Decimal(observed_rate)
    baseline_rate = Decimal(str(assessment["baseline"]["unemployment_rate"]))
    difference = observed - baseline_rate
    if difference > 0:
        direction = "increased"
    elif difference < 0:
        direction = "decreased"
    else:
        direction = "unchanged"
    threshold_met = None
    if assessment.get("sahm_threshold_available") is True:
        threshold = Decimal(str(assessment["october_rate_that_reaches_0_50"]))
        threshold_met = observed >= threshold
    return {
        "evidence_class": "verified_release_outcome",
        "scenario_hash": assessment["payload_hash"],
        "observed_rate": observed_rate,
        "direction_versus_baseline": direction,
        "threshold_condition_met": threshold_met,
        "difference_from_baseline_percentage_points": str(difference),
        "forecasting_skill": None,
        "reason": "No directional forecast was made, so accuracy is not awarded.",
        "published_at": published_at.isoformat(),
        "retrieved_at": retrieved_at.isoformat(),
    }


def freeze_record(directory, payload: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Write the next immutable version. The same payload is idempotent."""
    from pathlib import Path

    assert_before_release(now)
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    digest = payload_hash(payload)
    existing = sorted(folder.glob("freeze-v*.json"))
    for path in existing:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("payload_hash") == digest:
            return saved
    version = len(existing) + 1
    record = {
        "version": version,
        "frozen_at": now.isoformat(),
        "payload_hash": digest,
        "payload": payload,
    }
    target = folder / f"freeze-v{version}.json"
    target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def recompute_hash(record: dict[str, Any]) -> bool:
    return payload_hash(record["payload"]) == record["payload_hash"]


def write_official_baseline(
    directory,
    *,
    schedule_verification: str = "source_unavailable",
) -> dict[str, Any]:
    """Retrieve LNS14000000 and freeze a baseline. A repeated identical payload is a no-op."""
    from aqil_research.adapters.bls.client import BLS_API_URL, fetch_timeseries

    now = datetime.now(UTC)
    response = fetch_timeseries("LNS14000000", 2024, 2026, live=True)
    assessment = assessment_from_official_payload(
        response.payload,
        retrieved_at=now,
        source_uri=BLS_API_URL,
        schedule_verification=schedule_verification,
    )
    return freeze_record(directory, assessment, now)


def main() -> None:
    from pathlib import Path

    folder = (
        Path(__file__).resolve().parents[3] / "assessments" / "2026-11-06-employment-situation"
    )
    record = write_official_baseline(folder)
    payload = record["payload"]
    print(record["frozen_at"])
    print(record["payload_hash"])
    print(payload["assessment_kind"])
    print(payload["schedule_verification"])
    print(payload["baseline"]["period"], payload["baseline"]["unemployment_rate"])


if __name__ == "__main__":
    main()
