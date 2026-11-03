"""Turn stored closes into events and the frozen intersection. No database access."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.events.availability import AvailabilityRow, build_feature_rows
from aqil_research.long_horizon.events.definition import (
    DEFINITION_ID,
    DEFINITION_VERSION,
    EVENT_DEFINITION,
    FROZEN_MACRO_INTERSECTION,
    FROZEN_PILOT_INTERSECTION,
    MACRO_CLAIM_ID,
    MACRO_EXPERIMENT_ID,
    PILOT_EXPERIMENT_ID,
    event_definition_hash,
    macro_intersection_hash,
    pilot_intersection_hash,
)
from aqil_research.long_horizon.events.identify import (
    EventDefinitionError,
    FamilyCount,
    ListingSeries,
    catalogue_listing,
    relative_and_leadership,
)
from aqil_research.long_horizon.events.pilot_rule import (
    DecisionRow,
    SymbolFrequency,
    condition_at,
    describe_pilot,
    evaluate_listing,
    summarise,
)
from aqil_research.long_horizon.money import decimal_text, sha256_document


@dataclass(frozen=True)
class CataloguedEvent:
    event_id: str
    symbol: str
    currency: str
    family: str
    horizon_label: str
    start_date: date
    end_date: date
    label_confirmed_on: date | None
    price_return: str
    session_steps: int
    max_intervening_drawdown: str
    up_session_fraction: str
    label_uses_later_prices: bool
    historically_observable_at_event_date: bool
    price_series_sha256: str
    detail: str
    start_index: int


@dataclass(frozen=True)
class FamilyRecord:
    symbol: str
    family: str
    horizon_label: str
    status: str
    reason: str
    event_count: int
    windows_examined: int
    qualifier_window_count: int | None
    censored_count: int
    price_series_sha256: str


@dataclass(frozen=True)
class MacroFacts:
    """Dates and stored labels only. Observation values are not carried."""

    periods: dict[str, tuple[date, ...]]
    seasonal: dict[str, str | None]
    gdp_vintage_count: int
    gdp_first: str
    gdp_last: str
    gdp_seasonal: str | None
    unemployment_vintage_count: int
    unemployment_first: str
    unemployment_last: str
    alfred_count: int
    fx_count: int
    distribution_tables: tuple[str, ...]


@dataclass(frozen=True)
class Analysis:
    events: tuple[CataloguedEvent, ...]
    families: tuple[FamilyRecord, ...]
    availability: tuple[AvailabilityRow, ...]
    decisions: tuple[DecisionRow, ...]
    frequencies: tuple[SymbolFrequency, ...]
    artifact: dict[str, object]


def _event_id(symbol: str, family: str, horizon: str, start: date, end: date) -> str:
    return f"PE-v1-{symbol}-{family}-{horizon}-{start.isoformat()}-{end.isoformat()}"


def _rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "not_defined"
    return decimal_text(Decimal(numerator) / Decimal(denominator))


def _blocked_notes(facts: MacroFacts) -> list[tuple[str, str]]:
    seasonal = facts.gdp_seasonal if facts.gdp_seasonal is not None else "not stored on this row"
    distributions = (
        ", ".join(facts.distribution_tables)
        if facts.distribution_tables
        else "no distribution table was found"
    )
    return [
        (
            "total_return",
            str(EVENT_DEFINITION["total_return_block_reason"]),
        ),
        (
            "foreign_exchange",
            (
                f"instruments.fx_observations has {facts.fx_count} rows. "
                "No conversion is applied and no rate is invented."
            ),
        ),
        (
            "distribution",
            (
                f"Distribution lookup: {distributions}. No distribution is invented "
                "and none is used to relabel a split-adjusted close."
            ),
        ),
        (
            "fred.alfred.UNRATE",
            (
                f"Stored rows whose dataset id contains alfred: {facts.alfred_count}. "
                "ALFRED is not stored by this programme and no value was read."
            ),
        ),
        (
            "bea.vintage.real_gdp.pct_preceding",
            (
                f"Stored provider-vintage rows: {facts.gdp_vintage_count}, "
                f"from {facts.gdp_first} to {facts.gdp_last}. "
                f"Stored seasonal adjustment: {seasonal}. "
                "The series was not joined to events and does not unlock a method."
            ),
        ),
        (
            "bls.ln.LNS14000000.provider_vintage",
            (
                f"Stored provider-vintage rows: {facts.unemployment_vintage_count}, "
                f"from {facts.unemployment_first} to {facts.unemployment_last}. "
                "They are not used as an original-vintage lookback."
            ),
        ),
    ]


def _families_for(
    listing: ListingSeries,
    series_hash: str,
    counts: list[FamilyCount],
) -> tuple[list[CataloguedEvent], list[FamilyRecord]]:
    events: list[CataloguedEvent] = []
    families: list[FamilyRecord] = []
    seen: set[str] = set()
    for count in counts:
        families.append(
            FamilyRecord(
                symbol=listing.symbol,
                family=count.family,
                horizon_label=count.horizon_label,
                status=count.status,
                reason=count.reason,
                event_count=len(count.events),
                windows_examined=count.windows_examined,
                qualifier_window_count=count.qualifier_window_count,
                censored_count=count.censored_count,
                price_series_sha256=series_hash,
            )
        )
        if count.status != "catalogued":
            continue
        for event in count.events:
            start = listing.dates[event.start_index]
            end = listing.dates[event.end_index]
            confirmed = (
                None
                if event.label_confirmed_index is None
                else listing.dates[event.label_confirmed_index]
            )
            identifier = _event_id(listing.symbol, event.family, event.horizon_label, start, end)
            if identifier in seen:
                raise EventDefinitionError(f"duplicate event id {identifier}")
            seen.add(identifier)
            events.append(
                CataloguedEvent(
                    event_id=identifier,
                    symbol=listing.symbol,
                    currency=listing.currency,
                    family=event.family,
                    horizon_label=event.horizon_label,
                    start_date=start,
                    end_date=end,
                    label_confirmed_on=confirmed,
                    price_return=event.price_return,
                    session_steps=event.end_index - event.start_index,
                    max_intervening_drawdown=event.max_intervening_drawdown,
                    up_session_fraction=event.up_session_fraction,
                    label_uses_later_prices=event.label_uses_later_prices,
                    historically_observable_at_event_date=(
                        event.historically_observable_at_event_date
                    ),
                    price_series_sha256=series_hash,
                    detail=event.detail,
                    start_index=event.start_index,
                )
            )
    return events, families


def _family_aggregates(families: list[FamilyRecord]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in families:
        key = (row.family, row.horizon_label, row.status)
        bucket = grouped.get(key)
        if bucket is None:
            bucket = {
                "family": row.family,
                "horizon_label": row.horizon_label,
                "status": row.status,
                "event_count": 0,
                "censored_count": 0,
                "windows_examined": 0,
                "qualifier_window_count": 0,
                "qualifier_defined": True,
                "symbols": 0,
            }
            grouped[key] = bucket
        bucket["event_count"] = int(bucket["event_count"]) + row.event_count
        bucket["censored_count"] = int(bucket["censored_count"]) + row.censored_count
        bucket["windows_examined"] = int(bucket["windows_examined"]) + row.windows_examined
        bucket["symbols"] = int(bucket["symbols"]) + 1
        if row.qualifier_window_count is None:
            bucket["qualifier_defined"] = False
        else:
            bucket["qualifier_window_count"] = (
                int(bucket["qualifier_window_count"]) + row.qualifier_window_count
            )
    aggregates: list[dict[str, object]] = []
    for key in sorted(grouped):
        bucket = grouped[key]
        qualifier: object
        if bucket["qualifier_defined"]:
            qualifier = bucket["qualifier_window_count"]
        else:
            qualifier = None
        aggregates.append(
            {
                "family": bucket["family"],
                "horizon_label": bucket["horizon_label"],
                "status": bucket["status"],
                "event_count": bucket["event_count"],
                "censored_count": bucket["censored_count"],
                "windows_examined": bucket["windows_examined"],
                "qualifier_window_count": qualifier,
                "symbols": bucket["symbols"],
            }
        )
    return aggregates


def _symbol_rows(frequencies: list[SymbolFrequency]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in sorted(frequencies, key=lambda row: row.symbol):
        conditional = _rate(item.condition_and_event, item.condition)
        if item.condition and item.eligible:
            lift = decimal_text(item.lift())
        else:
            lift = "not_defined"
        rows.append(
            {
                "symbol": item.symbol,
                "eligible": item.eligible,
                "condition": item.condition,
                "event": item.event,
                "condition_and_event": item.condition_and_event,
                "false_positives": item.condition - item.condition_and_event,
                "false_negatives": item.event - item.condition_and_event,
                "qualifies": item.qualifies(),
                "base_rate": _rate(item.event, item.eligible),
                "conditional_frequency": conditional,
                "condition_frequency": _rate(item.condition, item.eligible),
                "event_share": _rate(item.condition_and_event, item.event),
                "lift": lift,
            }
        )
    return rows


def analyse(
    listings: list[ListingSeries],
    series_hashes: dict[str, str],
    facts: MacroFacts,
) -> Analysis:
    if not listings:
        raise EventDefinitionError("no stored listing was loaded")
    cross = relative_and_leadership(listings)
    events: list[CataloguedEvent] = []
    families: list[FamilyRecord] = []
    decisions: list[DecisionRow] = []
    frequencies: list[SymbolFrequency] = []
    availability: list[AvailabilityRow] = []
    notes = _blocked_notes(facts)
    for listing in sorted(listings, key=lambda item: item.symbol):
        counts = catalogue_listing(listing, cross[listing.symbol])
        listing_events, listing_families = _families_for(
            listing,
            series_hashes[listing.symbol],
            counts,
        )
        events.extend(listing_events)
        families.extend(listing_families)
        listing_decisions = evaluate_listing(listing.symbol, listing.dates, listing.closes)
        decisions.extend(listing_decisions)
        if listing_decisions:
            frequencies.append(summarise(listing_decisions))
        else:
            frequencies.append(SymbolFrequency(listing.symbol, 0, 0, 0, 0))
        for decision in listing_decisions:
            if decision.selected_on_future_return:
                raise EventDefinitionError("a comparison period was selected on the later return")
            prefix = listing.closes[: decision.decision_index + 1]
            if condition_at(prefix, decision.decision_index) != decision.condition_met:
                raise EventDefinitionError("the condition changed when later closes were removed")
        starts = [(event.start_date, event.start_index) for event in listing_events]
        availability.extend(
            build_feature_rows(
                listing.symbol,
                starts,
                {key: list(value) for key, value in facts.periods.items()},
                facts.seasonal,
                notes,
            )
        )
    described = describe_pilot(frequencies)
    if described["status"] in {
        "statistically_supported",
        "economically_useful",
        "forward_validated",
    }:
        raise EventDefinitionError("category C status was promoted")
    event_identity = [
        {
            "event_id": event.event_id,
            "price_return": event.price_return,
            "start_date": event.start_date.isoformat(),
            "end_date": event.end_date.isoformat(),
        }
        for event in sorted(events, key=lambda item: item.event_id)
    ]
    comparison_identity = [
        {
            "symbol": row.symbol,
            "decision_date": row.decision_date.isoformat(),
            "condition_met": row.condition_met,
            "outcome_advance": row.outcome_advance,
            "forward_price_return": row.forward_price_return,
            "selected_on_future_return": False,
        }
        for row in sorted(decisions, key=lambda item: (item.symbol, item.decision_date))
    ]
    artifact: dict[str, object] = {
        "definition_id": DEFINITION_ID,
        "definition_version": DEFINITION_VERSION,
        "definition_hash": event_definition_hash(),
        "pilot_experiment_id": PILOT_EXPERIMENT_ID,
        "pilot_specification_hash": pilot_intersection_hash(),
        "macro_experiment_id": MACRO_EXPERIMENT_ID,
        "macro_specification_hash": macro_intersection_hash(),
        "macro_estimated": False,
        "macro_block_reason": FROZEN_MACRO_INTERSECTION["block_reason"],
        "portfolio_comparison": FROZEN_PILOT_INTERSECTION["portfolio_comparison"],
        "status": described["status"],
        "reasons": described["reasons"],
        "medians": described["medians"],
        "qualifying_symbols": described["qualifying_symbols"],
        "pooled": described["pooled"],
        "symbols": _symbol_rows(frequencies),
        "families": _family_aggregates(families),
        "event_count": len(events),
        "comparison_count": len(decisions),
        "event_identity_sha256": sha256_document(event_identity),
        "comparison_identity_sha256": sha256_document(comparison_identity),
        "price_series_sha256": {symbol: series_hashes[symbol] for symbol in sorted(series_hashes)},
        "fx_observation_count": facts.fx_count,
        "alfred_row_count": facts.alfred_count,
        "publication_allowed": False,
        "holdout": "none",
        "not_an_investment_claim": True,
    }
    return Analysis(
        events=tuple(sorted(events, key=lambda item: item.event_id)),
        families=tuple(families),
        availability=tuple(availability),
        decisions=tuple(sorted(decisions, key=lambda item: (item.symbol, item.decision_date))),
        frequencies=tuple(frequencies),
        artifact=artifact,
    )


def claim_proposition(artifact: dict[str, object]) -> str:
    medians = artifact["medians"]
    assert isinstance(medians, dict)
    reasons = artifact["reasons"]
    assert isinstance(reasons, list)
    return (
        f"The preregistered category C intersection is {artifact['status']}. "
        f"Median lift is {medians['lift']}. "
        f"Median condition frequency is {medians['condition_frequency']}. "
        f"Median event share is {medians['event_share']}. "
        f"Reasons: {'; '.join(str(reason) for reason in reasons)}. "
        "This is not an investment claim. The portfolio comparison was not run."
    )


MACRO_CLAIM_TEXT = (
    f"{MACRO_CLAIM_ID} records that the example macro intersection was not estimated. "
    "Latest-revised industrial production and consumer prices were not read as "
    "decision inputs. No portfolio path was run. This is not an investment claim."
)
