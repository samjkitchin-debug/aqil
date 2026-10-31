"""Plug-in and plug-out for one source and one method.

Fixtures only. The live database named postgres is not opened.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import psycopg
import pytest
from pydantic import BaseModel

from aqil_research.adapters.source_registry import (
    FunctionSourceConnector,
    ParsedSource,
    SourceIdentity,
    SourceRegistry,
)
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult, bind_dependency
from aqil_research.methods.registry import MethodRegistry, default_method_registry
from aqil_research.persistence.observation_store import PostgresObservationStore
from aqil_research.pipeline.execute_method import MethodExecutionRefused, execute_registered_method
from aqil_research.reads.v1 import RESEARCH_READ_VERSION, read_methodology_result
from aqil_research.workflow.refresh import default_source_registry
from db_guard import open_isolated_test_database

pytestmark = pytest.mark.integration

WHEN = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
TOY_METHOD = "TEST_ONLY_LEVEL"


class ToyConfig(BaseModel):
    config_id: str = "test-only-level"


class ToyMethod:
    method_id = TOY_METHOD
    method_version = "0"

    def implementation_hash(self) -> str:
        return "test-only-level"

    def required_dataset_ids(self) -> tuple[str, ...]:
        return ("bls.ln.LNS14000000",)

    def dependency(self):
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history="one stored month",
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return {"config_id": "test-only-level"}

    def parse_config(self, payload: dict[str, object]) -> ToyConfig:
        return ToyConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        return "test-only-level"

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        del config
        observation = next(
            row
            for row in context.primary_series().values()
            if row.observation_id.startswith("plugin-")
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation={"level": observation.raw_value, "publication_allowed": False},
            observation_ids=(observation.observation_id,),
            assumptions=(),
            limitations=("publication_allowed is false.",),
            missing_reason=None,
            statistical_interpretation="A test level was stored.",
            causal_hypothesis="No causal mechanism is established.",
            investment_implication="no_action",
            narrative="Test level. publication_allowed is false.",
        )


class SimulatedSource:
    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    def identity(self) -> SourceIdentity:
        return SourceIdentity(
            source_id="test_only_source",
            cadence="monthly",
            enabled=self._enabled,
            rights_record_id="test_only_source",
            dataset_ids=("test.only.series",),
            data_frequency="monthly",
        )

    def fetch(self, now: datetime) -> object:
        del now
        return self._observation()

    def parse(self, fetched: object) -> ParsedSource:
        if isinstance(fetched, EconomicObservation):
            return ParsedSource((fetched,))
        return ParsedSource(())

    def validate(self, parsed: ParsedSource) -> ParsedSource:
        for observation in parsed.observations:
            if observation.unit != "level":
                raise ValueError(observation.unit)
        return parsed

    def refresh(self, now: datetime) -> object:
        del now
        return None

    def _observation(self) -> EconomicObservation:
        return EconomicObservation(
            observation_id="test-only-observation",
            dataset_id="test.only.series",
            provider_id="test",
            source_id="test_only_source",
            rights_record_id="test_only_source",
            period_start=date(2026, 1, 1),
            frequency=Frequency.MONTHLY,
            geography="US",
            unit="level",
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
            raw_value="1",
            quality_status=QualityStatus.OBSERVED,
            series_provenance=SeriesProvenance.LATEST_REVISED,
            provider_vintage_date=date(2026, 1, 1),
            availability_precision=AvailabilityPrecision.UNKNOWN,
            retrieved_at=WHEN,
            first_seen_at=WHEN,
            adapter_version="test",
        )


def test_a_simulated_source_can_be_registered_validated_and_disabled() -> None:
    registry = SourceRegistry()
    simulated = SimulatedSource()
    registry.register(simulated)
    validated = simulated.validate(simulated.parse(simulated.fetch(WHEN)))
    assert validated.observations[0].schema_version == "1.0"
    assert validated.observations[0].unit == "level"
    registry.disable("test_only_source")
    assert "test_only_source" not in registry.source_ids(enabled_only=True)
    assert "test_only_source" not in default_source_registry().source_ids()
    disabled = FunctionSourceConnector(
        source_id="test_only_source",
        action=lambda now: None,
        cadence="monthly",
        data_frequency="monthly",
        rights_record_id="test_only_source",
        enabled=False,
    )
    registry.register(disabled)
    assert "test_only_source" not in registry.source_ids(enabled_only=True)


def test_a_simulated_method_is_executed_read_and_then_disabled(require_db: str) -> None:
    registry = MethodRegistry()
    registry.register(ToyMethod())
    with psycopg.connect(require_db) as conn:
        _insert_unemployment(conn)
        run = execute_registered_method(conn, TOY_METHOD, registry=registry, executed_at=WHEN)
        assert run.publication_allowed is False
        read = read_methodology_result(conn, run.run_id)
        assert read is not None
        assert read["version"] == RESEARCH_READ_VERSION
        assert read["method_id"] == TOY_METHOD
        assert read["publication_allowed"] is False
        assert read["calculation"]["level"] == "4.2"
        registry.disable(TOY_METHOD)
        with pytest.raises(MethodExecutionRefused):
            execute_registered_method(conn, TOY_METHOD, registry=registry, executed_at=WHEN)
        conn.rollback()
    production = {method.method_id for method in default_method_registry().registered()}
    assert TOY_METHOD not in production
    assert TOY_METHOD not in {method.method_id for method in default_method_registry().enabled()}


@pytest.fixture(scope="module")
def require_db() -> str:
    return open_isolated_test_database()


def _insert_unemployment(conn: psycopg.Connection) -> None:
    retrieval_id = uuid4()
    dataset_id = "bls.ln.LNS14000000"
    source_id = "bls_cps_unemployment_rate"
    conn.execute(
        """
        insert into research.source_retrievals (
          retrieval_id, source_id, dataset_id, rights_record_id, provider_id,
          adapter_id, adapter_version, retrieved_at, collection_mode,
          endpoint_host, request_series_ids, attempt_count, http_status,
          provider_status, response_byte_count, rights_decision_snapshot,
          ingest_notes
        ) values (
          %s, %s, %s, %s, 'test', 'plugin', '0', %s, 'fixture',
          '127.0.0.1', %s, 1, 200, 'ok', 1, '{}'::jsonb, '{}'
        )
        """,
        (retrieval_id, source_id, dataset_id, source_id, WHEN, [dataset_id]),
    )
    PostgresObservationStore(conn, retrieval_id=retrieval_id).append_many(
        (
            EconomicObservation(
                observation_id="plugin-unemployment-2026-09",
                dataset_id=dataset_id,
                provider_id="test",
                source_id=source_id,
                rights_record_id=source_id,
                period_start=date(2026, 9, 1),
                frequency=Frequency.MONTHLY,
                geography="US",
                unit="percent",
                seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
                raw_value="4.2",
                quality_status=QualityStatus.OBSERVED,
                series_provenance=SeriesProvenance.LATEST_REVISED,
                provider_vintage_date=date(2026, 9, 1),
                availability_precision=AvailabilityPrecision.UNKNOWN,
                retrieved_at=WHEN,
                first_seen_at=WHEN,
                adapter_version="test",
            ),
        )
    )
