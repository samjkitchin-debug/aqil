"""Compare four stored macro readings without making a score.

The synthesis reads results that have already been calculated. It does not
reload observations, subtract the federal funds rate from the 10-year yield,
compute a real rate, or turn industrial production into a GDP figure.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.pipeline.evidence import assess_analytical_evidence
from aqil_research.pipeline.integrity import analytical_payload_hash
from aqil_research.pipeline.models import ResearchRun

SYNTHESIS_METHOD_ID = "MACRO_READING_SYNTHESIS"
SYNTHESIS_METHOD_VERSION = "1.0.0"
SYNTHESIS_CONFIG_ID = "macro_reading_synthesis_v1"
SYNTHESIS_LABEL = "Comparison of the four stored macro readings"

_CAUSAL = "No causal mechanism is established."
_HICP = "Euro-area HICP is excluded and ends in December 2025."
_OCTOBER_2025 = "October 2025 is absent for unemployment and CPI-U. That month is not interpolated."
_H15_ADJUSTMENT = "H.15 seasonal adjustment is unknown."
_NOT_VINTAGE = "The stored files are latest_revised. They are not a vintage panel."
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

_LABOUR = "LABOUR_MARKET_CONDITIONS"
_PRICES = "PRICES_AND_POLICY"
_PRODUCTION = "INDUSTRIAL_PRODUCTION_ACTIVITY"
_CREDIT = "CREDIT_STANDARDS_AND_VOLUMES"


@dataclass(frozen=True, slots=True)
class MacroReadingInput:
    method_id: str
    sufficiency: str
    missing_reason: str | None
    calculation: dict[str, object] | None
    run_id: str


@dataclass(frozen=True, slots=True)
class _Anchor:
    name: str
    period: str
    frequency: str


@dataclass(frozen=True, slots=True)
class MacroSynthesis:
    summary: str
    agreements: tuple[str, ...]
    divergences: tuple[str, ...]
    mismatched_latest_months: tuple[str, ...]
    stale_inputs: tuple[str, ...]
    cited_changes: tuple[str, ...]
    limitations: tuple[str, ...]
    observation_ids: tuple[str, ...]
    sufficiency: Literal["sufficient", "insufficient"]
    source_run_ids: tuple[str, ...]

    def calculation(self) -> dict[str, object]:
        return {
            "method_id": SYNTHESIS_METHOD_ID,
            "method_version": SYNTHESIS_METHOD_VERSION,
            "summary": self.summary,
            "agreements": list(self.agreements),
            "divergences": list(self.divergences),
            "mismatched_latest_months": list(self.mismatched_latest_months),
            "stale_inputs": list(self.stale_inputs),
            "cited_changes": list(self.cited_changes),
            "limitations": list(self.limitations),
            "observation_ids": list(self.observation_ids),
            "source_run_ids": list(self.source_run_ids),
            "composite_score": None,
        }


def synthesize_macro_readings(
    results: tuple[MacroReadingInput, ...] | list[MacroReadingInput],
    *,
    production_endpoints: dict[str, str] | None = None,
) -> MacroSynthesis:
    """State agreement, divergence, mismatched months, and stale inputs."""
    by_id = {item.method_id: item for item in results}
    cited: list[str] = []
    anchors: list[_Anchor] = []
    signs: list[int] = []
    observation_ids: list[str] = []
    failures: list[str] = []

    _consume(
        by_id.get(_LABOUR),
        _labour,
        cited,
        anchors,
        signs,
        observation_ids,
        failures,
        production_endpoints,
    )
    _consume(
        by_id.get(_PRICES),
        _prices,
        cited,
        anchors,
        signs,
        observation_ids,
        failures,
        production_endpoints,
    )
    _consume(
        by_id.get(_PRODUCTION),
        _production,
        cited,
        anchors,
        signs,
        observation_ids,
        failures,
        production_endpoints,
    )
    _consume(
        by_id.get(_CREDIT),
        _credit,
        cited,
        anchors,
        signs,
        observation_ids,
        failures,
        production_endpoints,
    )

    agreements, divergences, mismatched, stale = _compare(anchors, signs)
    sufficient_count = sum(1 for item in results if item.sufficiency == "sufficient")
    sufficiency: Literal["sufficient", "insufficient"] = (
        "sufficient" if sufficient_count >= 2 else "insufficient"
    )
    limitations = _limitations(failures)
    summary = _summary(agreements, divergences, mismatched, stale, failures)
    return MacroSynthesis(
        summary=summary,
        agreements=tuple(agreements),
        divergences=tuple(divergences),
        mismatched_latest_months=tuple(mismatched),
        stale_inputs=tuple(stale),
        cited_changes=tuple(cited),
        limitations=limitations,
        observation_ids=tuple(dict.fromkeys(observation_ids)),
        sufficiency=sufficiency,
        source_run_ids=tuple(item.run_id for item in results),
    )


def build_synthesis_run(
    synthesis: MacroSynthesis,
    *,
    dataset_id: str,
    source_id: str,
    input_dataset_ids: list[str],
    evaluation_period: str,
    executed_at: datetime | None = None,
    run_id: str | None = None,
) -> ResearchRun:
    """Append-only run. publication_allowed stays false."""
    wall_clock = executed_at or datetime.now(tz=UTC)
    execution_status: Literal["completed", "completed_insufficient"] = (
        "completed" if synthesis.sufficiency == "sufficient" else "completed_insufficient"
    )
    implication: Literal["no_action", "insufficient_evidence"] = (
        "no_action" if synthesis.sufficiency == "sufficient" else "insufficient_evidence"
    )
    evidence = assess_analytical_evidence(
        execution_status=execution_status,
        data_sufficiency=synthesis.sufficiency,
        publication_allowed=False,
    )
    config_hash = MethodParameterDocument(
        config_id=SYNTHESIS_CONFIG_ID,
        label=SYNTHESIS_LABEL,
        scalars={},
    ).config_hash()
    implementation_hash = hashlib.sha256(
        f"{SYNTHESIS_METHOD_ID}:{SYNTHESIS_METHOD_VERSION}".encode(),
    ).hexdigest()
    snapshot = hashlib.sha256(",".join(synthesis.source_run_ids).encode()).hexdigest()
    run = ResearchRun(
        run_id=run_id or str(uuid.uuid4()),
        executed_at=wall_clock,
        execution_status=execution_status,
        dataset_id=dataset_id,
        input_dataset_ids=input_dataset_ids,
        source_id=source_id,
        rights_record_id=source_id,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type=SYNTHESIS_METHOD_ID,
        decision_at=wall_clock,
        evaluation_period=evaluation_period,
        method_id=SYNTHESIS_METHOD_ID,
        method_version=SYNTHESIS_METHOD_VERSION,
        implementation_hash=implementation_hash,
        config_id=SYNTHESIS_CONFIG_ID,
        config_hash=config_hash,
        input_snapshot_hash=snapshot,
        data_sufficiency=synthesis.sufficiency,
        missing_data_reason=None if synthesis.sufficiency == "sufficient" else synthesis.summary,
        calculation=synthesis.calculation(),
        statistical_interpretation=(
            "Descriptive comparison of stored readings. Not a forecast and not a score."
        ),
        causal_hypothesis=_CAUSAL,
        market_pricing="unknown",
        investment_implication=implication,
        assumptions=[
            "Each reading keeps its own window.",
            "A shared month is not a cause.",
            "HICP is not an input.",
        ],
        limitations=list(synthesis.limitations),
        observation_ids=list(synthesis.observation_ids),
        adapter_ids=[],
        ingest_notes=[],
        reproduction={
            "method_id": SYNTHESIS_METHOD_ID,
            "method_version": SYNTHESIS_METHOD_VERSION,
            "implementation_hash": implementation_hash,
            "config_hash": config_hash,
            "input_snapshot_hash": snapshot,
        },
        narrative=synthesis.summary,
        publication_allowed=False,
        verification_status=evidence.verification_status,
        evidence_reasons=list(evidence.reasons),
    )
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    return run.model_copy(
        update={"analytical_payload_hash": analytical_payload_hash(run.model_dump(mode="json"))},
    )


def spoken_period(iso_date: str, *, quarterly: bool = False) -> str:
    year_s, month_s, day_s = iso_date[:10].split("-")
    month = _MONTHS[int(month_s) - 1]
    day = int(day_s)
    if quarterly:
        return f"the quarter starting {day} {month} {year_s}"
    if day == 1:
        return f"{month} {year_s}"
    return f"{day} {month} {year_s}"


def _consume(
    item: MacroReadingInput | None,
    reader,
    cited: list[str],
    anchors: list[_Anchor],
    signs: list[int],
    observation_ids: list[str],
    failures: list[str],
    production_endpoints: dict[str, str] | None,
) -> None:
    if item is None:
        failures.append("A reading was not supplied.")
        return
    if item.sufficiency != "sufficient" or not isinstance(item.calculation, dict):
        reason = item.missing_reason or "The stored reading is not sufficient."
        failures.append(f"{_plain_name(item.method_id)} is insufficient: {reason}")
        return
    try:
        reader(item.calculation, cited, anchors, signs, observation_ids, production_endpoints)
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(f"{_plain_name(item.method_id)} could not be read: {exc}")


def _labour(
    calculation: dict[str, object],
    cited: list[str],
    anchors: list[_Anchor],
    signs: list[int],
    observation_ids: list[str],
    _endpoints: dict[str, str] | None,
) -> None:
    series = calculation.get("series")
    if not isinstance(series, list):
        raise ValueError("labour calculation has no series")
    latest_periods: list[str] = []
    for row in series:
        if not isinstance(row, dict):
            continue
        change = row.get("twelve_month_change")
        if not isinstance(change, dict):
            continue
        name = _dataset_name(str(row["dataset_id"]))
        period = str(row["latest_period"])
        latest_periods.append(period)
        anchors.append(_Anchor(name, period, "monthly"))
        observation_ids.append(str(row["observation_id"]))
        observation_ids.extend(
            [str(change["start_observation_id"]), str(change["end_observation_id"])],
        )
        if "change_percentage_points" in change:
            movement = f"{change['change_percentage_points']} percentage points"
            signs.append(_sign(str(change["change_percentage_points"])))
        else:
            movement = (
                f"{change['change_thousands']} thousands ({change['percent_change']} percent)"
            )
            signs.append(_sign(str(change["percent_change"])))
        cited.append(
            f"{name} was {row['level']} {row['unit']} in {spoken_period(period)} "
            f"(observation {row['observation_id']}), a 12-month change of {movement} "
            f"from {spoken_period(str(change['window_start']))} "
            f"(observation {change['start_observation_id']}) to "
            f"{spoken_period(str(change['window_end']))} "
            f"(observation {change['end_observation_id']}). "
            f"Rank {row['rank']} of {row['history_count']} stored values.",
        )
    joint = calculation.get("joint")
    if not isinstance(joint, dict):
        return
    joint_period = str(joint["latest_common_period"])
    anchors.append(_Anchor("Joint labour month", joint_period, "joint"))
    window = joint.get("twelve_month_change")
    if isinstance(window, dict):
        cited.append(
            "The joint labour reading uses "
            f"{spoken_period(joint_period)}, the latest month present in all three series. "
            f"Its 12-month window is {spoken_period(str(window['window_start']))} to "
            f"{spoken_period(str(window['window_end']))}.",
        )


def _prices(
    calculation: dict[str, object],
    cited: list[str],
    anchors: list[_Anchor],
    signs: list[int],
    observation_ids: list[str],
    _endpoints: dict[str, str] | None,
) -> None:
    cpi = calculation.get("cpi_u")
    funds = calculation.get("federal_funds")
    treasury = calculation.get("treasury_10_year")
    if not isinstance(cpi, dict) or not isinstance(funds, dict) or not isinstance(treasury, dict):
        raise ValueError("prices calculation is incomplete")
    anchors.append(_Anchor("CPI-U", str(cpi["period"]), "monthly"))
    anchors.append(_Anchor("Federal funds", str(funds["period"]), "monthly"))
    anchors.append(_Anchor("10-year yield", str(treasury["period"]), "monthly"))
    signs.append(_sign(str(cpi["twelve_month_percent_change"])))
    signs.append(_sign(str(funds["one_month_change_percentage_points"])))
    signs.append(_sign(str(treasury["one_month_change_percentage_points"])))
    _append_id(observation_ids, cpi.get("comparison_observation_id"))
    _append_id(observation_ids, cpi.get("observation_id"))
    for block in (funds, treasury):
        _append_id(observation_ids, block.get("observation_id"))
        _append_id(observation_ids, block.get("prior_observation_id"))
    cited.append(
        "CPI-U 12-month change from "
        f"{spoken_period(str(cpi['comparison_period']))} to "
        f"{spoken_period(str(cpi['period']))} is {cpi['twelve_month_percent_change']} percent "
        f"(index {cpi['comparison_index_level']} to {cpi['index_level']}, {cpi['unit']}). "
        f"{_endpoint_sentence(cpi.get('comparison_observation_id'), cpi.get('observation_id'))}"
        f"Rank {cpi['rank']}. "
        f"{cpi['values_strictly_below']} stored values are strictly below this index."
    )
    cited.append(
        f"Federal funds was {funds['level_percent_per_year']} percent per year in "
        f"{spoken_period(str(funds['period']))} "
        f"({_id_clause(funds.get('observation_id'))}), a one-month change of "
        f"{funds['one_month_change_percentage_points']} percentage points from "
        f"{spoken_period(str(funds['prior_period']))} "
        f"({_id_clause(funds.get('prior_observation_id'))}). "
        f"Rank {funds['rank']}. "
        f"{funds['values_strictly_below']} stored values are strictly below this level."
    )
    cited.append(
        f"The 10-year yield was {treasury['level_percent_per_year']} percent per year in "
        f"{spoken_period(str(treasury['period']))} "
        f"({_id_clause(treasury.get('observation_id'))}), a one-month change of "
        f"{treasury['one_month_change_percentage_points']} percentage points from "
        f"{spoken_period(str(treasury['prior_period']))} "
        f"({_id_clause(treasury.get('prior_observation_id'))}). "
        f"Rank {treasury['rank']}. "
        f"{treasury['values_strictly_below']} stored values are strictly below this level. "
        "Federal funds and the 10-year yield stay separate levels."
    )


def _production(
    calculation: dict[str, object],
    cited: list[str],
    anchors: list[_Anchor],
    signs: list[int],
    observation_ids: list[str],
    endpoints: dict[str, str] | None,
) -> None:
    latest = str(calculation["latest_period"])
    earlier = str(calculation["earlier_period"])
    anchors.append(_Anchor("Industrial production", latest, "monthly"))
    signs.append(_sign(str(calculation["twelve_month_percent_change"])))
    latest_id = (endpoints or {}).get("latest")
    earlier_id = (endpoints or {}).get("earlier")
    if latest_id:
        observation_ids.append(latest_id)
    if earlier_id:
        observation_ids.append(earlier_id)
    id_text = ""
    if latest_id and earlier_id:
        id_text = f" Earlier observation {earlier_id}. Later observation {latest_id}."
    cited.append(
        f"Industrial production was {calculation['latest_level']} "
        f"({calculation['unit']}) in {spoken_period(latest)}. "
        f"The 12-month percent change from {spoken_period(earlier)} "
        f"({calculation['earlier_level']}) is {calculation['twelve_month_percent_change']} "
        f"percent. Rank {calculation['historical_rank']} of "
        f"{calculation['stored_value_count']} stored values.{id_text} "
        "This is production, not a GDP figure.",
    )


def _credit(
    calculation: dict[str, object],
    cited: list[str],
    anchors: list[_Anchor],
    signs: list[int],
    observation_ids: list[str],
    _endpoints: dict[str, str] | None,
) -> None:
    standards = calculation.get("lending_standards")
    volume = calculation.get("bank_credit")
    if not isinstance(standards, dict) or not isinstance(volume, dict):
        raise ValueError("credit calculation is incomplete")
    latest = str(standards["latest_period_start"])
    prior = str(standards["prior_period_start"])
    anchors.append(_Anchor("SLOOS", latest, "quarterly"))
    anchors.append(_Anchor("Bank credit", str(volume["latest_period_start"]), "weekly"))
    signs.append(_sign(str(standards["difference_percentage_points"])))
    observation_ids.append(str(standards["latest_observation_id"]))
    observation_ids.append(str(standards["prior_observation_id"]))
    observation_ids.append(str(volume["latest_observation_id"]))
    cited.append(
        f"The SLOOS net tightening share was {standards['latest_share']} "
        f"{standards['unit']} for {spoken_period(latest, quarterly=True)} "
        f"(observation {standards['latest_observation_id']}). "
        f"The prior quarter, {spoken_period(prior, quarterly=True)}, was "
        f"{standards['prior_share']} (observation {standards['prior_observation_id']}). "
        f"The difference is {standards['difference_percentage_points']} percentage points.",
    )
    week = spoken_period(str(volume["latest_period_start"]))
    if volume.get("change_usd_millions") is None:
        cited.append(
            f"Bank credit for the week of {week} was "
            f"{volume['latest_level_usd_millions']} {volume['unit']} "
            f"(observation {volume['latest_observation_id']}). "
            f"{volume.get('missing_reason') or 'The 52-week change is unavailable.'}",
        )
        return
    signs.append(_sign(str(volume["change_usd_millions"])))
    comparison_id = volume.get("comparison_observation_id")
    if comparison_id:
        observation_ids.append(str(comparison_id))
    cited.append(
        f"Bank credit for the week of {week} was "
        f"{volume['latest_level_usd_millions']} {volume['unit']} "
        f"(observation {volume['latest_observation_id']}). "
        f"The week of {spoken_period(str(volume['comparison_period_start']))} was "
        f"{volume['comparison_level_usd_millions']} "
        f"(observation {comparison_id}). "
        f"The 52-week change is {volume['change_usd_millions']} {volume['unit']}. "
        "The survey share is not converted into dollars.",
    )


def _compare(
    anchors: list[_Anchor],
    signs: list[int],
) -> tuple[list[str], list[str], list[str], list[str]]:
    monthly = [anchor for anchor in anchors if anchor.frequency == "monthly"]
    agreement_period = _shared_period(monthly)
    shared = [anchor.name for anchor in monthly if anchor.period == agreement_period]
    agreements: list[str] = []
    if len(shared) >= 2 and agreement_period is not None:
        agreements.append(
            f"{_join(shared)} share {spoken_period(agreement_period)} as their latest month. "
            "A shared month is not a cause.",
        )
    nonzero = {sign for sign in signs if sign != 0}
    if len(nonzero) == 1 and signs:
        agreements.append(
            "The cited changes that are not zero share one sign. That coincidence is not a cause.",
        )
    mismatched = [
        f"{anchor.name} {spoken_period(anchor.period, quarterly=anchor.frequency == 'quarterly')}"
        for anchor in anchors
        if agreement_period is None or anchor.period != agreement_period
    ]
    divergences: list[str] = []
    if mismatched:
        divergences.append(
            "Latest months that do not match"
            + (f" {spoken_period(agreement_period)}" if agreement_period else "")
            + f": {_join(mismatched)}.",
        )
    if len(nonzero) > 1:
        divergences.append(
            "The stored changes do not share one sign. "
            "The windows are not the same length, and coincident moves are not a cause.",
        )
    elif not divergences:
        divergences.append("No stored latest month diverges from the shared monthly month.")
    stale = _stale(anchors, agreement_period)
    return agreements, divergences, mismatched, stale


def _stale(anchors: list[_Anchor], agreement_period: str | None) -> list[str]:
    stale = [_HICP]
    if agreement_period is None:
        return stale
    behind = [
        anchor
        for anchor in anchors
        if anchor.period < agreement_period and anchor.frequency != "weekly"
    ]
    if behind:
        stale.append(
            f"{_join([anchor.name for anchor in behind])} "
            f"{'is' if len(behind) == 1 else 'are'} behind {spoken_period(agreement_period)}.",
        )
    newer = [anchor for anchor in anchors if anchor.period > agreement_period]
    if newer:
        named = [f"{anchor.name} ({spoken_period(anchor.period)})" for anchor in newer]
        stale.append(
            f"{_join(named)} "
            f"{'is' if len(newer) == 1 else 'are'} later than the monthly readings. "
            "The earlier monthly readings are not updated to that date.",
        )
    return stale


def _summary(
    agreements: list[str],
    divergences: list[str],
    mismatched: list[str],
    stale: list[str],
    failures: list[str],
) -> str:
    parts = [
        "The reading is internal.",
        "Labour, prices, production, and credit stay separate. No composite score is calculated.",
    ]
    if agreements:
        parts.append("Agreement: " + " ".join(agreements))
    else:
        parts.append("Agreement: no shared latest month was available.")
    parts.append("Divergence: " + " ".join(divergences))
    if mismatched:
        parts.append(f"Mismatched latest months: {_join(mismatched)}.")
    parts.append("Stale inputs: " + " ".join(stale))
    if failures:
        parts.append(" ".join(failures))
    return " ".join(parts)


def _limitations(failures: list[str]) -> tuple[str, ...]:
    base = [
        "The reading is internal.",
        "Publication remains closed.",
        f"{_CAUSAL} Coincident changes are not a cause.",
        "No composite score is calculated.",
        "Federal funds and the 10-year yield stay separate. "
        "Their difference is not calculated. No real rate is calculated.",
        _H15_ADJUSTMENT,
        f"{_HICP} That series is not an input.",
        "Industrial production is not a GDP figure. Census advance orders were not collected.",
        _OCTOBER_2025,
        "A missing endpoint is not interpolated.",
        _NOT_VINTAGE,
    ]
    return tuple(base + failures)


def _shared_period(monthly: list[_Anchor]) -> str | None:
    counts: dict[str, int] = {}
    for anchor in monthly:
        counts[anchor.period] = counts.get(anchor.period, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda period: (counts[period], period))


def _append_id(observation_ids: list[str], value: object) -> None:
    if isinstance(value, str) and value:
        observation_ids.append(value)


def _id_clause(value: object) -> str:
    if isinstance(value, str) and value:
        return f"observation {value}"
    return "observation not named on the stored result"


def _endpoint_sentence(earlier: object, later: object) -> str:
    if isinstance(earlier, str) and earlier and isinstance(later, str) and later:
        return f"Earlier observation {earlier}. Later observation {later}. "
    return ""


def _sign(value: str) -> int:
    number = Decimal(value)
    if number > 0:
        return 1
    if number < 0:
        return -1
    return 0


def _dataset_name(dataset_id: str) -> str:
    names = {
        "bls.ln.LNS14000000": "Unemployment",
        "bls.ce.CES0000000001": "Payrolls",
        "bls.jt.JTS000000000000000JOL": "Job openings",
    }
    return names.get(dataset_id, dataset_id)


def _plain_name(method_id: str) -> str:
    names = {
        _LABOUR: "The labour reading",
        _PRICES: "The prices reading",
        _PRODUCTION: "The production reading",
        _CREDIT: "The credit reading",
    }
    return names.get(method_id, method_id)


def _join(items: list[str] | tuple[str, ...]) -> str:
    names = list(items)
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"
