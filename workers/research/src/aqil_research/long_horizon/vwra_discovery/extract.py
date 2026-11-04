"""Pull continuous numbers out of an existing method calculation.

A missing field is a failure. This module does not invent a series.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.money import decimal_text
from aqil_research.long_horizon.state_atlas.features import _shift_months, period_bound
from aqil_research.long_horizon.vwra_discovery.specification import PHASE_CODE
from aqil_research.methods.harding_pagan_characteristics import expansion_contraction_states


@dataclass(frozen=True)
class RawPoint:
    series_key: str
    period_start: date
    period_end: date
    value_text: str | None
    state_label: str | None
    unit: str


def as_number(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return decimal_text(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return decimal_text(Decimal(str(value)))
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return None
        try:
            return decimal_text(Decimal(text))
        except ArithmeticError:
            return None
    return None


def _day(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _month_end(start: date) -> date:
    return period_bound(start, None, "monthly")


def _quarter_end(start: date) -> date:
    return period_bound(start, None, "quarterly")


def _point(
    series_key: str,
    start: date,
    end: date,
    value: object,
    unit: str,
    label: str | None = None,
) -> RawPoint | None:
    text = as_number(value)
    if text is None and label is None:
        return None
    return RawPoint(series_key, start, end, text, label, unit)


def _span_months(start: date, end: date) -> list[date]:
    cursor = start
    months: list[date] = []
    while cursor <= end:
        months.append(cursor)
        cursor = _shift_months(cursor, 1)
    return months


def extract_points(
    method_id: str,
    calculation: Mapping[str, object] | None,
    sample_end: date,
) -> tuple[list[RawPoint], str | None]:
    """Return points, or a failure reason when the calculation has no number."""
    if not isinstance(calculation, Mapping):
        return [], "the calculation is empty"
    try:
        points = _EXTRACTORS[method_id](calculation, sample_end)
    except (KeyError, ValueError, ArithmeticError) as exc:
        return [], f"the calculation could not be read: {exc}"
    kept = [point for point in points if point.value_text is not None or point.state_label]
    numbered = [point for point in kept if point.value_text is not None]
    if not numbered:
        return [], "the calculation did not contain a continuous number"
    return kept, None


def _sahm(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    start = _day(calculation["evaluation_period"])
    label = "threshold_met" if calculation.get("threshold_met") is True else "threshold_not_met"
    point = _point(
        "gap_percentage_points",
        start,
        _month_end(start),
        calculation.get("gap_percentage_points"),
        "percentage_points",
        label,
    )
    return [] if point is None else [point]


def _period_change(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    start = _day(calculation["evaluation_period"])
    point = _point(
        "level_change",
        start,
        _month_end(start),
        calculation.get("level_change"),
        "percentage_points",
    )
    return [] if point is None else [point]


def _sloos(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    start = _day(calculation["observation_period"])
    point = _point(
        "net_tightening_share_percent",
        start,
        _quarter_end(start),
        calculation.get("net_tightening_share_percent"),
        "percent_net_tightening",
        str(calculation.get("direction_label") or "") or None,
    )
    return [] if point is None else [point]


def _labour(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    rows = calculation.get("series")
    if not isinstance(rows, list):
        return []
    mapping = {
        "bls.ln.LNS14000000": (
            (
                "unemployment_change_percentage_points",
                "change_percentage_points",
                "percentage_points",
            ),
        ),
        "bls.ce.CES0000000001": (
            ("payrolls_percent_change", "percent_change", "percent"),
            ("payrolls_change_thousands", "change_thousands", "thousands"),
        ),
        "bls.jt.JTS000000000000000JOL": (
            ("openings_percent_change", "percent_change", "percent"),
            ("openings_change_thousands", "change_thousands", "thousands"),
        ),
    }
    points: list[RawPoint] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        dataset_id = str(row.get("dataset_id"))
        change = row.get("twelve_month_change")
        if not isinstance(change, Mapping):
            continue
        start = _day(row["latest_period"])
        for series_key, field, unit in mapping.get(dataset_id, ()):
            point = _point(series_key, start, _month_end(start), change.get(field), unit)
            if point is not None:
                points.append(point)
    return points


def _prices(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    specs = (
        ("cpi_u", "cpi_twelve_month_percent_change", "twelve_month_percent_change", "percent"),
        (
            "federal_funds",
            "funds_one_month_change_percentage_points",
            "one_month_change_percentage_points",
            "percentage_points",
        ),
        (
            "treasury_10_year",
            "treasury_10y_one_month_change_percentage_points",
            "one_month_change_percentage_points",
            "percentage_points",
        ),
    )
    points: list[RawPoint] = []
    for block, series_key, field, unit in specs:
        payload = calculation.get(block)
        if not isinstance(payload, Mapping):
            continue
        start = _day(payload["period"])
        point = _point(series_key, start, _month_end(start), payload.get(field), unit)
        if point is not None:
            points.append(point)
    return points


def _ip_activity(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    start = _day(calculation["latest_period"])
    point = _point(
        "twelve_month_percent_change",
        start,
        _month_end(start),
        calculation.get("twelve_month_percent_change"),
        "percent",
    )
    return [] if point is None else [point]


def _credit(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    points: list[RawPoint] = []
    standards = calculation.get("lending_standards")
    if isinstance(standards, Mapping):
        start = _day(standards["latest_period_start"])
        point = _point(
            "difference_percentage_points",
            start,
            _quarter_end(start),
            standards.get("difference_percentage_points"),
            "percentage_points",
        )
        if point is not None:
            points.append(point)
    volume = calculation.get("bank_credit")
    if isinstance(volume, Mapping) and volume.get("sufficiency") == "sufficient":
        start = _day(volume["latest_period_start"])
        point = _point(
            "change_usd_millions",
            start,
            start,
            volume.get("change_usd_millions"),
            "usd_millions",
        )
        if point is not None:
            points.append(point)
    return points


def _estrella(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    start = _day(calculation["evaluation_period"])
    point = _point(
        "spread", start, _month_end(start), calculation.get("spread"), "percentage_points"
    )
    return [] if point is None else [point]


def _real_funds(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    start = _day(calculation["inflation_end_month"])
    point = _point(
        "real_funds_rate_percent_per_year",
        start,
        _month_end(start),
        calculation.get("real_funds_rate_percent_per_year"),
        "percent_per_year",
    )
    return [] if point is None else [point]


def _federal_funds(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    months = calculation.get("months")
    if not isinstance(months, list):
        return []
    points: list[RawPoint] = []
    for row in months:
        if not isinstance(row, Mapping):
            continue
        start = _day(row["period"])
        point = _point(
            "ex_post_real_rate_percentage_points",
            start,
            _month_end(start),
            row.get("ex_post_real_rate_percentage_points"),
            "percentage_points",
        )
        if point is not None:
            points.append(point)
    return points


def _diffusion(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    months = calculation.get("months")
    if not isinstance(months, list):
        return []
    points: list[RawPoint] = []
    for row in months:
        if not isinstance(row, Mapping):
            continue
        start = _day(row["period"])
        share = _point("share", start, _month_end(start), row.get("share"), "share")
        if share is not None:
            points.append(share)
        persistence = _point(
            "persistence_months",
            start,
            _month_end(start),
            row.get("persistence_months"),
            "months",
        )
        if persistence is not None:
            points.append(persistence)
    return points


def _hamilton(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    points: list[RawPoint] = []
    blocks = {
        "filtered_regime_probabilities": "filtered",
        "smoothed_regime_probabilities": "smoothed",
    }
    for block, prefix in blocks.items():
        rows = calculation.get(block)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            start = _day(row["period"])
            for field in ("higher_mean", "lower_mean"):
                point = _point(
                    f"{prefix}_{field}",
                    start,
                    _month_end(start),
                    row.get(field),
                    "probability",
                )
                if point is not None:
                    points.append(point)
    return points


def _phases(
    dataset_key: str,
    peaks: object,
    troughs: object,
) -> list[RawPoint]:
    if not isinstance(peaks, list) or not isinstance(troughs, list):
        return []
    states = expansion_contraction_states(
        tuple(_day(item) for item in peaks),
        tuple(_day(item) for item in troughs),
    )
    if states is None:
        return []
    points: list[RawPoint] = []
    for start, label in sorted(states.items()):
        point = _point(
            f"{dataset_key}:phase",
            start,
            _month_end(start),
            PHASE_CODE[label],
            "phase_code",
            label,
        )
        if point is not None:
            points.append(point)
    return points


def _bry(calculation: Mapping[str, object], sample_end: date) -> list[RawPoint]:
    points = _phases("g17", calculation.get("peaks"), calculation.get("troughs"))
    mcd = _point(
        "mcd_months", sample_end, _month_end(sample_end), calculation.get("mcd_months"), "months"
    )
    if mcd is not None:
        points.append(mcd)
    return points


def _harding(calculation: Mapping[str, object], sample_end: date) -> list[RawPoint]:
    rows = calculation.get("series")
    points: list[RawPoint] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            dataset_id = str(row.get("dataset_id"))
            points.extend(_phases(dataset_id, row.get("peaks"), row.get("troughs")))
            phases = row.get("phases")
            if not isinstance(phases, list):
                continue
            for phase in phases:
                if not isinstance(phase, Mapping) or phase.get("amplitude_percent") is None:
                    continue
                end = _day(phase["end"])
                point = _point(
                    f"{dataset_id}:amplitude_percent",
                    end,
                    _month_end(end),
                    phase.get("amplitude_percent"),
                    "percent",
                    str(phase.get("phase") or "") or None,
                )
                if point is not None:
                    points.append(point)
    pairs = calculation.get("concordance")
    if isinstance(pairs, list):
        for pair in pairs:
            if not isinstance(pair, Mapping) or pair.get("computed") is not True:
                continue
            left = str(pair.get("left_dataset_id"))
            right = str(pair.get("right_dataset_id"))
            point = _point(
                f"concordance:{left}:{right}",
                sample_end,
                _month_end(sample_end),
                pair.get("concordance"),
                "share",
            )
            if point is not None:
                points.append(point)
    return points


def _bai(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    segments = calculation.get("segments")
    if not isinstance(segments, list):
        return []
    points: list[RawPoint] = []
    for segment in segments:
        if not isinstance(segment, Mapping):
            continue
        for start in _span_months(_day(segment["start"]), _day(segment["end"])):
            point = _point(
                "mean_log_growth",
                start,
                _month_end(start),
                segment.get("mean_log_growth"),
                "log_growth",
            )
            if point is not None:
                points.append(point)
    return points


def _factor(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    path = calculation.get("filtered_factor")
    if not isinstance(path, list):
        return []
    start = _day(calculation["growth_start"])
    last = _day(calculation["sample_levels"][1])
    months = _span_months(start, last)
    if len(months) != len(path):
        raise ValueError(
            "the filtered factor length does not match a contiguous month span, "
            "and the calculation does not list the months"
        )
    points: list[RawPoint] = []
    for month, value in zip(months, path, strict=True):
        point = _point("filtered_factor", month, _month_end(month), value, "coincident_factor")
        if point is not None:
            points.append(point)
    return points


def _probit(calculation: Mapping[str, object], _sample_end: date) -> list[RawPoint]:
    if (
        calculation.get("fit_status") != "estimated"
        or calculation.get("probabilities_accepted") is not True
    ):
        reason = calculation.get("fit_status") or "not_estimated"
        raise ValueError(f"probit fit {reason}")
    rows = calculation.get("probabilities")
    if not isinstance(rows, list) or not rows:
        raise ValueError("probit fit produced no probabilities")
    points: list[RawPoint] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        start = _day(row["outcome_quarter"])
        point = _point(
            "probability",
            start,
            _quarter_end(start),
            row.get("probability"),
            "probability",
        )
        if point is not None:
            points.append(point)
    return points


def _lead_lag(calculation: Mapping[str, object], sample_end: date) -> list[RawPoint]:
    end = _day(calculation.get("growth_end") or sample_end)
    pairs = calculation.get("pairs")
    if not isinstance(pairs, list):
        return []
    points: list[RawPoint] = []
    for pair in pairs:
        if not isinstance(pair, Mapping):
            continue
        left = str(pair.get("first_dataset_id"))
        right = str(pair.get("second_dataset_id"))
        lags = pair.get("lags")
        if not isinstance(lags, list):
            continue
        for lag in lags:
            if not isinstance(lag, Mapping) or lag.get("correlation") is None:
                continue
            point = _point(
                f"lag_correlation:{left}:{right}:{lag.get('lag')}",
                end,
                _month_end(end),
                lag.get("correlation"),
                "correlation",
            )
            if point is not None:
                points.append(point)
    return points


def _adf(calculation: Mapping[str, object], sample_end: date) -> list[RawPoint]:
    end = _day(calculation.get("growth_end") or sample_end)
    point = _point(
        "adf_statistic", end, _month_end(end), calculation.get("statistic"), "adf_statistic"
    )
    return [] if point is None else [point]


def _cusum(calculation: Mapping[str, object], sample_end: date) -> list[RawPoint]:
    end = _day(calculation.get("growth_end") or sample_end)
    point = _point("extreme_cusum", end, _month_end(end), calculation.get("extreme_cusum"), "cusum")
    return [] if point is None else [point]


def _horizons(calculation: Mapping[str, object], sample_end: date) -> list[RawPoint]:
    end = _day(calculation.get("growth_end") or sample_end)
    rows = calculation.get("horizons")
    points: list[RawPoint] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping) or row.get("mae") is None:
                continue
            point = _point(
                f"mae_h{row.get('horizon_months')}",
                end,
                _month_end(end),
                row.get("mae"),
                "mae",
            )
            if point is not None:
                points.append(point)
    if calculation.get("persistence") is not None and not isinstance(
        calculation.get("persistence"), str
    ):
        point = _point(
            "persistence",
            end,
            _month_end(end),
            calculation.get("persistence"),
            "ar_coefficient_sum",
        )
        if point is not None:
            points.append(point)
    return points


def _cpi_ar(calculation: Mapping[str, object], sample_end: date) -> list[RawPoint]:
    end = _day(calculation.get("growth_end") or sample_end)
    point = _point(
        "persistence",
        end,
        _month_end(end),
        calculation.get("persistence"),
        "ar_coefficient_sum",
    )
    return [] if point is None else [point]


_EXTRACTORS = {
    "SAHM_UNEMPLOYMENT_GAP": _sahm,
    "PERIOD_LEVEL_CHANGE": _period_change,
    "SLOOS_CIL_LENDING_STANDARDS": _sloos,
    "LABOUR_MARKET_CONDITIONS": _labour,
    "PRICES_AND_POLICY": _prices,
    "INDUSTRIAL_PRODUCTION_ACTIVITY": _ip_activity,
    "CREDIT_STANDARDS_AND_VOLUMES": _credit,
    "ESTRELLA_MISHKIN_TERM_SPREAD": _estrella,
    "EX_POST_REAL_FUNDS_RATE": _real_funds,
    "EX_POST_REAL_FEDERAL_FUNDS_RATE": _federal_funds,
    "RESTRICTED_COINCIDENT_DIFFUSION": _diffusion,
    "HAMILTON_MONTHLY_REGIME_SWITCHING": _hamilton,
    "BRY_BOSCHAN_SPENCER15_VARIANT": _bry,
    "HARDING_PAGAN_CHARACTERISTICS": _harding,
    "BAI_PERRON_MEAN_SHIFTS": _bai,
    "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT": _factor,
    "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT": _probit,
    "LEAD_LAG_CROSS_CORRELATION": _lead_lag,
    "ENGLE_GRANGER_COINTEGRATION": _adf,
    "CUSUM_RECURSIVE_RESIDUALS": _cusum,
    "IP_GROWTH_CUSUM": _cusum,
    "INFLATION_AUTOREGRESSION": _horizons,
    "AUTOREGRESSIVE_BENCHMARK": _horizons,
    "CPI_U_INFLATION_AUTREGRESSION": _cpi_ar,
}
