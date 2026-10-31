"""Recompute research from a persisted run's frozen observation evidence."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Literal

import psycopg

from aqil_research.methods.autoregressive_benchmark import (
    PUBLISHED_CONFIG as AUTOREGRESSIVE_BENCHMARK_PUBLISHED,
)
from aqil_research.methods.bai_perron_mean_shifts import (
    PUBLISHED_CONFIG as BAI_PERRON_MEAN_SHIFTS_PUBLISHED,
)
from aqil_research.methods.bry_boschan_spencer15 import (
    BRY_BOSCHAN_SPENCER15_VARIANT,
    BryBoschanSpencer15Method,
    legacy_variant_implementation_hash,
)
from aqil_research.methods.configs import (
    BRY_BOSCHAN_SPENCER15_PUBLISHED,
    CENSUS_ADV_ORDERS_PUBLISHED,
    MACRO_CONDITIONS_PUBLISHED,
    SAHM_PUBLISHED,
    SAHM_SENSITIVITY,
    SLOOS_CIL_PUBLISHED,
)
from aqil_research.methods.constant_maturity_spread_recession_probit import (
    ACCEPTED_CONFIG as CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT_PUBLISHED,
)
from aqil_research.methods.cpi_u_inflation_autoregression import (
    PUBLISHED_CONFIG as CPI_U_INFLATION_AUTREGRESSION_PUBLISHED,
)
from aqil_research.methods.cusum_recursive_residuals import (
    PUBLISHED_CONFIG as CUSUM_RECURSIVE_RESIDUALS_PUBLISHED,
)
from aqil_research.methods.engle_granger_cointegration import (
    PUBLISHED_CONFIG as ENGLE_GRANGER_COINTEGRATION_PUBLISHED,
)
from aqil_research.methods.estrella_mishkin import ESTRELLA_MISHKIN_PUBLISHED
from aqil_research.methods.ex_post_real_federal_funds import (
    PUBLISHED_CONFIG as EX_POST_REAL_FEDERAL_FUNDS_PUBLISHED,
)
from aqil_research.methods.ex_post_real_funds_rate import (
    PUBLISHED_CONFIG as EX_POST_REAL_FUNDS_RATE_PUBLISHED,
)
from aqil_research.methods.hamilton_monthly import HAMILTON_MONTHLY_PUBLISHED
from aqil_research.methods.harding_pagan_characteristics import (
    HARDING_PAGAN_CHARACTERISTICS_PUBLISHED,
)
from aqil_research.methods.inflation_autoregression import (
    PUBLISHED_CONFIG as INFLATION_AUTOREGRESSION_PUBLISHED,
)
from aqil_research.methods.ip_growth_cusum import PUBLISHED_CONFIG as IP_GROWTH_CUSUM_PUBLISHED
from aqil_research.methods.lead_lag import PUBLISHED_CONFIG as LEAD_LAG_PUBLISHED
from aqil_research.methods.registry import (
    MethodRegistry,
    MethodRegistryError,
    default_method_registry,
)
from aqil_research.methods.restricted_coincident_diffusion import (
    PUBLISHED_CONFIG as RESTRICTED_COINCIDENT_DIFFUSION_PUBLISHED,
)
from aqil_research.methods.stock_watson_1988_fit import (
    ACCEPTED_CONFIG,
    MULTISTART_CONFIG,
    REFIT_CONFIG,
    SPECIFICATION_ID,
)
from aqil_research.persistence.calculation_normalize import normalize_calculation_payload
from aqil_research.persistence.observation_store import load_observations_by_ids
from aqil_research.persistence.runs import load_research_run, load_run_observation_ids
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore


@dataclass(frozen=True, slots=True)
class RunReplayVerification:
    stored: ResearchRun
    recomputed: ResearchRun

    @property
    def calculation_match(self) -> bool:
        if self.stored.calculation is None and self.recomputed.calculation is None:
            return True
        if self.stored.calculation is None or self.recomputed.calculation is None:
            return False
        stored = normalize_calculation_payload(self.stored.calculation)
        recomputed = normalize_calculation_payload(self.recomputed.calculation)
        return json.dumps(stored, sort_keys=True) == json.dumps(recomputed, sort_keys=True)

    def calculation_mismatch_keys(self) -> tuple[str, ...]:
        if self.stored.calculation is None or self.recomputed.calculation is None:
            return ("calculation",)
        stored = normalize_calculation_payload(self.stored.calculation) or {}
        recomputed = normalize_calculation_payload(self.recomputed.calculation) or {}
        keys = sorted(set(stored) | set(recomputed))
        return tuple(key for key in keys if stored.get(key) != recomputed.get(key))

    @property
    def input_snapshot_hash_match(self) -> bool:
        return self.stored.input_snapshot_hash == self.recomputed.input_snapshot_hash

    @property
    def analytical_payload_hash_match(self) -> bool:
        return self.stored.analytical_payload_hash == self.recomputed.analytical_payload_hash

    @property
    def observation_ids_match(self) -> bool:
        return sorted(self.stored.observation_ids) == sorted(self.recomputed.observation_ids)

    @property
    def full_match(self) -> bool:
        return (
            self.input_snapshot_hash_match
            and self.calculation_match
            and self.analytical_payload_hash_match
            and self.observation_ids_match
        )


def verify_stored_run_replay(
    conn: psycopg.Connection,
    run_id: str,
    *,
    stored: ResearchRun | None = None,
) -> RunReplayVerification:
    persisted = stored if stored is not None else load_research_run(conn, run_id)
    recomputed = recompute_stored_run(conn, run_id)
    return RunReplayVerification(stored=persisted, recomputed=recomputed)


def recompute_stored_run(conn: psycopg.Connection, run_id: str) -> ResearchRun:
    """Re-run analysis using observation IDs recorded on the immutable run."""
    stored = load_research_run(conn, run_id)
    observation_ids = load_run_observation_ids(conn, run_id)
    observations = load_observations_by_ids(conn, observation_ids)
    store = InMemoryObservationStore()
    for row in observations:
        store.append(row)

    registry = default_method_registry()
    if (
        stored.method_id == BRY_BOSCHAN_SPENCER15_VARIANT
        and stored.implementation_hash == legacy_variant_implementation_hash()
    ):
        registry.register(BryBoschanSpencer15Method(payload_revision="legacy"))
    method_config = replay_configuration(registry, stored)
    if not observation_ids:
        raise ValueError(f"stored run {stored.run_id} has no frozen observation evidence")
    request = ResearchExecutionRequest(
        source_id=stored.source_id,
        dataset_id=stored.dataset_id,
        decision_at=stored.decision_at,
        analysis_mode=stored.analysis_mode,
        evaluation_period=stored.evaluation_period,
        method_id=stored.method_id,
        method_config=method_config,
        collect=False,
        primary_adapter_id=stored.adapter_ids[0] if stored.adapter_ids else None,
        replay_frozen_observations=True,
    )
    recomputed = execute_research_run(
        request,
        store=store,
        rights_records=load_source_rights(),
        method_registry=registry,
        executed_at=stored.executed_at,
        run_id=stored.run_id,
    )
    return recomputed.model_copy(
        update={
            "ingest_notes": list(stored.ingest_notes),
            "adapter_ids": list(stored.adapter_ids),
        },
    )


# Absolute gap allowed when two scientific figures are called the same.
# A later diagnostic field, or a hash of the implementation, is not a figure.
SCIENTIFIC_ABSOLUTE_TOLERANCE = 1e-8
PARAMETER_FIELDS = (
    "loadings_ip_income_sales_payroll",
    "factor_ar",
    "idiosyncratic_ar",
    "idiosyncratic_scale",
)
ReplayOutcome = Literal["replayable", "executable-but-historically-unmatched", "blocked"]


@dataclass(frozen=True, slots=True)
class HistoricalReplay:
    """One stored row, judged from frozen observations and its own specification."""

    run_id: str
    outcome: ReplayOutcome
    missing_field: str | None
    tolerance: float
    differences: tuple[str, ...]
    notes: tuple[str, ...]


def replay_configuration(
    registry: MethodRegistry,
    stored: ResearchRun,
) -> dict[str, object]:
    """Resolve the specification the stored run used.

    A stored config hash that is not the current method hash is recorded by
    the caller. It does not stop the scientific comparison, and it is not
    rewritten on the stored row.
    """
    payload = stored_specification(stored, reproduction_config(stored.config_id))
    registry.get(stored.method_id).parse_config(payload)
    return payload


def stored_specification(
    stored: ResearchRun,
    payload: dict[str, object],
) -> dict[str, object]:
    """Map a stored config id onto the calculation that row actually ran.

    The preserved Stock–Watson row is a calculation with its stored parameter
    vector. It is not a refit, and the vector is not written back as a new hash.
    """
    mapped = dict(payload)
    if stored.method_id != SPECIFICATION_ID or stored.config_id != ACCEPTED_CONFIG["config_id"]:
        return mapped
    parameters = _parameters_from_calculation(stored.calculation)
    if parameters is None:
        return mapped
    mapped["execution_mode"] = "calculate"
    mapped["accepted_parameters"] = parameters
    return mapped


def _parameters_from_calculation(
    calculation: dict[str, object] | None,
) -> dict[str, object] | None:
    if calculation is None or any(key not in calculation for key in PARAMETER_FIELDS):
        return None
    parameters = {key: calculation[key] for key in PARAMETER_FIELDS}
    moments = calculation.get("moments")
    if isinstance(moments, dict):
        parameters["moments"] = moments
    return parameters


def classify_historical_replay(
    conn: psycopg.Connection,
    run_id: str,
) -> HistoricalReplay:
    """Recompute one stored row and classify the scientific comparison.

    The stored hashes and the stored calculation are not updated.
    """
    stored = load_research_run(conn, run_id)
    observation_ids = load_run_observation_ids(conn, run_id)
    if not observation_ids:
        return _blocked(stored.run_id, "observation_ids")
    observations = load_observations_by_ids(conn, observation_ids)
    if len(observations) != len(set(observation_ids)):
        return _blocked(stored.run_id, "observation_ids")
    registry = default_method_registry()
    try:
        method = registry.get(stored.method_id)
    except MethodRegistryError:
        return _blocked(stored.run_id, "method_id")
    try:
        reproduction_config(stored.config_id)
    except ValueError as exc:
        if "unknown config_id" not in str(exc):
            raise
        return _blocked(stored.run_id, "config_id")
    present = {row.dataset_id for row in observations}
    missing = tuple(
        dataset_id for dataset_id in method.required_dataset_ids() if dataset_id not in present
    )
    if missing:
        return _blocked(stored.run_id, "observation_ids: " + ", ".join(missing))
    recomputed = recompute_stored_run(conn, run_id)
    differences, notes = scientific_field_report(stored.calculation, recomputed.calculation)
    notes = list(notes)
    if stored.config_hash != recomputed.config_hash:
        notes.append(
            "stored config hash differs from the current method hash and was not rewritten"
        )
    if stored.implementation_hash != recomputed.implementation_hash:
        notes.append("implementation hash differs and was not rewritten")
    if stored.input_snapshot_hash != recomputed.input_snapshot_hash:
        notes.append("input snapshot hash differs and was not rewritten")
    if stored.analytical_payload_hash != recomputed.analytical_payload_hash:
        notes.append("analytical payload hash differs and was not rewritten")
    if differences:
        shown = differences[:12]
        if len(differences) > len(shown):
            notes.append(f"{len(differences)} scientific fields differ")
        return HistoricalReplay(
            run_id=stored.run_id,
            outcome="executable-but-historically-unmatched",
            missing_field=None,
            tolerance=SCIENTIFIC_ABSOLUTE_TOLERANCE,
            differences=shown,
            notes=tuple(notes),
        )
    return HistoricalReplay(
        run_id=stored.run_id,
        outcome="replayable",
        missing_field=None,
        tolerance=SCIENTIFIC_ABSOLUTE_TOLERANCE,
        differences=(),
        notes=tuple(notes),
    )


def scientific_field_report(
    stored: dict[str, object] | None,
    recomputed: dict[str, object] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Compare scientific figures. Extra fields are notes, not a numerical pass.

    Shared numbers match within ``SCIENTIFIC_ABSOLUTE_TOLERANCE``. A number that
    the stored row has and the recomputation omits is a difference. A field that
    exists only on the recomputation is explained beside the comparison.
    """
    left = normalize_calculation_payload(stored)
    right = normalize_calculation_payload(recomputed)
    differences: list[str] = []
    notes: list[str] = []
    if left is None and right is None:
        return (), ()
    if left is None or right is None:
        return ("calculation",), ()
    _compare_values(left, right, "", differences, notes)
    return tuple(differences), tuple(notes)


def _compare_values(
    stored: object,
    recomputed: object,
    path: str,
    differences: list[str],
    notes: list[str],
) -> None:
    if isinstance(stored, dict) and isinstance(recomputed, dict):
        for key in sorted(set(stored) & set(recomputed)):
            child = f"{path}.{key}" if path else key
            _compare_values(stored[key], recomputed[key], child, differences, notes)
        for key in sorted(set(recomputed) - set(stored)):
            child = f"{path}.{key}" if path else key
            notes.append(f"extra field {child}")
        for key in sorted(set(stored) - set(recomputed)):
            child = f"{path}.{key}" if path else key
            if _contains_number(stored[key]):
                differences.append(child)
            else:
                notes.append(f"stored field {child} was not reproduced")
        return
    if isinstance(stored, list) and isinstance(recomputed, list):
        if len(stored) != len(recomputed):
            differences.append(path or "value")
            return
        for index, (left, right) in enumerate(zip(stored, recomputed, strict=True)):
            _compare_values(left, right, f"{path}[{index}]", differences, notes)
        return
    if _numbers_within_tolerance(stored, recomputed):
        return
    if stored != recomputed:
        differences.append(path or "value")


def _numbers_within_tolerance(stored: object, recomputed: object) -> bool:
    if isinstance(stored, bool) or isinstance(recomputed, bool):
        return False
    if not isinstance(stored, (int, float)) or not isinstance(recomputed, (int, float)):
        return False
    if not math.isfinite(float(stored)) or not math.isfinite(float(recomputed)):
        return False
    return abs(float(stored) - float(recomputed)) <= SCIENTIFIC_ABSOLUTE_TOLERANCE


def _contains_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, dict):
        return any(_contains_number(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_number(item) for item in value)
    return False


def _blocked(run_id: str, missing_field: str) -> HistoricalReplay:
    return HistoricalReplay(
        run_id=run_id,
        outcome="blocked",
        missing_field=missing_field,
        tolerance=SCIENTIFIC_ABSOLUTE_TOLERANCE,
        differences=(),
        notes=(),
    )


def reproduction_config(config_id: str) -> dict[str, object]:
    """Return the payload the method's parser already accepts for this config id."""
    if config_id == SAHM_PUBLISHED.config_id:
        return SAHM_PUBLISHED.model_dump(mode="json")
    if config_id == SAHM_SENSITIVITY.config_id:
        return SAHM_SENSITIVITY.model_dump(mode="json")
    published_panels = (
        MACRO_CONDITIONS_PUBLISHED,
        SLOOS_CIL_PUBLISHED,
        CENSUS_ADV_ORDERS_PUBLISHED,
        BRY_BOSCHAN_SPENCER15_PUBLISHED,
        HARDING_PAGAN_CHARACTERISTICS_PUBLISHED,
        HAMILTON_MONTHLY_PUBLISHED,
        BAI_PERRON_MEAN_SHIFTS_PUBLISHED,
        AUTOREGRESSIVE_BENCHMARK_PUBLISHED,
        LEAD_LAG_PUBLISHED,
        RESTRICTED_COINCIDENT_DIFFUSION_PUBLISHED,
        ACCEPTED_CONFIG,
        REFIT_CONFIG,
        MULTISTART_CONFIG,
        ENGLE_GRANGER_COINTEGRATION_PUBLISHED,
        CUSUM_RECURSIVE_RESIDUALS_PUBLISHED,
        CPI_U_INFLATION_AUTREGRESSION_PUBLISHED,
        EX_POST_REAL_FEDERAL_FUNDS_PUBLISHED,
        INFLATION_AUTOREGRESSION_PUBLISHED,
        EX_POST_REAL_FUNDS_RATE_PUBLISHED,
        IP_GROWTH_CUSUM_PUBLISHED,
        ESTRELLA_MISHKIN_PUBLISHED,
        CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT_PUBLISHED,
    )
    for panel in published_panels:
        if config_id == panel["config_id"]:
            return dict(panel)
    raise ValueError(f"unknown config_id for reproduction: {config_id}")
