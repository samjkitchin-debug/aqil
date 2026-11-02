"""Gates 1 to 6. A cell that misses a floor is recorded and not promoted."""

from __future__ import annotations

import zlib
from datetime import date
from decimal import Decimal
from typing import Any

from aqil_research.discovery.association import (
    AssociationError,
    added_slope_p,
    associate,
    benjamini_hochberg,
    claim_class,
)
from aqil_research.discovery.coverage import materialise_feature
from aqil_research.discovery.eligibility import SampleFloors, meets_exploratory, meets_statistical
from aqil_research.discovery.load import StudyData
from aqil_research.discovery.pairs import (
    AlignedPair,
    align_forward_returns,
    non_overlapping_count,
    split_holdout,
)
from aqil_research.methods.restricted_coincident_diffusion import restricted_coincident_diffusion
from aqil_research.methods.sahm import SahmConfig, SahmMethodError, run_sahm
from aqil_research.methods.stock_watson_1988_fit import MODERN_REFIT_DATASETS

PointClass = "retrospective_assumed_lag"


def rerun_pilot(
    study: StudyData,
    catalogue: dict[str, Any],
    matrix_rows: list[dict[str, object]],
) -> dict[str, Any]:
    """Recompute the preregistered pilot from the same inputs."""
    return _Context(study, catalogue, matrix_rows).pilot()


def run_gates(
    study: StudyData,
    catalogue: dict[str, Any],
    matrix_rows: list[dict[str, object]],
) -> list[dict[str, Any]]:
    """Run the preregistered pilot and every later gate the matrix leaves eligible."""
    context = _Context(study, catalogue, matrix_rows)
    records: list[dict[str, Any]] = []
    records.append(context.pilot())
    descriptive = context.descriptive_family()
    records.extend(descriptive)
    inferential = context.inferential_family()
    records.extend(inferential)
    records.extend(context.gate2())
    records.extend(context.gate3_and_4())
    records.extend(context.gate5_and_6(inferential))
    return records


class _Context:
    def __init__(
        self,
        study: StudyData,
        catalogue: dict[str, Any],
        matrix_rows: list[dict[str, object]],
    ) -> None:
        self.study = study
        self.catalogue = catalogue
        self.matrix = {
            (str(row["feature_id"]), str(row["etf"]), int(row["horizon_months"])): row
            for row in matrix_rows
        }
        self.features = {str(item["feature_id"]): item for item in catalogue["features"]}
        self.floors = SampleFloors(
            exploratory_decision_points=int(catalogue["floors"]["exploratory_decision_points"]),
            exploratory_non_overlapping=int(catalogue["floors"]["exploratory_non_overlapping"]),
            statistical_decision_points=int(catalogue["floors"]["statistical_decision_points"]),
            statistical_non_overlapping=int(catalogue["floors"]["statistical_non_overlapping"]),
        )
        self.lag = int(catalogue["assumed_lag_months"])
        self.maximum_gap_days = int(catalogue["maximum_decision_to_entry_days"])
        self.holdout = date.fromisoformat(catalogue["holdout"]["decision_period_on_or_after"])
        self.alpha = float(catalogue["primary_test"]["alpha"])
        self.replicates = int(catalogue["bootstrap"]["replicates"])
        self.base_seed = int(catalogue["bootstrap"]["seed"])
        self.collinear = float(catalogue["collinearity_abs_pearson"])
        self.signals = {
            feature_id: materialise_feature(spec, study.series)
            for feature_id, spec in self.features.items()
        }

    def pilot(self) -> dict[str, Any]:
        pilot = self.catalogue["pilot"]
        feature_id = str(pilot["feature_id"])
        etf = str(pilot["etf"])
        horizon = int(pilot["horizon_months"])
        cell = f"pilot:{feature_id}:{etf}:{horizon}"
        row = self.matrix[(feature_id, etf, horizon)]
        pairs = self._pairs(feature_id, etf, horizon)
        below = str(row["status"]) != "retrospective_only"
        payload = self._estimate(pairs, horizon, cell)
        payload["decision_points"] = len(pairs)
        payload["non_overlapping"] = non_overlapping_count(pairs)
        payload["missing_windows"] = int(row["missing_windows"])
        payload["below_exploratory_floor"] = below
        return self._record(
            gate="pilot",
            cell_id=cell,
            status="blocked" if below or not payload.get("estimated") else "retrospective_only",
            evidence="not_claimed" if below or not payload.get("estimated") else "exploratory",
            payload=payload,
        )

    def descriptive_family(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for key, row in sorted(self.matrix.items()):
            feature_id, etf, horizon = key
            if not self._search_cell(row) or self._is_pilot(feature_id, etf, horizon):
                continue
            pairs = self._pairs(feature_id, etf, horizon)
            payload = self._estimate(pairs, horizon, f"gate1:{feature_id}:{etf}:{horizon}")
            payload["sample"] = "full_stored_overlap"
            payload["selection_statistic"] = False
            records.append(
                self._record(
                    gate="1",
                    cell_id=f"gate1:{feature_id}:{etf}:{horizon}",
                    status="retrospective_only" if payload.get("estimated") else "blocked",
                    evidence="exploratory" if payload.get("estimated") else "not_claimed",
                    payload=payload,
                )
            )
        return records

    def inferential_family(self) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for key, row in sorted(self.matrix.items()):
            feature_id, etf, horizon = key
            if not self._search_cell(row) or self._is_pilot(feature_id, etf, horizon):
                continue
            training, holdout = split_holdout(self._pairs(feature_id, etf, horizon), self.holdout)
            if not meets_statistical(
                len(training),
                non_overlapping_count(training),
                self.floors,
            ):
                continue
            cell = f"gate1-training:{feature_id}:{etf}:{horizon}"
            payload = self._estimate(training, horizon, cell)
            payload["sample"] = "training_before_holdout"
            payload["holdout_decision_points"] = len(holdout)
            payload["training_decision_points"] = len(training)
            payload["training_non_overlapping"] = non_overlapping_count(training)
            if not payload.get("estimated"):
                candidates.append(
                    self._record(
                        gate="1-inferential",
                        cell_id=cell,
                        status="blocked",
                        evidence="not_claimed",
                        payload=payload,
                    )
                )
                continue
            candidates.append(
                {
                    "_pending": True,
                    "cell": cell,
                    "feature_id": feature_id,
                    "etf": etf,
                    "horizon": horizon,
                    "payload": payload,
                    "holdout_pairs": holdout,
                    "training_pairs": training,
                }
            )
        estimated = [item for item in candidates if item.get("_pending")]
        adjusted = benjamini_hochberg([float(item["payload"]["slope_p"]) for item in estimated])
        records: list[dict[str, Any]] = [item for item in candidates if not item.get("_pending")]
        for item, bh_p in zip(estimated, adjusted, strict=True):
            payload = dict(item["payload"])
            payload["bh_p"] = bh_p
            payload["family_size"] = len(estimated)
            rejects = bh_p < self.alpha and bool(payload.get("bootstrap_excludes_zero"))
            confirmed = False
            if rejects:
                holdout_payload = self._estimate(
                    item["holdout_pairs"],
                    int(item["horizon"]),
                    item["cell"] + ":holdout",
                )
                payload["holdout"] = holdout_payload
                confirmed = _same_sign(payload, holdout_payload) and int(
                    holdout_payload.get("n", 0)
                ) >= int(self.catalogue["holdout"]["minimum_decision_points"])
                payload["holdout_confirms"] = confirmed
            evidence = claim_class(
                is_null_control=False,
                below_floor=False,
                statistical_bar=True,
                bh_rejects=rejects,
                holdout_confirms=confirmed,
                economic_advantage=False,
                bootstrap_excludes_zero=bool(payload.get("bootstrap_excludes_zero")),
                forward_frozen=False,
            )
            payload["training_pairs_retained"] = False
            records.append(
                self._record(
                    gate="1-inferential",
                    cell_id=str(item["cell"]),
                    status="retrospective_only",
                    evidence=evidence,
                    payload=payload,
                )
            )
        if not estimated:
            records.append(
                self._record(
                    gate="6",
                    cell_id="holdout",
                    status="blocked",
                    evidence="not_claimed",
                    payload={
                        "reason": "no cell met the training-window statistical floor",
                        "holdout_run": False,
                    },
                )
            )
        return records

    def gate2(self) -> list[dict[str, Any]]:
        groups: dict[str, list[str]] = {}
        for feature_id, spec in self.features.items():
            groups.setdefault(str(spec["group"]), []).append(feature_id)
        attempts: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        for group, members in sorted(groups.items()):
            if len(members) < 2:
                continue
            left_id, right_id = sorted(members)
            for etf in self.catalogue["first_pass_etfs"]:
                for horizon in self.catalogue["horizons_months"]:
                    if not self._both_eligible(left_id, right_id, etf, int(horizon)):
                        continue
                    cell = f"gate2:{group}:{etf}:{horizon}"
                    attempt = self._incremental(left_id, right_id, etf, int(horizon), cell)
                    attempt["group"] = group
                    if attempt.get("estimated"):
                        attempts.append(attempt | {"cell": cell})
                    else:
                        records.append(
                            self._record(
                                gate="2",
                                cell_id=cell,
                                status="blocked",
                                evidence="not_claimed",
                                payload=attempt,
                            )
                        )
        adjusted = benjamini_hochberg([float(item["added_p"]) for item in attempts])
        for item, bh_p in zip(attempts, adjusted, strict=True):
            payload = {key: value for key, value in item.items() if key != "cell"}
            payload["bh_p"] = bh_p
            payload["family_size"] = len(attempts)
            evidence = "exploratory"
            if (
                bh_p < self.alpha
                and item.get("statistical_bar")
                and item.get("bootstrap_excludes_zero")
            ):
                evidence = "exploratory"
                payload["promotion"] = (
                    "incremental result stays inside Gate 2; it is not a held-out claim"
                )
            records.append(
                self._record(
                    gate="2",
                    cell_id=str(item["cell"]),
                    status="retrospective_only" if item.get("estimated") else "blocked",
                    evidence=evidence,
                    payload=payload,
                )
            )
        if not attempts and not records:
            records.append(
                self._record(
                    gate="2",
                    cell_id="combinations",
                    status="blocked",
                    evidence="not_claimed",
                    payload={
                        "reason": "no eligible pair of collinear cousins met the training floor"
                    },
                )
            )
        return records

    def gate3_and_4(self) -> list[dict[str, Any]]:
        indicators = self._indicators()
        records: list[dict[str, Any]] = []
        attempts: list[dict[str, Any]] = []
        for spec in self.catalogue["gate3"]:
            indicator = indicators.get(str(spec["indicator_id"]))
            if indicator is None:
                records.append(
                    self._record(
                        gate="3",
                        cell_id=str(spec["indicator_id"]),
                        status="blocked",
                        evidence="not_claimed",
                        payload={
                            "reason": indicators.get(
                                "_error", "the indicator could not be recomputed"
                            )
                        },
                    )
                )
                continue
            baseline = self._baseline(spec)
            for etf in self.catalogue["first_pass_etfs"]:
                for horizon in self.catalogue["horizons_months"]:
                    cell = f"gate3:{spec['indicator_id']}:{etf}:{horizon}"
                    attempt = self._indicator_increment(
                        indicator,
                        baseline,
                        etf,
                        int(horizon),
                        cell,
                        str(spec["indicator_id"]),
                    )
                    if not attempt.get("eligible"):
                        records.append(
                            self._record(
                                gate="3",
                                cell_id=cell,
                                status="blocked",
                                evidence="not_claimed",
                                payload=attempt,
                            )
                        )
                        continue
                    attempts.append(attempt | {"cell": cell, "indicator_id": spec["indicator_id"]})
        adjusted = benjamini_hochberg(
            [float(item["added_p"]) for item in attempts if item.get("estimated")]
        )
        estimated = [item for item in attempts if item.get("estimated")]
        distinct: dict[str, dict[str, Any]] = {}
        cursor = 0
        for item in attempts:
            if not item.get("estimated"):
                records.append(
                    self._record(
                        gate="3",
                        cell_id=str(item["cell"]),
                        status="blocked",
                        evidence="not_claimed",
                        payload={key: value for key, value in item.items() if key != "cell"},
                    )
                )
                continue
            bh_p = adjusted[cursor]
            cursor += 1
            payload = {
                key: value for key, value in item.items() if key not in {"cell", "indicator_id"}
            }
            payload["bh_p"] = bh_p
            payload["family_size"] = len(estimated)
            is_distinct = (
                bh_p < self.alpha
                and bool(item.get("statistical_bar"))
                and bool(item.get("bootstrap_excludes_zero"))
            )
            payload["distinct_information"] = is_distinct
            if is_distinct:
                distinct[str(item["indicator_id"])] = item
            records.append(
                self._record(
                    gate="3",
                    cell_id=str(item["cell"]),
                    status="retrospective_only",
                    evidence="exploratory",
                    payload=payload,
                )
            )
        records.append(self._gate4(distinct))
        return records

    def gate5_and_6(self, inferential: list[dict[str, Any]]) -> list[dict[str, Any]]:
        supported = [
            record
            for record in inferential
            if record["evidence_class"] == "statistically_supported"
        ]
        records: list[dict[str, Any]] = []
        if any(record["gate"] == "6" for record in inferential):
            holdout_already = True
        else:
            holdout_already = False
        if not supported:
            if not holdout_already:
                records.append(
                    self._record(
                        gate="6",
                        cell_id="holdout",
                        status="blocked",
                        evidence="not_claimed",
                        payload={
                            "reason": (
                                "no inferential cell survived false-discovery control "
                                "and the holdout"
                            ),
                            "holdout_run": any(
                                record["payload"].get("holdout_confirms") is False
                                and record["payload"].get("holdout")
                                for record in inferential
                            ),
                        },
                    )
                )
            records.append(
                self._record(
                    gate="5",
                    cell_id="economic",
                    status="blocked",
                    evidence="not_claimed",
                    payload={
                        "reason": (
                            "no cell met the statistically supported bar, "
                            "so the economic comparison was not run"
                        ),
                    },
                )
            )
            return records
        records.append(
            self._record(
                gate="5",
                cell_id="economic",
                status="blocked",
                evidence="not_claimed",
                payload={"reason": "supported cells are compared individually"},
            )
        )
        return records

    def _gate4(self, distinct: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if len(distinct) < 2:
            return self._record(
                gate="4",
                cell_id="methodology-combinations",
                status="blocked",
                evidence="not_claimed",
                payload={
                    "reason": "fewer than two Gate 3 outputs carried distinct information",
                    "distinct_indicators": sorted(distinct),
                },
            )
        return self._record(
            gate="4",
            cell_id="methodology-combinations",
            status="blocked",
            evidence="not_claimed",
            payload={
                "reason": "a composite macro score is not estimated",
                "distinct_indicators": sorted(distinct),
            },
        )

    def _baseline(self, spec: dict[str, Any]) -> dict[date, Decimal] | None:
        if "baseline_dataset_id" in spec:
            return self.study.series.get(str(spec["baseline_dataset_id"])) or None
        return self.signals.get(str(spec["baseline_feature_id"]))

    def _indicators(self) -> dict[str, Any]:
        found: dict[str, Any] = {}
        try:
            found["sahm_gap"] = _sahm_gap(self.study.observations["bls.ln.LNS14000000"])
        except (SahmMethodError, KeyError, ValueError) as exc:
            found["_error"] = str(exc)
        try:
            found["diffusion_share"] = _diffusion(self.study.series)
        except (KeyError, ValueError) as exc:
            found["_error"] = str(exc)
        spread = self.signals.get("spread_level")
        if spread:
            found["spread_level"] = spread
        return found

    def _incremental(
        self,
        left_id: str,
        right_id: str,
        etf: str,
        horizon: int,
        cell: str,
    ) -> dict[str, Any]:
        left = self._training_pairs(left_id, etf, horizon)
        right = self._training_pairs(right_id, etf, horizon)
        joined = _join_signals(left, right)
        if not meets_exploratory(len(joined), _joined_non_overlap(joined), self.floors):
            return {
                "estimated": False,
                "reason": "the training window is below the exploratory floor",
                "training_decision_points": len(joined),
            }
        y = [float(pair.forward_return) for pair, _other in joined]
        x1 = [float(pair.signal) for pair, _other in joined]
        x2 = [float(other.signal) for _pair, other in joined]
        try:
            added_p, added_slope = added_slope_p(
                y,
                x1,
                x2,
                maxlags=horizon - 1,
                collinear_abs=self.collinear,
            )
        except AssociationError as exc:
            return {"estimated": False, "reason": str(exc), "training_decision_points": len(joined)}
        return {
            "estimated": True,
            "added_p": added_p,
            "added_slope": added_slope,
            "training_decision_points": len(joined),
            "statistical_bar": meets_statistical(
                len(joined), _joined_non_overlap(joined), self.floors
            ),
            "bootstrap_excludes_zero": False,
            "cell_seed": _seed(self.base_seed, cell),
        }

    def _indicator_increment(
        self,
        indicator: dict[date, Decimal],
        baseline: dict[date, Decimal] | None,
        etf: str,
        horizon: int,
        cell: str,
        indicator_id: str,
    ) -> dict[str, Any]:
        listing = self.study.listings.get(etf)
        if listing is None or baseline is None or not indicator:
            return {
                "eligible": False,
                "estimated": False,
                "reason": "the indicator or its baseline is missing",
            }
        indicator_pairs = self._align(indicator, listing, horizon)
        baseline_pairs = self._training_only(self._align(baseline, listing, horizon))
        indicator_training = self._training_only(indicator_pairs)
        if not meets_exploratory(
            len(indicator_pairs),
            non_overlapping_count(indicator_pairs),
            self.floors,
        ):
            return {
                "eligible": False,
                "estimated": False,
                "reason": "the indicator does not meet the exploratory floor",
                "decision_points": len(indicator_pairs),
                "non_overlapping": non_overlapping_count(indicator_pairs),
            }
        joined = _join_signals(baseline_pairs, indicator_training)
        if not meets_exploratory(len(joined), _joined_non_overlap(joined), self.floors):
            return {
                "eligible": False,
                "estimated": False,
                "reason": "the training comparison is below the exploratory floor",
            }
        y = [float(pair.forward_return) for pair, _other in joined]
        x1 = [float(pair.signal) for pair, _other in joined]
        x2 = [float(other.signal) for _pair, other in joined]
        try:
            added_p, added_slope = added_slope_p(
                y,
                x1,
                x2,
                maxlags=max(horizon - 1, 0),
                collinear_abs=self.collinear,
            )
        except AssociationError as exc:
            return {"eligible": True, "estimated": False, "reason": str(exc), "cell": cell}
        return {
            "eligible": True,
            "estimated": True,
            "added_p": added_p,
            "added_slope": added_slope,
            "indicator_id": indicator_id,
            "statistical_bar": meets_statistical(
                len(joined), _joined_non_overlap(joined), self.floors
            ),
            "bootstrap_excludes_zero": False,
            "cell": cell,
        }

    def _both_eligible(self, left_id: str, right_id: str, etf: str, horizon: int) -> bool:
        left = self.matrix.get((left_id, etf, horizon))
        right = self.matrix.get((right_id, etf, horizon))
        return bool(
            left
            and right
            and left["status"] == "retrospective_only"
            and right["status"] == "retrospective_only"
        )

    def _search_cell(self, row: dict[str, object]) -> bool:
        return row["status"] == "retrospective_only" and row["first_pass"] == "true"

    def _is_pilot(self, feature_id: str, etf: str, horizon: int) -> bool:
        pilot = self.catalogue["pilot"]
        return (
            feature_id == pilot["feature_id"]
            and etf == pilot["etf"]
            and horizon == int(pilot["horizon_months"])
        )

    def _pairs(self, feature_id: str, etf: str, horizon: int) -> tuple[AlignedPair, ...]:
        signal = self.signals[feature_id]
        listing = self.study.listings[etf]
        if signal is None:
            return ()
        return self._align(signal, listing, horizon)

    def _align(
        self, signal: dict[date, Decimal], listing: Any, horizon: int
    ) -> tuple[AlignedPair, ...]:
        return align_forward_returns(
            signal,
            listing.sessions,
            listing.prices,
            horizon_months=horizon,
            lag_months=self.lag,
            quote_unit=listing.quote_unit,
            distribution_policy=listing.distribution_policy,
            inception_bound=listing.sessions[0],
            dividend=None,
            maximum_gap_days=self.maximum_gap_days,
        ).pairs

    def _training_pairs(self, feature_id: str, etf: str, horizon: int) -> tuple[AlignedPair, ...]:
        return self._training_only(self._pairs(feature_id, etf, horizon))

    def _training_only(self, pairs: tuple[AlignedPair, ...]) -> tuple[AlignedPair, ...]:
        training, _holdout = split_holdout(pairs, self.holdout)
        return training

    def _estimate(self, pairs: tuple[AlignedPair, ...], horizon: int, cell: str) -> dict[str, Any]:
        if len(pairs) < 3:
            return {"estimated": False, "reason": "fewer than three pairs", "n": len(pairs)}
        try:
            fit = associate(
                [float(pair.signal) for pair in pairs],
                [float(pair.forward_return) for pair in pairs],
                maxlags=max(horizon - 1, 0),
                block=horizon,
                replicates=self.replicates,
                seed=_seed(self.base_seed, cell),
            )
        except AssociationError as exc:
            return {"estimated": False, "reason": str(exc), "n": len(pairs)}
        excludes = fit.bootstrap_low is not None and (
            fit.bootstrap_low > 0 or fit.bootstrap_high is not None and fit.bootstrap_high < 0
        )
        return {
            "estimated": True,
            "n": fit.n,
            "pearson_r": fit.pearson_r,
            "pearson_p": fit.pearson_p,
            "spearman_r": fit.spearman_r,
            "spearman_p": fit.spearman_p,
            "intercept": fit.intercept,
            "slope": fit.slope,
            "slope_se": fit.slope_se,
            "slope_p": fit.slope_p,
            "maxlags": fit.maxlags,
            "bootstrap_low": fit.bootstrap_low,
            "bootstrap_high": fit.bootstrap_high,
            "bootstrap_excludes_zero": excludes,
        }

    def _record(
        self,
        *,
        gate: str,
        cell_id: str,
        status: str,
        evidence: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "record_type": "trial",
            "trial_id": f"{gate}:{cell_id}",
            "catalogue_hash": self.catalogue["_hash"],
            "gate": gate,
            "cell_id": cell_id,
            "status": status,
            "point_in_time_class": PointClass,
            "evidence_class": evidence,
            "payload": payload,
        }


def _seed(base: int, cell: str) -> int:
    return base + (zlib.adler32(cell.encode("utf-8")) % 100_000)


def _same_sign(training: dict[str, Any], holdout: dict[str, Any]) -> bool:
    if not holdout.get("estimated"):
        return False
    left = float(training["slope"])
    right = float(holdout["slope"])
    return left * right > 0


def _join_signals(
    left: tuple[AlignedPair, ...],
    right: tuple[AlignedPair, ...],
) -> list[tuple[AlignedPair, AlignedPair]]:
    index = {pair.reference_month: pair for pair in right}
    return [(pair, index[pair.reference_month]) for pair in left if pair.reference_month in index]


def _joined_non_overlap(joined: list[tuple[AlignedPair, AlignedPair]]) -> int:
    return non_overlapping_count(tuple(pair for pair, _other in joined))


def _sahm_gap(observations: dict[date, Any]) -> dict[date, Decimal]:
    config = SahmConfig(
        config_id="discovery-sahm",
        threshold_percentage_points=Decimal("0.50"),
        label="Sahm 0.50 percentage points",
    )
    gaps: dict[date, Decimal] = {}
    for period in sorted(observations):
        try:
            gaps[period] = run_sahm(observations, period, config).gap_percentage_points
        except SahmMethodError:
            continue
    if gaps:
        return gaps
    run_sahm(observations, sorted(observations)[-1], config)
    return gaps


def _diffusion(series: dict[str, dict[date, Decimal]]) -> dict[date, Decimal]:
    levels = {
        dataset_id: {period: float(value) for period, value in series[dataset_id].items()}
        for dataset_id in MODERN_REFIT_DATASETS
    }
    result = restricted_coincident_diffusion(levels)
    return {
        month.period: Decimal(str(month.share))
        for month in result.months
        if month.share is not None
    }
