"""Published Spencer-15 variant of monthly Bry-Boschan dating.

This is not the 1971 program listing and not a FORTRAN replica.
`BRY_BOSCHAN_MONTHLY_1971` still refuses to date. The 1971 volume does not
print the Spencer coefficients or the twelve-month placement, and footnote 7
cites no source.

Weights and divisor: Frederick R. Macaulay, *The Smoothing of Time Series*
(NBER, 1931), chapter III, book page 55,
https://www.nber.org/system/files/chapters/c9363/c9363.pdf.
The page prints the fifteen coefficients over 320:
-3, -6, -5, +3, +21, +46, +67, +74, +67, +46, +21, +3, -5, -6, -3.

Twelve-month placement: Takeshi Otsu, "Robust Statistics and Business Cycle
Dating", Seijo University Economic Papers, no. 228, March 2020, the section
"Dating Algorithm: Bry-Boschan Procedure". The page says the MA12 filter is
not symmetric: 6 lags and 5 leads, so the value dated at month t uses t-6
through t+5. Otsu says that description follows the FORTRAN rather than the
1971 prose. Harding-Pagan quarterly BBQ is not used.

Other windows are the 1971 chapter 2 rules already frozen in the dossier.
Even spans use the same one-extra-lag split that the twelve-month sentence
prints, which is also the centred window when the span is odd. Months for
cyclical dominance use absolute differences, the difference option Otsu
names, then the 1971 confinement to three through six months.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.bry_boschan_monthly import (
    G17_DATASET_ID,
    G17InputPoint,
    assess_g17_level_input,
)
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

BRY_BOSCHAN_SPENCER15_VARIANT = "BRY_BOSCHAN_SPENCER15_VARIANT"
VARIANT_VERSION = "1.0.0"
PUBLICATION_ALLOWED = False

SPENCER_WEIGHTS: tuple[int, ...] = (
    -3,
    -6,
    -5,
    3,
    21,
    46,
    67,
    74,
    67,
    46,
    21,
    3,
    -5,
    -6,
    -3,
)
SPENCER_DIVISOR = 320
SPENCER_RADIUS = 7
MA12_LAGS = 6
MA12_LEADS = 5
OUTLIER_STANDARD_DEVIATIONS = Decimal("3.5")
LOCAL_RADIUS = 5
MINIMUM_CYCLE_MONTHS = 15
MINIMUM_PHASE_MONTHS = 5
ENDPOINT_BAN_MONTHS = 6
CROSSOVER_CONTRACTION_MONTHS = 10
FINAL_WINDOW_FLOOR = 4
MCD_FLOOR = 3
MCD_CAP = 6

MACAULAY_CITATION = (
    "Frederick R. Macaulay, The Smoothing of Time Series, NBER, 1931, "
    "book page 55, https://www.nber.org/system/files/chapters/c9363/c9363.pdf"
)
OTSU_CITATION = (
    "Takeshi Otsu, Robust Statistics and Business Cycle Dating, "
    "Seijo University Economic Papers, no. 228, March 2020, "
    "https://www.seijo.ac.jp/education/faeco/academic-journals/"
    "jtmo420000001iji-att/228-3otsu.pdf"
)
NBER_CHRONOLOGY_CITATION = (
    "NBER US Business Cycle Expansions and Contractions, "
    "https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions, "
    "page dated 14 March 2023"
)

CAUSAL_HYPOTHESIS = "No causal mechanism is established."
NOT_THE_1971_LISTING = (
    "This is the labelled Spencer-15 variant. It is not the 1971 program listing "
    "and it is not a FORTRAN replica."
)


class BryBoschanSpencer15Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class _Turn:
    index: int
    kind: Literal["peak", "trough"]
    value: Decimal


@dataclass(frozen=True, slots=True)
class Spencer15Dates:
    peaks: tuple[date, ...]
    troughs: tuple[date, ...]
    mcd_months: int
    variant_id: str = BRY_BOSCHAN_SPENCER15_VARIANT


def spencer_weights_sum() -> int:
    return sum(SPENCER_WEIGHTS)


def centred_spencer(values: tuple[Decimal, ...] | list[Decimal]) -> list[Decimal | None]:
    """Fifteen-point Spencer curve. The centre weight 74 is dated at month t."""
    series = list(values)
    size = len(series)
    curve: list[Decimal | None] = [None] * size
    if size < len(SPENCER_WEIGHTS):
        return curve
    for centre in range(SPENCER_RADIUS, size - SPENCER_RADIUS):
        total = Decimal(0)
        for offset, weight in enumerate(SPENCER_WEIGHTS):
            total += Decimal(weight) * series[centre - SPENCER_RADIUS + offset]
        curve[centre] = total / Decimal(SPENCER_DIVISOR)
    return curve


def moving_average(
    values: tuple[Decimal, ...] | list[Decimal],
    span: int,
) -> list[Decimal | None]:
    """Date the average at t.

    Lags are span // 2 and leads are span - lags - 1. For twelve months that
    is 6 lags and 5 leads. An odd span is the centred window.
    """
    if span < 1:
        raise ValueError("span must be at least 1")
    series = list(values)
    size = len(series)
    lags = span // 2
    leads = span - lags - 1
    curve: list[Decimal | None] = [None] * size
    for centre in range(size):
        start = centre - lags
        end = centre + leads
        if start < 0 or end >= size:
            continue
        window = series[start : end + 1]
        curve[centre] = sum(window, Decimal(0)) / Decimal(span)
    return curve


def _sample_standard_deviation(values: list[Decimal]) -> Decimal:
    count = len(values)
    if count < 2:
        return Decimal(0)
    mean = sum(values, Decimal(0)) / Decimal(count)
    squared = sum((item - mean) ** 2 for item in values)
    return (squared / Decimal(count - 1)).sqrt()


def replace_extremes(
    values: list[Decimal],
    spencer_a: list[Decimal | None],
) -> list[Decimal]:
    """Replace a month when its percentage ratio is more than 3.5 sample SD from the mean."""
    ratios: list[Decimal] = []
    indexes: list[int] = []
    for index, curve_value in enumerate(spencer_a):
        if curve_value is None or curve_value == 0:
            continue
        ratios.append(Decimal(100) * values[index] / curve_value)
        indexes.append(index)
    if len(ratios) < 2:
        return list(values)
    mean = sum(ratios, Decimal(0)) / Decimal(len(ratios))
    deviation = _sample_standard_deviation(ratios)
    limit = OUTLIER_STANDARD_DEVIATIONS * deviation
    replaced = list(values)
    for index, ratio in zip(indexes, ratios, strict=True):
        if abs(ratio - mean) > limit:
            curve_value = spencer_a[index]
            if curve_value is not None:
                replaced[index] = curve_value
    return replaced


def _best_index(
    curve: list[Decimal | None],
    centre: int,
    radius: int,
    kind: Literal["peak", "trough"],
) -> int | None:
    start = max(0, centre - radius)
    end = min(len(curve) - 1, centre + radius)
    chosen: int | None = None
    chosen_value: Decimal | None = None
    for index in range(start, end + 1):
        value = curve[index]
        if value is None:
            continue
        if chosen is None or chosen_value is None:
            chosen = index
            chosen_value = value
            continue
        if kind == "peak":
            if value > chosen_value or (value == chosen_value and index < chosen):
                chosen = index
                chosen_value = value
        elif value < chosen_value or (value == chosen_value and index > chosen):
            chosen = index
            chosen_value = value
    return chosen


def _local_turns(curve: list[Decimal | None], radius: int) -> list[_Turn]:
    turns: list[_Turn] = []
    for index, value in enumerate(curve):
        if value is None:
            continue
        start = index - radius
        end = index + radius
        if start < 0 or end >= len(curve):
            continue
        neighbours = curve[start : end + 1]
        if any(item is None for item in neighbours):
            continue
        if all(value > item for offset, item in enumerate(neighbours) if offset != radius):
            turns.append(_Turn(index, "peak", value))
        elif all(value < item for offset, item in enumerate(neighbours) if offset != radius):
            turns.append(_Turn(index, "trough", value))
    return turns


def _prefer(left: _Turn, right: _Turn) -> _Turn:
    if left.kind != right.kind:
        raise ValueError("alternation compares like turns")
    if left.kind == "peak":
        if left.value > right.value or (left.value == right.value and left.index < right.index):
            return left
        return right
    if left.value < right.value or (left.value == right.value and left.index > right.index):
        return left
    return right


def _enforce_alternation(turns: list[_Turn]) -> list[_Turn]:
    ordered = sorted(turns, key=lambda item: item.index)
    changed = True
    while changed and ordered:
        changed = False
        reduced: list[_Turn] = []
        for turn in ordered:
            if reduced and reduced[-1].kind == turn.kind:
                reduced[-1] = _prefer(reduced[-1], turn)
                changed = True
            else:
                reduced.append(turn)
        ordered = reduced
    return ordered


def _drop_short_cycles(turns: list[_Turn]) -> list[_Turn]:
    """Drop the lower peak or higher trough when like turns are under fifteen months apart."""
    ordered = sorted(turns, key=lambda item: item.index)
    changed = True
    while changed:
        changed = False
        for kind in ("peak", "trough"):
            group = [turn for turn in ordered if turn.kind == kind]
            for index in range(len(group) - 1):
                left = group[index]
                right = group[index + 1]
                if right.index - left.index >= MINIMUM_CYCLE_MONTHS:
                    continue
                dropped = left if _prefer(left, right) is right else right
                ordered = [
                    turn
                    for turn in ordered
                    if not (turn.index == dropped.index and turn.kind == dropped.kind)
                ]
                changed = True
                break
            if changed:
                break
    return ordered


def _drop_short_phases(turns: list[_Turn]) -> list[_Turn]:
    """Drop the later turn of a phase shorter than five months."""
    ordered = sorted(turns, key=lambda item: item.index)
    changed = True
    while changed:
        changed = False
        for index in range(len(ordered) - 1):
            if ordered[index + 1].index - ordered[index].index >= MINIMUM_PHASE_MONTHS:
                continue
            ordered.pop(index + 1)
            changed = True
            break
    return ordered


def _drop_endpoints(turns: list[_Turn], size: int) -> list[_Turn]:
    last = size - 1 - ENDPOINT_BAN_MONTHS
    return [turn for turn in turns if ENDPOINT_BAN_MONTHS <= turn.index <= last]


def _drop_end_dominance(turns: list[_Turn], curve: list[Decimal | None]) -> list[_Turn]:
    ordered = list(turns)
    if not ordered:
        return ordered
    first = ordered[0]
    earlier = [item for item in curve[: first.index] if item is not None]
    if first.kind == "peak" and any(item > first.value for item in earlier):
        ordered = ordered[1:]
    elif first.kind == "trough" and any(item < first.value for item in earlier):
        ordered = ordered[1:]
    if not ordered:
        return ordered
    last = ordered[-1]
    later = [item for item in curve[last.index + 1 :] if item is not None]
    if last.kind == "peak" and any(item > last.value for item in later):
        ordered = ordered[:-1]
    elif last.kind == "trough" and any(item < last.value for item in later):
        ordered = ordered[:-1]
    return ordered


def _drop_crossovers(
    turns: list[_Turn],
    curve: list[Decimal | None],
    radius: int,
) -> list[_Turn]:
    ordered = sorted(turns, key=lambda item: item.index)
    dropped: set[int] = set()
    for index in range(len(ordered) - 1):
        peak = ordered[index]
        trough = ordered[index + 1]
        if peak.kind != "peak" or trough.kind != "trough":
            continue
        if trough.index - peak.index >= CROSSOVER_CONTRACTION_MONTHS:
            continue
        peak_at = _best_index(curve, peak.index, radius, "peak")
        trough_at = _best_index(curve, trough.index, radius, "trough")
        if peak_at is None or trough_at is None:
            continue
        if trough_at < peak_at:
            dropped.add(peak.index)
            dropped.add(trough.index)
    return [turn for turn in ordered if turn.index not in dropped]


def _refine(
    turns: list[_Turn],
    curve: list[Decimal | None],
    radius: int,
) -> list[_Turn]:
    refined: list[_Turn] = []
    for turn in turns:
        found = _best_index(curve, turn.index, radius, turn.kind)
        if found is None or curve[found] is None:
            continue
        refined.append(_Turn(found, turn.kind, curve[found]))
    return _enforce_alternation(refined)


def _censor(turns: list[_Turn], curve: list[Decimal | None]) -> list[_Turn]:
    ordered = _drop_endpoints(turns, len(curve))
    ordered = _drop_end_dominance(ordered, curve)
    ordered = _drop_short_cycles(ordered)
    ordered = _enforce_alternation(ordered)
    ordered = _drop_short_phases(ordered)
    return _enforce_alternation(ordered)


def _mean_absolute_change(series: list[Decimal | None], span: int) -> Decimal | None:
    changes: list[Decimal] = []
    for index in range(span, len(series)):
        current = series[index]
        prior = series[index - span]
        if current is None or prior is None:
            continue
        changes.append(abs(current - prior))
    if not changes:
        return None
    return sum(changes, Decimal(0)) / Decimal(len(changes))


def months_for_cyclical_dominance(
    levels: list[Decimal],
    trend_cycle: list[Decimal | None],
) -> int:
    """Smallest span where the Spencer change exceeds the irregular change, then confined."""
    irregular: list[Decimal | None] = []
    for level, trend in zip(levels, trend_cycle, strict=True):
        irregular.append(None if trend is None else level - trend)
    raw: int | None = None
    for span in range(1, 13):
        trend_change = _mean_absolute_change(trend_cycle, span)
        irregular_change = _mean_absolute_change(irregular, span)
        if trend_change is None or irregular_change is None:
            continue
        if trend_change > irregular_change:
            raw = span
            break
    if raw is None or raw >= 7:
        return MCD_CAP
    if raw <= 2:
        return MCD_FLOOR
    return raw


def date_spencer15_variant(
    levels: tuple[tuple[date, Decimal], ...] | list[tuple[date, Decimal]],
) -> Spencer15Dates:
    """Date specific-cycle peaks and troughs with the labelled variant."""
    ordered = tuple(sorted(levels, key=lambda item: item[0]))
    if len(ordered) < len(SPENCER_WEIGHTS) + MINIMUM_CYCLE_MONTHS:
        return Spencer15Dates((), (), MCD_FLOOR)
    periods = [item[0] for item in ordered]
    values = [item[1] for item in ordered]
    spencer_a = centred_spencer(values)
    adjusted = replace_extremes(values, spencer_a)
    spencer_b = centred_spencer(adjusted)
    ma12 = moving_average(adjusted, MA12_LAGS + MA12_LEADS + 1)
    ma_turns = _censor(_local_turns(ma12, LOCAL_RADIUS), ma12)
    ma_turns = _drop_crossovers(ma_turns, spencer_b, LOCAL_RADIUS)
    spencer_turns = _censor(_refine(ma_turns, spencer_b, LOCAL_RADIUS), spencer_b)
    mcd = months_for_cyclical_dominance(values, spencer_a)
    short_curve = moving_average(values, mcd)
    short_turns = _censor(_refine(spencer_turns, short_curve, LOCAL_RADIUS), short_curve)
    final_radius = max(FINAL_WINDOW_FLOOR, mcd)
    final_curve: list[Decimal | None] = list(values)
    final_turns = _censor(_refine(short_turns, final_curve, final_radius), final_curve)
    peaks = tuple(periods[turn.index] for turn in final_turns if turn.kind == "peak")
    troughs = tuple(periods[turn.index] for turn in final_turns if turn.kind == "trough")
    return Spencer15Dates(peaks, troughs, mcd)


def variant_implementation_hash() -> str:
    payload = "|".join(
        (
            BRY_BOSCHAN_SPENCER15_VARIANT,
            VARIANT_VERSION,
            ",".join(str(weight) for weight in SPENCER_WEIGHTS),
            str(SPENCER_DIVISOR),
            f"{MA12_LAGS}lags{MA12_LEADS}leads",
            "mcd=absolute-difference",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class BryBoschanSpencer15Method:
    method_id = BRY_BOSCHAN_SPENCER15_VARIANT
    method_version = VARIANT_VERSION

    def implementation_hash(self) -> str:
        return variant_implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (G17_DATASET_ID,)

    def parse_config(self, payload: dict[str, object]) -> BryBoschanSpencer15Config:
        return BryBoschanSpencer15Config.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, BryBoschanSpencer15Config):
            raise TypeError("expected BryBoschanSpencer15Config")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "spencer_divisor": str(SPENCER_DIVISOR),
                "ma12_lags": str(MA12_LAGS),
                "ma12_leads": str(MA12_LEADS),
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, BryBoschanSpencer15Config):
            raise TypeError("expected BryBoschanSpencer15Config")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "the stored G.17 file is a latest-revised file, not a vintage panel"
            )
        series = context.inputs_by_dataset.get(G17_DATASET_ID, {})
        points = tuple(
            G17InputPoint(observation=observation, collection_mode="live")
            for observation in series.values()
        )
        assessment = assess_g17_level_input(points)
        if (
            not assessment.eligible
            or assessment.sample_start is None
            or assessment.sample_end is None
        ):
            return _insufficient("; ".join(assessment.reasons) or "G.17 input is ineligible")
        chosen = [
            series[period]
            for period in sorted(series)
            if assessment.sample_start <= period <= assessment.sample_end
        ]
        dated = date_spencer15_variant(
            tuple(
                (observation.period_start, observation.decimal_value()) for observation in chosen
            ),
        )
        peaks = [item.isoformat() for item in dated.peaks]
        troughs = [item.isoformat() for item in dated.troughs]
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation={
                "variant_id": BRY_BOSCHAN_SPENCER15_VARIANT,
                "peaks": peaks,
                "troughs": troughs,
                "mcd_months": dated.mcd_months,
                "publication_allowed": PUBLICATION_ALLOWED,
                "spencer_citation": MACAULAY_CITATION,
                "ma12_citation": OTSU_CITATION,
                "not_a_fortran_replica": True,
            },
            observation_ids=tuple(observation.observation_id for observation in chosen),
            assumptions=(
                NOT_THE_1971_LISTING,
                "Spencer weights and the divisor 320 are Macaulay 1931, page 55.",
                "The twelve-month average dated at t uses t-6 through t+5.",
                "Months for cyclical dominance compare absolute differences.",
            ),
            limitations=(
                NOT_THE_1971_LISTING,
                "The 1971 volume still does not print these two constants.",
                "NBER reference-cycle overlap is not an acceptance test.",
                "publication_allowed stays false.",
            ),
            missing_reason=None,
            statistical_interpretation=(
                "Specific-cycle peaks and troughs in the industrial production index "
                "under the labelled Spencer-15 variant. This is not a reference-cycle date "
                "and not a forecast."
            ),
            causal_hypothesis=CAUSAL_HYPOTHESIS,
            investment_implication="no_action",
            narrative=(
                f"Spencer-15 variant dated {len(peaks)} peaks and {len(troughs)} troughs "
                "in industrial production. publication_allowed is false. "
                "This is not the 1971 listing."
            ),
        )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=(NOT_THE_1971_LISTING,),
        missing_reason=reason,
        statistical_interpretation="Dating was not completed.",
        causal_hypothesis="Unresolved because inputs were insufficient.",
        investment_implication="insufficient_evidence",
        narrative=f"Dating incomplete. Reason: {reason}",
    )


# NBER reference chronology, month of the turn, from the page cited above.
# The first printed trough has no preceding peak on that table.
NBER_REFERENCE_TURNS: tuple[tuple[Literal["peak", "trough"], date], ...] = (
    ("trough", date(1854, 12, 1)),
    ("peak", date(1857, 6, 1)),
    ("trough", date(1858, 12, 1)),
    ("peak", date(1860, 10, 1)),
    ("trough", date(1861, 6, 1)),
    ("peak", date(1865, 4, 1)),
    ("trough", date(1867, 12, 1)),
    ("peak", date(1869, 6, 1)),
    ("trough", date(1870, 12, 1)),
    ("peak", date(1873, 10, 1)),
    ("trough", date(1879, 3, 1)),
    ("peak", date(1882, 3, 1)),
    ("trough", date(1885, 5, 1)),
    ("peak", date(1887, 3, 1)),
    ("trough", date(1888, 4, 1)),
    ("peak", date(1890, 7, 1)),
    ("trough", date(1891, 5, 1)),
    ("peak", date(1893, 1, 1)),
    ("trough", date(1894, 6, 1)),
    ("peak", date(1895, 12, 1)),
    ("trough", date(1897, 6, 1)),
    ("peak", date(1899, 6, 1)),
    ("trough", date(1900, 12, 1)),
    ("peak", date(1902, 9, 1)),
    ("trough", date(1904, 8, 1)),
    ("peak", date(1907, 5, 1)),
    ("trough", date(1908, 6, 1)),
    ("peak", date(1910, 1, 1)),
    ("trough", date(1912, 1, 1)),
    ("peak", date(1913, 1, 1)),
    ("trough", date(1914, 12, 1)),
    ("peak", date(1918, 8, 1)),
    ("trough", date(1919, 3, 1)),
    ("peak", date(1920, 1, 1)),
    ("trough", date(1921, 7, 1)),
    ("peak", date(1923, 5, 1)),
    ("trough", date(1924, 7, 1)),
    ("peak", date(1926, 10, 1)),
    ("trough", date(1927, 11, 1)),
    ("peak", date(1929, 8, 1)),
    ("trough", date(1933, 3, 1)),
    ("peak", date(1937, 5, 1)),
    ("trough", date(1938, 6, 1)),
    ("peak", date(1945, 2, 1)),
    ("trough", date(1945, 10, 1)),
    ("peak", date(1948, 11, 1)),
    ("trough", date(1949, 10, 1)),
    ("peak", date(1953, 7, 1)),
    ("trough", date(1954, 5, 1)),
    ("peak", date(1957, 8, 1)),
    ("trough", date(1958, 4, 1)),
    ("peak", date(1960, 4, 1)),
    ("trough", date(1961, 2, 1)),
    ("peak", date(1969, 12, 1)),
    ("trough", date(1970, 11, 1)),
    ("peak", date(1973, 11, 1)),
    ("trough", date(1975, 3, 1)),
    ("peak", date(1980, 1, 1)),
    ("trough", date(1980, 7, 1)),
    ("peak", date(1981, 7, 1)),
    ("trough", date(1982, 11, 1)),
    ("peak", date(1990, 7, 1)),
    ("trough", date(1991, 3, 1)),
    ("peak", date(2001, 3, 1)),
    ("trough", date(2001, 11, 1)),
    ("peak", date(2007, 12, 1)),
    ("trough", date(2009, 6, 1)),
    ("peak", date(2020, 2, 1)),
    ("trough", date(2020, 4, 1)),
)


def _month_gap(left: date, right: date) -> int:
    return abs((left.year - right.year) * 12 + (left.month - right.month))


def nber_reference_diagnostic(
    peaks: tuple[date, ...] | list[date],
    troughs: tuple[date, ...] | list[date],
    *,
    window_months: int = 6,
) -> dict[str, object]:
    """Compare specific-cycle dates with the reference chronology.

    A near date is not mathematical proof and is not an exact-match test.
    """
    reference_peaks = tuple(item[1] for item in NBER_REFERENCE_TURNS if item[0] == "peak")
    reference_troughs = tuple(item[1] for item in NBER_REFERENCE_TURNS if item[0] == "trough")

    def rows(
        specific: tuple[date, ...] | list[date], reference: tuple[date, ...]
    ) -> list[dict[str, object]]:
        table: list[dict[str, object]] = []
        for item in specific:
            if not reference:
                table.append(
                    {
                        "specific": item.isoformat(),
                        "nearest": None,
                        "gap_months": None,
                        "within_window": False,
                    }
                )
                continue
            nearest = min(reference, key=lambda candidate: _month_gap(item, candidate))
            gap = _month_gap(item, nearest)
            table.append(
                {
                    "specific": item.isoformat(),
                    "nearest": nearest.isoformat(),
                    "gap_months": gap,
                    "within_window": gap <= window_months,
                },
            )
        return table

    peak_rows = rows(peaks, reference_peaks)
    trough_rows = rows(troughs, reference_troughs)
    return {
        "citation": NBER_CHRONOLOGY_CITATION,
        "window_months": window_months,
        "peaks": peak_rows,
        "troughs": trough_rows,
        "within_window_count": sum(1 for row in (*peak_rows, *trough_rows) if row["within_window"]),
        "statement": (
            "Overlap with the NBER reference chronology is not mathematical proof "
            "and is not an exact-match acceptance test."
        ),
        "gates_the_method": False,
    }


@dataclass(frozen=True, slots=True)
class HealthFinding:
    code: str
    failed: bool
    detail: str


def assess_spencer15_health(
    *,
    months: tuple[date, ...],
    evaluation_period: date,
    peaks: tuple[date, ...],
    troughs: tuple[date, ...],
    collection_modes: tuple[str, ...],
    replay_matches: bool,
    publication_allowed: bool,
) -> tuple[HealthFinding, ...]:
    """Health fails on a gap, a rule breach, a replay mismatch, or a fixture row.

    Disagreement with the NBER chronology is recorded and does not fail health.
    """
    ordered = tuple(sorted(months))
    missing = not ordered or ordered[-1] != evaluation_period
    if not missing and len(ordered) > 1:
        for prior, current in zip(ordered, ordered[1:], strict=False):
            gap = (current.year - prior.year) * 12 + (current.month - prior.month)
            if gap != 1:
                missing = True
                break
    rule_failed = publication_allowed
    rule_detail = (
        "publication_allowed must stay false"
        if publication_allowed
        else "phase and cycle rules hold"
    )
    combined = sorted(
        [("peak", item) for item in peaks] + [("trough", item) for item in troughs],
        key=lambda item: item[1],
    )
    if ordered:
        first = ordered[0]
        last = ordered[-1]
        for _kind, turn in combined:
            if (
                _month_gap(turn, first) < ENDPOINT_BAN_MONTHS
                or _month_gap(turn, last) < ENDPOINT_BAN_MONTHS
            ):
                rule_failed = True
                rule_detail = "a turn is inside the six-month endpoint ban"
        for index in range(len(combined) - 1):
            gap = _month_gap(combined[index][1], combined[index + 1][1])
            if gap < MINIMUM_PHASE_MONTHS:
                rule_failed = True
                rule_detail = "a phase is shorter than five months"
        for index in range(len(combined)):
            for later in range(index + 1, len(combined)):
                if combined[index][0] != combined[later][0]:
                    continue
                if _month_gap(combined[index][1], combined[later][1]) < MINIMUM_CYCLE_MONTHS:
                    rule_failed = True
                    rule_detail = "like turns are closer than fifteen months"
                break
    fixture = any(mode == "fixture" for mode in collection_modes)
    diagnostic = nber_reference_diagnostic(peaks, troughs)
    return (
        HealthFinding(
            "missing_latest_month",
            missing,
            "the monthly index does not reach the evaluation month without a gap"
            if missing
            else "the monthly index reaches the evaluation month",
        ),
        HealthFinding("rule_breach", rule_failed, rule_detail),
        HealthFinding(
            "replay_mismatch",
            not replay_matches,
            "replay does not match the stored dates" if not replay_matches else "replay matches",
        ),
        HealthFinding(
            "fixture_rows",
            fixture,
            "a fixture row is included" if fixture else "no fixture row is included",
        ),
        HealthFinding(
            "nber_disagreement",
            False,
            str(diagnostic["statement"]),
        ),
    )
