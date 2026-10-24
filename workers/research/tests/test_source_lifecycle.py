"""Lock the refresh list to operational coverage and the HICP identity rules.

The OECD leading indicator stays stored and stays out of refresh. The two ECB
HICP series stay on their own dataset ids. The Eurostat replacement is a
different object.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aqil_research.adapters.ecb_hicp_core.constants import DATASET_ID as ECB_CORE_DATASET_ID
from aqil_research.adapters.ecb_sdw.constants import DATASET_ID as ECB_HEADLINE_DATASET_ID
from aqil_research.adapters.eurostat_gdp.constants import GEO_CODE as GDP_GEO_CODE
from aqil_research.adapters.eurostat_gdp.constants import GEO_LABEL as GDP_GEO_LABEL
from aqil_research.adapters.eurostat_hicp.client import series_json_url
from aqil_research.adapters.eurostat_hicp.constants import (
    CORE_COUNTERPART_STORED,
    DATASET_CODE,
    DATASET_ID,
    DISCONTINUED_DATASET_CODE,
    GEO_CODE,
    SEASONAL_VALUE,
    SOURCE_ID,
)
from aqil_research.adapters.eurostat_hicp.parse import parse_eurostat_json
from aqil_research.contracts.observation import SeasonalAdjustment
from aqil_research.methods.macro_conditions import MacroConditionsMethod
from aqil_research.methods.prices_and_policy import PricesAndPolicyMethod
from aqil_research.workflow.refresh import default_refresh_steps

ROOT = Path(__file__).resolve().parents[3]
COVERAGE = ROOT / "docs" / "sources" / "MACRO_COVERAGE.csv"
SYNTHESIS = (
    ROOT
    / "workers"
    / "research"
    / "src"
    / "aqil_research"
    / "methods"
    / "macro_reading_synthesis.py"
)
PUBLICATION_STEPS = {
    "bls_employment_situation_archive",
    "bls_cpi_archive",
    "federal_reserve_monetary_press",
    "ecb_monetary_press",
    "bls_ics_schedule",
}
BLOCKED_FROM_REFRESH = {
    "oecd_cli_g20",
    "meti_iip_production_sa",
    "boj_fm01_call_rate",
    "boj_fm08_yen",
    "nbs_national_data",
    "nbs_cpi",
    "nbs_industrial_production",
    "pboc_statistics",
    "pboc_policy_rate",
    "pboc_exchange_rate",
    "census_adv_durable_goods",
}
RETRIEVED = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
GEO_LABEL = (
    "Euro area (EA11-1999, EA12-2001, EA13-2007, EA15-2008, EA16-2009, "
    "EA17-2011, EA18-2014, EA19-2015, EA20-2023, EA21-2026)"
)


def test_refresh_list_matches_operational_coverage_and_excludes_oecd() -> None:
    operational = {row["source_id"] for row in _coverage_rows() if row["status"] == "operational"}
    steps = {name for name, _action in default_refresh_steps()}
    assert operational == (steps - PUBLICATION_STEPS) | {"bls_cps_unemployment_rate"}
    assert SOURCE_ID in operational
    assert "oecd_cli_g20" not in steps
    assert "oecd_cli_g20" not in operational
    for source_id in BLOCKED_FROM_REFRESH:
        assert source_id not in steps


def test_ecb_hicp_identities_stay_unchanged() -> None:
    assert ECB_HEADLINE_DATASET_ID == "ecb.icp.M.U2.Y.000000.3.INX"
    assert ECB_CORE_DATASET_ID == "ecb.icp.M.U2.Y.XEF000.3.INX"
    assert DATASET_ID not in {ECB_HEADLINE_DATASET_ID, ECB_CORE_DATASET_ID}
    assert DATASET_CODE == "prc_hicp_minr"
    assert DATASET_CODE != DISCONTINUED_DATASET_CODE
    assert SEASONAL_VALUE == "not_seasonally_adjusted"
    assert GEO_CODE == "EA"
    assert CORE_COUNTERPART_STORED is False
    assert "includeHistory" not in series_json_url()
    assert "prc_hicp_midx" not in series_json_url()
    assert "s_adj" not in series_json_url()


def test_existing_euro_area_series_stay_on_ea21() -> None:
    assert GDP_GEO_CODE == "EA21"
    assert GDP_GEO_LABEL == "Euro area \u2013 21 countries (from 2026)"
    assert GEO_CODE != GDP_GEO_CODE


def test_new_hicp_index_stays_out_of_the_us_readings() -> None:
    assert DATASET_ID not in PricesAndPolicyMethod().required_dataset_ids()
    assert DATASET_ID not in MacroConditionsMethod().required_dataset_ids()
    synthesis = SYNTHESIS.read_text(encoding="utf-8")
    assert DATASET_ID not in synthesis
    assert "eurostat_hicp_total_ea" not in synthesis


def test_parser_stores_the_nsa_index_and_refuses_the_other_objects() -> None:
    text = _fixture()
    parsed = parse_eurostat_json(text, retrieved_at=RETRIEVED)
    assert len(parsed.observations) == 2
    assert parsed.observations[0].dataset_id == DATASET_ID
    assert parsed.observations[0].seasonal_adjustment is SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
    assert parsed.observations[0].unit == "index, 2025 = 100"
    assert parsed.observations[0].geography == "EA"
    assert parsed.omitted_periods == ("2026-08",)

    rate = _fixture(unit_code="RCH_A", unit_label="Annual rate of change")
    with pytest.raises(ValueError, match="rate-of-change"):
        parse_eurostat_json(rate, retrieved_at=RETRIEVED)

    seasonal = _fixture(extra_dimension=("s_adj", "SA", "Seasonally adjusted data"))
    with pytest.raises(ValueError, match="seasonal-adjustment"):
        parse_eurostat_json(seasonal, retrieved_at=RETRIEVED)

    discontinued = _fixture(extension_id="PRC_HICP_MIDX")
    with pytest.raises(ValueError, match="prc_hicp_midx"):
        parse_eurostat_json(discontinued, retrieved_at=RETRIEVED)

    import aqil_research.adapters.eurostat_hicp.parse as parse_module

    original = parse_module.DATASET_ID
    parse_module.DATASET_ID = ECB_HEADLINE_DATASET_ID
    try:
        with pytest.raises(ValueError, match="ECB HICP dataset"):
            parse_eurostat_json(text, retrieved_at=RETRIEVED)
    finally:
        parse_module.DATASET_ID = original


def _coverage_rows() -> list[dict[str, str]]:
    with COVERAGE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _fixture(
    *,
    unit_code: str = "I25",
    unit_label: str = "Index, 2025=100",
    extension_id: str = "PRC_HICP_MINR",
    extra_dimension: tuple[str, str, str] | None = None,
) -> str:
    dimensions = [
        ("freq", "M", "Monthly"),
        ("unit", unit_code, unit_label),
        ("coicop18", "TOTAL", "Total"),
        ("geo", "EA", GEO_LABEL),
    ]
    if extra_dimension is not None:
        dimensions.append(extra_dimension)
    periods = [("2026-07", "100.10"), ("2026-08", None), ("2026-09", "104.31")]
    dimension: dict[str, object] = {}
    for name, code, label in dimensions:
        dimension[name] = {"category": {"index": {code: 0}, "label": {code: label}}}
    dimension["time"] = {
        "category": {
            "index": {token: index for index, (token, _value) in enumerate(periods)},
            "label": {token: token for token, _value in periods},
        },
    }
    values = {
        str(index): json.loads(value)
        for index, (_token, value) in enumerate(periods)
        if value is not None
    }
    payload = {
        "label": (
            "Harmonised index of consumer prices (HICP) - ECOICOP ver.2 - "
            "indices and rates of change, monthly data"
        ),
        "source": "ESTAT",
        "extension": {"agencyId": "ESTAT", "id": extension_id},
        "id": [name for name, _code, _label in dimensions] + ["time"],
        "size": [1 for _item in dimensions] + [len(periods)],
        "dimension": dimension,
        "value": values,
    }
    return json.dumps(payload)
