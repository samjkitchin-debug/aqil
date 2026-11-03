"""Assemble atlas rows from stored series. This module does not open a database."""

from __future__ import annotations

import bisect
import inspect
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from aqil_research.long_horizon.events.identify import ListingSeries, session_on_or_before
from aqil_research.long_horizon.events.pilot_rule import month_end_indices
from aqil_research.long_horizon.money import canonical_json, decimal_text
from aqil_research.long_horizon.state_atlas.features import (
    EconomicPoint,
    FeatureValue,
    economic_features,
    outcome_at,
    trailing_acceleration,
    trailing_return,
    volatility,
)
from aqil_research.long_horizon.state_atlas.features import (
    drawdown as drawdown_feature,
)
from aqil_research.long_horizon.state_atlas.features import (
    recovery_from_prior_trough as recovery_feature,
)
from aqil_research.long_horizon.state_atlas.rule import SequenceDecision, evaluate_listing
from aqil_research.long_horizon.state_atlas.specification import (
    POINT_IN_TIME_DATASET,
    SESSION_STEPS,
    SPECIFICATION_ID,
    SPECIFICATION_VERSION,
)

RETROSPECTIVE = "retrospective_latest_revised_release_lag_unknown"
POINT_IN_TIME = "point_in_time_observation"
STORED_SESSIONS = "stored_sessions"
PRICE_DETAIL = "split-adjusted close on or before the anchor; not a total return"
RETRO_DETAIL = "latest revised; release lag unknown; not a decision input"
PIT_DETAIL = (
    "printed release date on or before the anchor; this does not make a method point-in-time"
)


class AtlasBuildError(ValueError):
    """Stored inputs cannot be assembled without inventing a value."""


@dataclass(frozen=True)
class StoredSeries:
    dataset_id: str
    frequency: str
    unit: str
    seasonal_adjustment: str
    points: tuple[EconomicPoint, ...]
    bounds: tuple[date, ...]


@dataclass(frozen=True)
class VintageRow:
    period_start: date
    period_end: date
    release_date: date
    value: Decimal


@dataclass(frozen=True)
class StoredEvent:
    event_id: str
    symbol: str
    family: str
    start_date: date
    end_date: date


@dataclass
class AtlasBatch:
    anchors: list[tuple[object, ...]] = field(default_factory=list)
    states: list[tuple[object, ...]] = field(default_factory=list)
    outcomes: list[tuple[object, ...]] = field(default_factory=list)
    inventory: list[tuple[object, ...]] = field(default_factory=list)
    links: list[tuple[object, ...]] = field(default_factory=list)
    episodes: list[tuple[object, ...]] = field(default_factory=list)
    episode_events: list[tuple[object, ...]] = field(default_factory=list)
    decisions: list[SequenceDecision] = field(default_factory=list)
    anchor_dates: dict[str, list[tuple[date, str]]] = field(default_factory=dict)


def anchor_identity(symbol: str, kind: str, session: date) -> str:
    return f"{SPECIFICATION_ID}:{SPECIFICATION_VERSION}:{symbol}:{kind}:{session.isoformat()}"


def _state(
    anchor_id: str,
    feature_id: str,
    family: str,
    feature: FeatureValue,
    clock: str,
    usable: bool,
    detail: str,
    recorded_at: datetime,
) -> tuple[object, ...]:
    if "surprise" in feature_id or feature_id.startswith("outcome_"):
        raise AtlasBuildError("a state row cannot carry a surprise or an outcome")
    if clock == RETROSPECTIVE:
        usable = False
    if feature.availability != "observed":
        usable = False
    return (
        f"{anchor_id}:{feature_id}",
        anchor_id,
        feature_id,
        family,
        feature.availability,
        clock,
        usable,
        feature.value,
        detail,
        False,
        recorded_at,
    )


def _market_feature(closes: Sequence[Decimal], index: int, steps: int, name: str) -> FeatureValue:
    if name == "trailing_return":
        return trailing_return(closes, index, steps)
    if name == "trailing_return_acceleration":
        return trailing_acceleration(closes, index, steps)
    if name == "drawdown":
        return drawdown_feature(closes, index, steps)
    if name == "recovery_from_prior_trough":
        return recovery_feature(closes, index, steps)
    if name == "volatility":
        return volatility(closes, index, steps)
    raise AtlasBuildError(name)


def _relative(
    listing: ListingSeries,
    index: int,
    steps: int,
    vwra: ListingSeries,
) -> tuple[FeatureValue, str]:
    if listing.currency != "USD":
        if listing.symbol == "EUNA":
            detail = "EUNA is EUR and fx_observations is empty, so relative performance is blocked"
        else:
            detail = (
                "cross-currency relative performance is blocked; "
                "no foreign-exchange rate is applied"
            )
        return FeatureValue("blocked_no_foreign_exchange", None), detail
    if listing.symbol == "VWRA":
        return FeatureValue("not_applicable", None), "VWRA is not compared with itself"
    peer = session_on_or_before(vwra.dates, listing.dates[index], 5)
    if peer is None or peer < steps:
        return FeatureValue(
            "insufficient_peer_date", None
        ), "no VWRA session inside the five-day tolerance"
    own = trailing_return(listing.closes, index, steps)
    if own.value is None:
        return own, PRICE_DETAIL
    peer_return = vwra.closes[peer] / vwra.closes[peer - steps] - 1
    excess = Decimal(own.value) - peer_return
    return FeatureValue("observed", decimal_text(excess)), PRICE_DETAIL


def _economic_states(
    anchor_id: str,
    session: date,
    series: Sequence[StoredSeries],
    recorded_at: datetime,
) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for curve in series:
        cut = bisect.bisect_right(curve.bounds, session)
        features = economic_features(curve.points[:cut], session)
        for name, feature in features.items():
            rows.append(
                _state(
                    anchor_id,
                    f"{curve.dataset_id}:{name}",
                    "economic_retrospective",
                    feature,
                    RETROSPECTIVE,
                    False,
                    RETRO_DETAIL,
                    recorded_at,
                )
            )
    return rows


def as_of_gdp(vintages: Sequence[VintageRow], as_of: date) -> list[EconomicPoint]:
    """Latest printed vintage for each quarter with a release date on or before as_of."""
    chosen: dict[date, VintageRow] = {}
    for row in vintages:
        if row.release_date > as_of:
            continue
        current = chosen.get(row.period_start)
        if (
            current is not None
            and current.release_date == row.release_date
            and current.value != row.value
        ):
            raise AtlasBuildError("one quarter has two values on the same release date")
        if current is None or row.release_date >= current.release_date:
            chosen[row.period_start] = row
    return [
        EconomicPoint(row.period_start, row.period_end, "quarterly", row.value)
        for _period, row in sorted(chosen.items())
    ]


def _pit_states(
    anchor_id: str,
    points: Sequence[EconomicPoint],
    session: date,
    recorded_at: datetime,
) -> list[tuple[object, ...]]:
    if not points:
        features = {
            name: FeatureValue("insufficient_no_vintage", None)
            for name in (
                "level",
                "direction",
                "difference",
                "percent_change",
                "year_on_year",
                "acceleration",
                "persistence",
                "trailing_percentile",
                "trailing_standardisation",
            )
        }
    else:
        features = economic_features(points, session)
    return [
        _state(
            anchor_id,
            f"{POINT_IN_TIME_DATASET}:{name}",
            "point_in_time",
            feature,
            POINT_IN_TIME,
            feature.availability == "observed",
            PIT_DETAIL,
            recorded_at,
        )
        for name, feature in features.items()
    ]


def compile_listing(
    listing: ListingSeries,
    *,
    specification_hash: str,
    series: Sequence[StoredSeries],
    pit_by_release: Sequence[tuple[date, tuple[EconomicPoint, ...]]],
    vwra: ListingSeries,
    recorded_at: datetime,
) -> tuple[
    list[tuple[object, ...]],
    list[tuple[object, ...]],
    list[tuple[object, ...]],
    list[SequenceDecision],
]:
    """Month-end anchors, states, outcomes, and eligible sequence rows for one listing."""
    release_dates = [item[0] for item in pit_by_release]
    anchors: list[tuple[object, ...]] = []
    states: list[tuple[object, ...]] = []
    outcomes: list[tuple[object, ...]] = []
    for index in month_end_indices(listing.dates):
        session = listing.dates[index]
        identity = anchor_identity(listing.symbol, "listing_month_end", session)
        anchors.append(
            (
                identity,
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                specification_hash,
                listing.symbol,
                "listing_month_end",
                session,
                index >= 252,
                listing.currency,
                False,
                recorded_at,
            )
        )
        states.append(
            _state(
                identity,
                "split_adjusted_close",
                "market",
                FeatureValue("observed", decimal_text(listing.closes[index])),
                STORED_SESSIONS,
                True,
                PRICE_DETAIL,
                recorded_at,
            )
        )
        for steps in SESSION_STEPS.values():
            for name in (
                "trailing_return",
                "trailing_return_acceleration",
                "drawdown",
                "recovery_from_prior_trough",
                "volatility",
            ):
                states.append(
                    _state(
                        identity,
                        f"{name}_{steps}",
                        "market",
                        _market_feature(listing.closes, index, steps, name),
                        STORED_SESSIONS,
                        True,
                        PRICE_DETAIL,
                        recorded_at,
                    )
                )
            relative, detail = _relative(listing, index, steps, vwra)
            states.append(
                _state(
                    identity,
                    f"relative_performance_vs_vwra_{steps}",
                    "market",
                    relative,
                    STORED_SESSIONS,
                    True,
                    detail,
                    recorded_at,
                )
            )
            status, text = outcome_at(listing.closes, index, steps)
            labelled: bool | None = None
            if status == "observed" and steps == 126 and text is not None:
                labelled = Decimal(text) >= Decimal("0.10")
            outcomes.append(
                (
                    f"{identity}:outcome_{steps}",
                    identity,
                    _horizon(steps),
                    steps,
                    status,
                    text,
                    labelled,
                    False,
                    False,
                    False,
                    recorded_at,
                )
            )
        states.extend(_economic_states(identity, session, series, recorded_at))
        release_at = bisect.bisect_right(release_dates, session) - 1
        pit_points = () if release_at < 0 else pit_by_release[release_at][1]
        states.extend(_pit_states(identity, pit_points, session, recorded_at))
    decisions = evaluate_listing(listing.symbol, listing.dates, listing.closes)
    return anchors, states, outcomes, decisions


def _horizon(steps: int) -> str:
    for label, value in SESSION_STEPS.items():
        if value == steps:
            return label
    raise AtlasBuildError(f"session step {steps} is not frozen")


def compile_releases(
    vintages: Sequence[VintageRow],
    *,
    specification_hash: str,
    recorded_at: datetime,
) -> tuple[
    list[tuple[object, ...]], list[tuple[object, ...]], list[tuple[date, tuple[EconomicPoint, ...]]]
]:
    releases = sorted({row.release_date for row in vintages})
    pit_by_release: list[tuple[date, tuple[EconomicPoint, ...]]] = []
    anchors: list[tuple[object, ...]] = []
    states: list[tuple[object, ...]] = []
    for release in releases:
        points = tuple(as_of_gdp(vintages, release))
        pit_by_release.append((release, points))
        identity = anchor_identity(POINT_IN_TIME_DATASET, "bea_gdp_release", release)
        anchors.append(
            (
                identity,
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                specification_hash,
                POINT_IN_TIME_DATASET,
                "bea_gdp_release",
                release,
                bool(points),
                None,
                False,
                recorded_at,
            )
        )
        states.extend(_pit_states(identity, points, release, recorded_at))
    return anchors, states, pit_by_release


def link_events(
    events: Sequence[StoredEvent],
    anchor_dates: dict[str, list[tuple[date, str]]],
    recorded_at: datetime,
) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for event in events:
        choices = anchor_dates.get(event.symbol, [])
        dates = [item[0] for item in choices]
        position = bisect.bisect_right(dates, event.start_date) - 1
        if position < 0:
            continue
        rows.append((choices[position][1], event.event_id, "preceding_state", False, recorded_at))
    return rows


def group_episodes(
    events: Sequence[StoredEvent],
    *,
    recorded_at: datetime,
) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    grouped: dict[str, list[StoredEvent]] = defaultdict(list)
    for event in events:
        grouped[event.symbol].append(event)
    episodes: list[tuple[object, ...]] = []
    membership: list[tuple[object, ...]] = []
    for symbol in sorted(grouped):
        ordered = sorted(
            grouped[symbol], key=lambda item: (item.start_date, item.end_date, item.event_id)
        )
        clusters: list[list[StoredEvent]] = []
        current: list[StoredEvent] = []
        cluster_end: date | None = None
        for event in ordered:
            if cluster_end is None or event.start_date > cluster_end:
                if current:
                    clusters.append(current)
                current = [event]
                cluster_end = event.end_date
            else:
                current.append(event)
                if event.end_date > cluster_end:
                    cluster_end = event.end_date
        if current:
            clusters.append(current)
        for ordinal, cluster in enumerate(clusters, start=1):
            episode_id = (
                f"{SPECIFICATION_ID}:{SPECIFICATION_VERSION}:{symbol}:episode:{ordinal:04d}"
            )
            start = min(item.start_date for item in cluster)
            end = max(item.end_date for item in cluster)
            episodes.append(
                (
                    episode_id,
                    SPECIFICATION_ID,
                    SPECIFICATION_VERSION,
                    symbol,
                    start,
                    end,
                    len(cluster),
                    False,
                    recorded_at,
                )
            )
            for event in cluster:
                membership.append((episode_id, event.event_id, False, recorded_at))
    return episodes, membership


def method_inventory_payload(method: object, stored_datasets: set[str]) -> dict[str, object]:
    dependency = method.dependency()
    inputs = list(method.required_dataset_ids())
    missing = [dataset for dataset in inputs if dataset not in stored_datasets]
    module = inspect.getmodule(method)
    docstring = (module.__doc__ or "").strip() if module is not None else ""
    output = docstring.splitlines()[0] if docstring else str(method.method_id)
    replay = "unavailable_input" if missing else "not_historically_replayed"
    return {
        "method_id": method.method_id,
        "method_version": method.method_version,
        "class_name": type(method).__name__,
        "vintage_class": dependency.vintage_class,
        "inputs": inputs,
        "output_definition": output,
        "replay_status": replay,
        "point_in_time": False,
        "missing_inputs": missing,
    }


def checksum_lines(batch: AtlasBatch, specification_hash: str) -> list[str]:
    lines = [f"specification|{specification_hash}"]
    for row in batch.anchors:
        session = row[6].isoformat()
        lookback = str(row[7]).lower()
        currency = row[8] or ""
        lines.append(f"anchor|{row[0]}|{row[4]}|{row[5]}|{session}|{lookback}|{currency}")
    for row in batch.states:
        usable = str(row[6]).lower()
        value = row[7] or ""
        lines.append(
            f"state|{row[0]}|{row[2]}|{row[3]}|{row[4]}|{row[5]}|{usable}|{value}|{row[8]}"
        )
    for row in batch.outcomes:
        labelled = "" if row[6] is None else str(row[6]).lower()
        lines.append(f"outcome|{row[0]}|{row[2]}|{row[3]}|{row[4]}|{row[5] or ''}|{labelled}")
    for row in batch.inventory:
        lines.append(f"inventory|{row[2]}|{row[3]}|{canonical_json(row[4])}")
    for row in batch.links:
        lines.append(f"link|{row[0]}|{row[1]}|{row[2]}")
    for row in batch.episodes:
        lines.append(
            f"episode|{row[0]}|{row[3]}|{row[4].isoformat()}|{row[5].isoformat()}|{row[6]}"
        )
    for row in batch.episode_events:
        lines.append(f"episode_event|{row[0]}|{row[1]}")
    lines.sort()
    return lines


def content_checksum(lines: Sequence[str]) -> str:
    import hashlib

    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()
