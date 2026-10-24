import csv
import inspect
from pathlib import Path

import pytest

from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    REGISTER_COLUMNS,
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsOperation,
    SourceRightsError,
    SourceRightsRecord,
    load_source_rights,
    operation_allowed,
    source_usable,
)


def _write_register(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTER_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(**overrides: str) -> dict[str, str]:
    base = {
        "source_id": "example_source",
        "dataset_id": "example.dataset",
        "provider_name": "Example provider",
        "publication_name": "Example publication",
        "geography": "US",
        "series_or_dataset_code": "EXAMPLE",
        "category": "test",
        "access_description": "Synthetic row for the rights gate.",
        "access_url": "https://example.com/access",
        "terms_url": "https://example.com/terms",
        "evidence_urls": "https://example.com/terms|https://example.com/access",
        "auth_requirement": "None",
        "automated_access": "permitted",
        "internal_computation": "permitted",
        "raw_data_retention": "unknown",
        "historical_archiving": "unknown",
        "redistribution": "prohibited",
        "commercial_publication": "unknown",
        "ai_processing": "unknown",
        "ai_model_training": "unknown",
        "attribution": "required",
        "m1_role": "unresolved",
        "operational_status": "enabled",
        "conditions": "Synthetic conditions.",
        "revision_behaviour": "Not a real series.",
        "unresolved_questions": "Synthetic uncertainty.",
        "evidence_note": "Synthetic evidence for the loader test.",
        "assessed_on": "2026-10-17",
    }
    base.update(overrides)
    return base


def test_register_loader_has_no_provider_client() -> None:
    import aqil_research.sources.rights as rights

    source = inspect.getsource(rights)
    assert "httpx" not in source
    assert "urlopen" not in source


def test_canonical_register_links_evidence_and_separates_datasets() -> None:
    records = load_source_rights()
    by_dataset = {record.dataset_id: record for record in records}

    assert set(by_dataset) == {
        "bls.ln.LNS14000000",
        "bls.empsit.archive",
        "fred.alfred.UNRATE",
        "treasury.xml.daily_treasury_yield_curve",
        "fiscal.avg_interest_rates",
        "board.h15.treasury_yields",
        "fed.sloos.SUBLPDCILS_N.Q",
        "census.m3.adv.MDM.NO",
        "board.yield.ntfs",
        "forward.fomc.schedule",
        "forward.bls.empsit.schedule",
        "forward.etf.vwra.holdings",
        "forward.etf.ishares.holdings",
        "forward.bls.selected_releases.schedule",
        "forward.bea.news.schedule",
        "forward.sec.edgar.completed_filings",
        "forward.company_ir.watchlist",
        "fed.press.monetary",
        "bls.cpi.archive",
        "ecb.press.monetary",
        "bls.cu.CUSR0000SA0",
        "bls.ce.CES0000000001",
        "bls.jt.JTS000000000000000JOL",
        "fed.g17.IP.B50001.S",
        "fed.h8.B1001NCBA",
        "fed.h15.RIFSPFF_N.M",
        "fed.h15.RIFLGFCY10_N.M",
        "ecb.icp.M.U2.Y.000000.3.INX",
        "govinfo.federal_register.notices",
        "ecb.icp.M.U2.Y.XEF000.3.INX",
        "ecb.fm.D.U2.EUR.4F.KR.DFR.LEV",
        "eurostat.namq_10_gdp.Q.CLV_I15.SCA.B1GQ.EA21",
        "eurostat.une_rt_m.M.SA.TOTAL.PC_ACT.T.EA21",
        "eurostat.sts_inpr_m.M.PRD.B-D.SCA.I21.EA21",
        "eurostat.sts_trtu_m.M.VOL_SLS.G47.SCA.I21.EA21",
        "ecb.bls.Q.U2.ALL.O.E.Z.B3.ST.S.WFNET",
        "ecb.bsi.M.U2.N.A.A20.A.1.U6.2240.Z01.E",
        "meti.iip.b2020.production.sa.m.1000000000",
        "stat.cpi.2025base.JP.0001.all_items.monthly.calendar.nsa.reference_3dp",
        "cao.mo.private_ex_volatile.nominal.million_yen.sa.monthly.calendar",
        "sbj.cpi.2025.all_items.m",
        "sbj.cpi.2025.all_items_less_fresh_food.m",
        "boj.FM01.not_bound",
        "boj.fm08.foreign_exchange",
        "nbs.national_data",
        "nbs_cpi.not_bound",
        "nbs_industrial_production.not_bound",
        "pboc.statistics",
        "pboc_policy_rate.not_bound",
        "pboc_exchange_rate.not_bound",
        "bis.ws_gli.Q.USD.3P.N.A.I.B.USD",
        "oecd.stes.DF_CLI.G20.M.LI.IX._Z.AA.IX._Z.H",
        "ons.mm23.D7BT",
        "boe.iudbedr",
        "dosm.ipi.abs",
    }
    for record in records:
        assert record.terms_url in record.evidence_urls
        assert record.evidence_note
        if record.dataset_id.startswith("forward."):
            assert record.assessed_on.isoformat() == "2026-10-18"
        elif record.dataset_id == "board.yield.ntfs":
            assert record.assessed_on.isoformat() == "2026-10-18"
        elif record.dataset_id in {
            "fed.sloos.SUBLPDCILS_N.Q",
            "census.m3.adv.MDM.NO",
            "fed.press.monetary",
            "bls.cpi.archive",
            "ecb.press.monetary",
            "bls.cu.CUSR0000SA0",
            "bls.ce.CES0000000001",
            "bls.jt.JTS000000000000000JOL",
            "fed.g17.IP.B50001.S",
            "fed.h8.B1001NCBA",
            "fed.h15.RIFSPFF_N.M",
            "fed.h15.RIFLGFCY10_N.M",
            "ecb.icp.M.U2.Y.000000.3.INX",
        }:
            assert record.assessed_on.isoformat() == "2026-10-22"
        elif record.dataset_id in {
            "ecb.icp.M.U2.Y.XEF000.3.INX",
            "ecb.fm.D.U2.EUR.4F.KR.DFR.LEV",
            "eurostat.namq_10_gdp.Q.CLV_I15.SCA.B1GQ.EA21",
            "eurostat.une_rt_m.M.SA.TOTAL.PC_ACT.T.EA21",
            "eurostat.sts_inpr_m.M.PRD.B-D.SCA.I21.EA21",
            "eurostat.sts_trtu_m.M.VOL_SLS.G47.SCA.I21.EA21",
            "ecb.bls.Q.U2.ALL.O.E.Z.B3.ST.S.WFNET",
            "ecb.bsi.M.U2.N.A.A20.A.1.U6.2240.Z01.E",
            "meti.iip.b2020.production.sa.m.1000000000",
            "stat.cpi.2025base.JP.0001.all_items.monthly.calendar.nsa.reference_3dp",
            "cao.mo.private_ex_volatile.nominal.million_yen.sa.monthly.calendar",
            "sbj.cpi.2025.all_items.m",
            "sbj.cpi.2025.all_items_less_fresh_food.m",
            "boj.FM01.not_bound",
            "boj.fm08.foreign_exchange",
            "nbs.national_data",
            "nbs_cpi.not_bound",
            "nbs_industrial_production.not_bound",
            "pboc.statistics",
            "pboc_policy_rate.not_bound",
            "pboc_exchange_rate.not_bound",
            "bis.ws_gli.Q.USD.3P.N.A.I.B.USD",
            "oecd.stes.DF_CLI.G20.M.LI.IX._Z.AA.IX._Z.H",
            "ons.mm23.D7BT",
            "boe.iudbedr",
            "dosm.ipi.abs",
        }:
            assert record.assessed_on.isoformat() == "2026-10-24"
        elif record.dataset_id == "govinfo.federal_register.notices":
            assert record.assessed_on.isoformat() == "2026-10-24"
        else:
            assert record.assessed_on.isoformat() == "2026-10-17"

    unemployment = by_dataset["bls.ln.LNS14000000"]
    assert unemployment.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert unemployment.series_or_dataset_code == "LNS14000000"
    assert source_usable(unemployment, RightsOperation.INTERNAL_COMPUTATION)
    assert source_usable(unemployment, RightsOperation.COMMERCIAL_PUBLICATION)
    assert not source_usable(unemployment, RightsOperation.AI_MODEL_TRAINING)
    assert not operation_allowed(unemployment, RightsOperation.AI_PROCESSING)

    fred = by_dataset["fred.alfred.UNRATE"]
    assert fred.m1_role == M1Role.INELIGIBLE
    assert fred.operational_status == OperationalStatus.ENABLED
    assert not source_usable(fred, RightsOperation.HISTORICAL_ARCHIVING)
    assert not source_usable(fred, RightsOperation.RAW_DATA_RETENTION)
    assert not source_usable(fred, RightsOperation.AI_PROCESSING)
    assert not source_usable(fred, RightsOperation.AI_MODEL_TRAINING)
    assert not operation_allowed(fred, RightsOperation.COMMERCIAL_PUBLICATION)

    treasury = by_dataset["treasury.xml.daily_treasury_yield_curve"]
    fiscal = by_dataset["fiscal.avg_interest_rates"]
    board = by_dataset["board.h15.treasury_yields"]
    assert treasury.dataset_id != fiscal.dataset_id
    assert treasury.dataset_id != board.dataset_id
    assert fiscal.m1_role == M1Role.NOT_A_MODEL_INPUT
    assert source_usable(fiscal, RightsOperation.COMMERCIAL_PUBLICATION)
    assert not source_usable(treasury, RightsOperation.COMMERCIAL_PUBLICATION)
    assert not source_usable(treasury, RightsOperation.AUTOMATED_ACCESS)
    assert board.m1_role == M1Role.YIELD_CURVE_CANDIDATE
    assert board.series_or_dataset_code == "unconfirmed"
    assert source_usable(board, RightsOperation.REDISTRIBUTION)
    assert not source_usable(board, RightsOperation.AI_MODEL_TRAINING)

    first_live = {
        record.dataset_id for record in records if record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    }
    assert first_live == {
        "bls.ln.LNS14000000",
        "fed.sloos.SUBLPDCILS_N.Q",
        "census.m3.adv.MDM.NO",
        "bls.cu.CUSR0000SA0",
        "bls.ce.CES0000000001",
        "bls.jt.JTS000000000000000JOL",
        "fed.g17.IP.B50001.S",
        "fed.h8.B1001NCBA",
        "fed.h15.RIFSPFF_N.M",
        "fed.h15.RIFLGFCY10_N.M",
        "ecb.icp.M.U2.Y.000000.3.INX",
        "ecb.icp.M.U2.Y.XEF000.3.INX",
        "ecb.fm.D.U2.EUR.4F.KR.DFR.LEV",
        "eurostat.namq_10_gdp.Q.CLV_I15.SCA.B1GQ.EA21",
        "eurostat.une_rt_m.M.SA.TOTAL.PC_ACT.T.EA21",
        "eurostat.sts_inpr_m.M.PRD.B-D.SCA.I21.EA21",
        "eurostat.sts_trtu_m.M.VOL_SLS.G47.SCA.I21.EA21",
        "stat.cpi.2025base.JP.0001.all_items.monthly.calendar.nsa.reference_3dp",
        "cao.mo.private_ex_volatile.nominal.million_yen.sa.monthly.calendar",
        "meti.iip.b2020.production.sa.m.1000000000",
        "bis.ws_gli.Q.USD.3P.N.A.I.B.USD",
        "ons.mm23.D7BT",
        "boe.iudbedr",
        "dosm.ipi.abs",
    }
    assert all(operation_allowed(unemployment, operation) for operation in FIRST_LIVE_OPERATIONS)
    assert unemployment.attribution == AttributionRequirement.REQUIRED

    govinfo = by_dataset["govinfo.federal_register.notices"]
    assert govinfo.source_id == "govinfo_federal_register"
    assert govinfo.m1_role == M1Role.UNRESOLVED
    assert govinfo.attribution == AttributionRequirement.REQUIRED
    assert govinfo.operational_status == OperationalStatus.ENABLED
    assert not source_usable(govinfo, RightsOperation.AUTOMATED_ACCESS)
    assert source_usable(govinfo, RightsOperation.RAW_DATA_RETENTION)
    assert source_usable(govinfo, RightsOperation.REDISTRIBUTION)
    assert not operation_allowed(govinfo, RightsOperation.AI_PROCESSING)
    assert not operation_allowed(govinfo, RightsOperation.AI_MODEL_TRAINING)
    assert govinfo.m1_role != M1Role.FIRST_LIVE_PROVIDER


def test_unknown_or_prohibited_rights_block_only_that_operation() -> None:
    record = SourceRightsRecord.model_validate(
        {**_row(), "evidence_urls": ("https://example.com/terms", "https://example.com/access")},
    )
    assert source_usable(record, RightsOperation.INTERNAL_COMPUTATION)
    assert not source_usable(record, RightsOperation.RAW_DATA_RETENTION)
    assert not source_usable(record, RightsOperation.REDISTRIBUTION)
    assert not operation_allowed(record, RightsOperation.COMMERCIAL_PUBLICATION)


def test_disabled_source_blocks_use_and_leaves_another_source_usable(tmp_path: Path) -> None:
    _write_register(
        tmp_path / "rights.csv",
        [
            _row(source_id="kept", dataset_id="example.kept", raw_data_retention="permitted"),
            _row(
                source_id="paused",
                dataset_id="example.paused",
                operational_status="disabled",
                raw_data_retention="permitted",
                internal_computation="permitted",
            ),
        ],
    )
    records = {record.source_id: record for record in load_source_rights(tmp_path / "rights.csv")}
    assert source_usable(records["kept"], RightsOperation.INTERNAL_COMPUTATION)
    assert records["paused"].operational_status == OperationalStatus.DISABLED
    assert operation_allowed(records["paused"], RightsOperation.INTERNAL_COMPUTATION)
    assert not source_usable(records["paused"], RightsOperation.INTERNAL_COMPUTATION)


def test_future_provider_loads_without_a_loader_change(tmp_path: Path) -> None:
    _write_register(
        tmp_path / "rights.csv",
        [_row(source_id="future_provider_not_in_code", dataset_id="future.dataset")],
    )
    records = load_source_rights(tmp_path / "rights.csv")
    assert records[0].source_id == "future_provider_not_in_code"
    assert not source_usable(records[0], RightsOperation.HISTORICAL_ARCHIVING)


def test_missing_evidence_url_is_rejected(tmp_path: Path) -> None:
    _write_register(tmp_path / "rights.csv", [_row(evidence_urls="")])
    with pytest.raises(SourceRightsError, match="evidence"):
        load_source_rights(tmp_path / "rights.csv")


def test_first_live_role_requires_cleared_operations(tmp_path: Path) -> None:
    _write_register(
        tmp_path / "rights.csv",
        [_row(m1_role="first_live_provider", raw_data_retention="unknown")],
    )
    with pytest.raises(SourceRightsError, match="not cleared"):
        load_source_rights(tmp_path / "rights.csv")
