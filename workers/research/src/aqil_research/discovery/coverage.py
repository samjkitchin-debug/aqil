"""Gate 0 cells. Counts are computed before any correlation."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from aqil_research.discovery.eligibility import SampleFloors, meets_exploratory
from aqil_research.discovery.features import (
    difference_over,
    level,
    ratio_change_over,
)
from aqil_research.discovery.load import ListingHistory, StudyData
from aqil_research.discovery.pairs import align_forward_returns, non_overlapping_count

MATRIX_FIELDS = (
    "feature_id",
    "etf",
    "isin",
    "mic",
    "currency",
    "distribution_policy",
    "horizon_months",
    "decision_points",
    "non_overlapping",
    "missing_windows",
    "weekday_gaps",
    "point_in_time_class",
    "status",
    "missing_input",
    "qualification",
    "first_pass",
)


def materialise_feature(
    spec: dict[str, object],
    series: dict[str, dict[date, Decimal]],
) -> dict[date, Decimal] | None:
    """Build one named feature. An unknown kind is refused."""
    kind = str(spec["kind"])
    if kind == "level":
        source = series.get(str(spec["dataset_id"]))
        return None if not source else level(source)
    if kind == "difference":
        source = series.get(str(spec["dataset_id"]))
        if not source:
            return None
        return difference_over(source, int(spec["months"]))
    if kind == "ratio_change":
        source = series.get(str(spec["dataset_id"]))
        if not source:
            return None
        return ratio_change_over(source, int(spec["months"]))
    if kind in {"spread", "spread_difference"}:
        longer = series.get(str(spec["long_dataset_id"]))
        shorter = series.get(str(spec["short_dataset_id"]))
        if not longer or not shorter:
            return None
        spread = {
            period: longer[period] - shorter[period] for period in longer.keys() & shorter.keys()
        }
        if kind == "spread":
            return spread
        return difference_over(spread, int(spec["months"]))
    raise ValueError(f"unknown feature kind: {kind}")


def build_matrix(
    study: StudyData,
    catalogue: dict[str, object],
    register_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    floors = _floors(catalogue)
    lag = int(catalogue["assumed_lag_months"])
    maximum_gap_days = int(catalogue["maximum_decision_to_entry_days"])
    horizons = [int(item) for item in catalogue["horizons_months"]]  # type: ignore[union-attr]
    first_pass = set(catalogue["first_pass_etfs"])  # type: ignore[arg-type]
    features = catalogue["features"]
    rows: list[dict[str, object]] = []
    for feature in features:  # type: ignore[union-attr]
        signal = materialise_feature(feature, study.series)
        for register in register_rows:
            listing = study.listings.get(register["research_symbol"])
            for horizon in horizons:
                rows.append(
                    _cell(
                        feature=feature,
                        register=register,
                        listing=listing,
                        signal=signal,
                        horizon=horizon,
                        lag=lag,
                        maximum_gap_days=maximum_gap_days,
                        floors=floors,
                        first_pass=register["research_symbol"] in first_pass,
                    )
                )
    return rows


def write_matrix(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATRIX_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in MATRIX_FIELDS})


def status_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row["status"])
        counts[status] = counts.get(status, 0) + 1
    return counts


def _floors(catalogue: dict[str, object]) -> SampleFloors:
    raw = catalogue["floors"]
    return SampleFloors(
        exploratory_decision_points=int(raw["exploratory_decision_points"]),  # type: ignore[index]
        exploratory_non_overlapping=int(raw["exploratory_non_overlapping"]),  # type: ignore[index]
        statistical_decision_points=int(raw["statistical_decision_points"]),  # type: ignore[index]
        statistical_non_overlapping=int(raw["statistical_non_overlapping"]),  # type: ignore[index]
    )


def _cell(
    *,
    feature: dict[str, object],
    register: dict[str, str],
    listing: ListingHistory | None,
    signal: dict[date, Decimal] | None,
    horizon: int,
    lag: int,
    maximum_gap_days: int,
    floors: SampleFloors,
    first_pass: bool,
) -> dict[str, object]:
    base = {
        "feature_id": feature["feature_id"],
        "etf": register["research_symbol"],
        "isin": register["isin"],
        "mic": "",
        "currency": register["listing_currency"],
        "distribution_policy": register["distribution_policy"].lower(),
        "horizon_months": horizon,
        "decision_points": 0,
        "non_overlapping": 0,
        "missing_windows": 0,
        "weekday_gaps": 0,
        "point_in_time_class": "blocked",
        "status": "blocked",
        "missing_input": "",
        "qualification": "",
        "first_pass": str(first_pass).lower(),
    }
    if listing is None:
        base["missing_input"] = "no stored listing price"
        return base
    base["mic"] = listing.mic
    base["currency"] = listing.currency
    base["distribution_policy"] = listing.distribution_policy
    base["weekday_gaps"] = listing.weekday_gaps
    if listing.isin != register["isin"]:
        base["missing_input"] = "stored ISIN does not match the register"
        return base
    if listing.currency != register["listing_currency"]:
        base["missing_input"] = "stored currency does not match the register"
        return base
    if listing.distribution_policy == "distributing":
        base["missing_input"] = "no dividend is stored for a distributing class"
        return base
    if signal is None:
        base["missing_input"] = "the series needed for this feature is not stored"
        return base
    base["point_in_time_class"] = "retrospective_assumed_lag"
    paired = align_forward_returns(
        signal,
        listing.sessions,
        listing.prices,
        horizon_months=horizon,
        lag_months=lag,
        quote_unit=listing.quote_unit,
        distribution_policy=listing.distribution_policy,
        inception_bound=listing.sessions[0],
        dividend=None,
        maximum_gap_days=maximum_gap_days,
    )
    decision_points = len(paired.pairs)
    non_overlap = non_overlapping_count(paired.pairs)
    base["decision_points"] = decision_points
    base["non_overlapping"] = non_overlap
    base["missing_windows"] = paired.missing_windows
    notes = [
        "Latest-revised inputs use an assumed one-month lag. "
        "That lag is not a stored release time.",
        "The legal inception date is not stored. The return bound is the first stored session.",
        "The return is a split-adjusted listing price ratio, "
        "not an issuer total-return index and not NAV.",
    ]
    if listing.currency != "USD":
        notes.append(
            "This listing stays in its stored currency and is not pooled into a USD result."
        )
    base["qualification"] = " ".join(notes)
    if not meets_exploratory(decision_points, non_overlap, floors):
        base["missing_input"] = (
            "exploratory floor requires 36 monthly decision points and 8 non-overlapping windows"
        )
        return base
    base["status"] = "retrospective_only"
    return base
