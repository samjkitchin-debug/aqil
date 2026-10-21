"""M6 analytical method tests on synthetic and fixture-backed stores."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from aqil_research.adapters.census_adv_orders.adapter import (
    CensusAdvOrdersAdapter,
    CensusAdvOrdersAdapterConfig,
)
from aqil_research.adapters.fed_sloos.adapter import FedSloosAdapter, FedSloosAdapterConfig
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.census_adv_orders import CensusAdvOrdersMethod
from aqil_research.methods.configs import MACRO_CONDITIONS_PUBLISHED
from aqil_research.methods.macro_conditions import MacroConditionsMethod
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.sloos_cil import SloosCilConfig, SloosCilMethod
from aqil_research.pipeline.ingestion import ingest_from_adapter
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURES = Path(__file__).parent / "fixtures"
BLS_FIXTURE = FIXTURES / "bls" / "api_lns14000000_success.json"
RETRIEVED = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)


def _load_macro_store() -> InMemoryObservationStore:
    from aqil_research.adapters.bls.adapter import BlsAdapterConfig, BlsUnemploymentAdapter

    rights = load_source_rights()
    store = InMemoryObservationStore()
    bls = BlsUnemploymentAdapter(
        config=BlsAdapterConfig(2022, 2025, live=False, fixture_path=BLS_FIXTURE),
        retrieved_at=RETRIEVED,
    )
    sloos = FedSloosAdapter(
        config=FedSloosAdapterConfig(
            live=False,
            fixture_path=FIXTURES / "fed_sloos" / "sublpdcils_n_q_bundle.json",
        ),
        retrieved_at=RETRIEVED,
    )
    census = CensusAdvOrdersAdapter(
        config=CensusAdvOrdersAdapterConfig(
            live=False,
            fixture_path=FIXTURES / "census" / "mdm_no_adv_vintages.json",
        ),
        retrieved_at=RETRIEVED,
    )
    for adapter in (bls, sloos, census):
        record = next(r for r in rights if r.source_id == adapter.identity.source_id)
        ingest_from_adapter(store, adapter, record, optional=False)
    return store


def test_census_mom_distinction() -> None:
    store = _load_macro_store()
    by_period = store.as_of(
        "census.m3.adv.MDM.NO",
        RETRIEVED,
        AnalysisMode.LATEST_REVISED,
    )
    method = CensusAdvOrdersMethod()
    context = MethodContext(
        inputs_by_dataset={"census.m3.adv.MDM.NO": by_period},
        evaluation_period=date(2024, 8, 1),
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id="census.m3.adv.MDM.NO",
        all_vintages_by_dataset={
            "census.m3.adv.MDM.NO": tuple(
                obs for obs in store.all_observations() if obs.dataset_id == "census.m3.adv.MDM.NO"
            ),
        },
    )
    result = method.run(
        context,
        method.parse_config(
            {"config_id": "test", "label": "test"},
        ),
    )
    assert result.sufficiency == "sufficient"
    calc = result.calculation or {}
    assert calc["initial_estimate_to_initial_estimate_pct_change"] == "4.00"
    assert calc["official_month_on_month_pct_change"] == "1.96"


def test_one_census_vintage_is_not_a_revision_comparison() -> None:
    store = _load_macro_store()
    rows = tuple(
        obs
        for obs in store.all_observations()
        if obs.dataset_id == "census.m3.adv.MDM.NO"
        and obs.provider_vintage_date.isoformat() == "2024-09-25"
    )
    method = CensusAdvOrdersMethod()
    context = MethodContext(
        inputs_by_dataset={"census.m3.adv.MDM.NO": {row.period_start: row for row in rows}},
        evaluation_period=date(2024, 8, 1),
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id="census.m3.adv.MDM.NO",
        all_vintages_by_dataset={"census.m3.adv.MDM.NO": rows},
    )
    result = method.run(context, method.parse_config({"config_id": "test", "label": "test"}))
    assert result.sufficiency == "insufficient"
    assert result.missing_reason is not None
    assert "one stored vintage" in result.missing_reason


def test_sloos_zero_is_net_balance() -> None:
    store = _load_macro_store()
    by_period = store.as_of(
        "fed.sloos.SUBLPDCILS_N.Q",
        RETRIEVED,
        AnalysisMode.LATEST_REVISED,
    )
    method = SloosCilMethod()
    context = MethodContext(
        inputs_by_dataset={"fed.sloos.SUBLPDCILS_N.Q": by_period},
        evaluation_period=date(2024, 10, 1),
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id="fed.sloos.SUBLPDCILS_N.Q",
    )
    result = method.run(
        context,
        SloosCilConfig(config_id="test", label="test"),
    )
    assert result.calculation is not None
    assert result.calculation["net_tightening_share_percent"] == "0.0"
    assert result.calculation["zero_means_net_balance_not_unanimous_unchanged"] is True


def test_macro_panel_blocks_forward_spread() -> None:
    store = _load_macro_store()
    inputs = {
        "bls.ln.LNS14000000": store.as_of(
            "bls.ln.LNS14000000",
            RETRIEVED,
            AnalysisMode.LATEST_REVISED,
        ),
        "fed.sloos.SUBLPDCILS_N.Q": store.as_of(
            "fed.sloos.SUBLPDCILS_N.Q",
            RETRIEVED,
            AnalysisMode.LATEST_REVISED,
        ),
        "census.m3.adv.MDM.NO": store.as_of(
            "census.m3.adv.MDM.NO",
            RETRIEVED,
            AnalysisMode.LATEST_REVISED,
        ),
    }
    method = MacroConditionsMethod()
    context = MethodContext(
        inputs_by_dataset=inputs,
        evaluation_period=date(2024, 12, 1),
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id="bls.ln.LNS14000000",
        all_vintages_by_dataset={
            "census.m3.adv.MDM.NO": tuple(
                obs for obs in store.all_observations() if obs.dataset_id == "census.m3.adv.MDM.NO"
            ),
        },
    )
    result = method.run(context, method.parse_config(MACRO_CONDITIONS_PUBLISHED))
    assert result.sufficiency == "sufficient"
    blocked = (result.calculation or {}).get("near_term_forward_spread", {})
    assert blocked.get("status") == "blocked"
