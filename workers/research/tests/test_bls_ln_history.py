"""The LN flat file keeps the history it prints. It does not open a year window."""

from __future__ import annotations

import inspect
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from aqil_research.adapters.bls_ln_history.adapter import BlsLnHistoryAdapter, BlsLnHistoryConfig
from aqil_research.adapters.bls_ln_history.client import LnClientError, assert_ln_url
from aqil_research.adapters.bls_ln_history.constants import DATA_URL, SERIES_URL
from aqil_research.adapters.bls_ln_history.parse import (
    confirm_unemployment_series,
    extract_unemployment_months,
)

RETRIEVED = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
SERIES = (
    "series_id\tperiodicity_code\tseries_title\tseasonal\t"
    "begin_year\tbegin_period\tend_year\tend_period\n"
    "LNS14000000\tM\t(Seas) Unemployment Rate\tS\t1948\tM01\t1948\tM03\n"
    "LNS14000000Q\tQ\t(Seas) Unemployment Rate\tS\t1948\tQ01\t1948\tQ01\n"
)
DATA = """series_id\tyear\tperiod\tvalue\tfootnote_codes
LNS14000000\t1948\tM01\t3.4\t
LNS14000000\t1948\tM02\t-\t
LNS14000000\t1948\tM03\t3.8\t
LNS14000000Q\t1948\tQ01\t3.5\t
"""


def test_series_file_binds_the_monthly_rate_and_not_the_quarter() -> None:
    binding = confirm_unemployment_series(SERIES)
    assert binding.title == "(Seas) Unemployment Rate"
    assert binding.begin == date(1948, 1, 1)
    assert binding.end == date(1948, 3, 1)


def test_extract_keeps_early_months_and_does_not_fill_a_blank() -> None:
    binding = confirm_unemployment_series(SERIES)
    extracted = extract_unemployment_months(DATA, binding)
    assert [row.period_start for row in extracted.rows] == [date(1948, 1, 1), date(1948, 3, 1)]
    assert [row.value for row in extracted.rows] == ["3.4", "3.8"]
    assert extracted.omitted_periods == ("1948-02-01",)
    assert "start_year" not in inspect.signature(extract_unemployment_months).parameters


def test_a_long_span_is_not_cut_at_2023() -> None:
    series = SERIES.replace("1948\tM03", "2026\tM01")
    data = DATA + "LNS14000000\t2026\tM01\t4.2\t\n"
    binding = confirm_unemployment_series(series)
    extracted = extract_unemployment_months(data, binding)
    periods = [row.period_start for row in extracted.rows]
    assert periods[0] == date(1948, 1, 1)
    assert periods[-1] == date(2026, 1, 1)
    assert date(2023, 1, 1) not in periods
    assert "1948-01-01" not in extracted.omitted_periods
    assert "2025-10-01" in extracted.omitted_periods


def test_wrong_title_does_not_bind() -> None:
    with pytest.raises(ValueError, match="title"):
        confirm_unemployment_series(SERIES.replace("(Seas) Unemployment Rate", "Employment"))


def test_client_rejects_other_hosts_and_the_api() -> None:
    assert_ln_url(SERIES_URL)
    assert_ln_url(DATA_URL)
    with pytest.raises(LnClientError):
        assert_ln_url("https://api.bls.gov/publicAPI/v2/timeseries/data/")
    with pytest.raises(LnClientError):
        assert_ln_url("https://fred.stlouisfed.org/series/UNRATE")
    with pytest.raises(LnClientError):
        assert_ln_url("https://download.bls.gov/pub/time.series/ce/ce.series")


def test_adapter_reads_a_fixture_without_a_year_window(tmp_path: Path) -> None:
    series_path = tmp_path / "ln.series"
    data_path = tmp_path / "ln.data.1.AllData"
    series_path.write_text(SERIES, encoding="utf-8")
    data_path.write_text(DATA, encoding="utf-8")
    result = BlsLnHistoryAdapter(
        config=BlsLnHistoryConfig(live=False, series_path=series_path, data_path=data_path),
        retrieved_at=RETRIEVED,
    ).fetch()
    assert result.errors == ()
    assert [row.period_start for row in result.observations] == [
        date(1948, 1, 1),
        date(1948, 3, 1),
    ]
    assert result.observations[0].series_provenance.value == "latest_revised"
    assert result.observations[0].dataset_id == "bls.ln.LNS14000000"
