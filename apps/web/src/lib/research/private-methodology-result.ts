/**
 * Read a stored calculation for a signed-in methodologies page.
 *
 * publication_allowed is not this gate. A false flag still withholds the
 * result from publication. This module only shapes a payload the page has
 * already loaded for an authenticated reader. It does not invent figures.
 */

export type StoredMethodologyRun = {
  runId: string;
  methodId: string;
  methodVersion: string;
  executedAt: string;
  executionStatus: string;
  publicationAllowed: boolean;
  dataSufficiency: string;
  analysisMode: string;
  primaryDatasetId: string;
  missingDataReason: string | null;
  statisticalInterpretation: string;
  limitations: readonly string[];
  calculation: Record<string, unknown> | null;
};

export type PrivateFact = {
  label: string;
  value: string;
};

export type PrivateSeriesPoint = {
  period: string;
  value: number;
};

export type PrivateSeries = {
  label: string;
  caption: string;
  unit: string;
  frequency: "monthly";
  points: PrivateSeriesPoint[];
};

export type PrivateDateMark = {
  kind: "Peak" | "Trough";
  period: string;
  series?: string;
};

export type PrivateMethodologyResult = {
  runId: string;
  methodId: string;
  methodVersion: string;
  executedAt: string;
  publicationAllowed: boolean;
  analysisMode: string;
  headline: string;
  standing: string;
  facts: readonly PrivateFact[];
  series: PrivateSeries | null;
  dates: readonly PrivateDateMark[];
  limitations: readonly string[];
  diagnostic: string | null;
};

export type DisplaySelection = {
  display: StoredMethodologyRun | null;
  unadoptedReestimate: StoredMethodologyRun | null;
};

const MODERN_REFIT = "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT";

const DAY = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

export function selectDisplayRun(runs: readonly StoredMethodologyRun[]): DisplaySelection {
  const modern = runs.filter((run) => run.methodId === MODERN_REFIT);
  if (modern.length > 0) {
    const unadopted = modern
      .filter((run) => run.calculation?.adopted_parameter_version === false)
      .sort((left, right) => Date.parse(right.executedAt) - Date.parse(left.executedAt));
    const adopted = modern
      .filter(
        (run) =>
          adoptedParameterVersion(run.calculation) &&
          run.executionStatus === "completed" &&
          Array.isArray(run.calculation?.filtered_factor),
      )
      .sort((left, right) => Date.parse(left.executedAt) - Date.parse(right.executedAt));
    const preservedId = text(unadopted[0]?.calculation?.preserved_run_id);
    const preserved = (preservedId ? adopted.find((run) => run.runId === preservedId) : null) ?? adopted[0] ?? null;
    if (preserved) return { display: preserved, unadoptedReestimate: unadopted[0] ?? null };
    return { display: unadopted[0] ?? null, unadoptedReestimate: null };
  }
  const completed = runs
    .filter((run) => run.executionStatus === "completed" && run.calculation)
    .sort((left, right) => Date.parse(right.executedAt) - Date.parse(left.executedAt));
  if (completed[0]) return { display: completed[0], unadoptedReestimate: null };
  const latest = [...runs].sort((left, right) => Date.parse(right.executedAt) - Date.parse(left.executedAt))[0] ?? null;
  return { display: latest, unadoptedReestimate: null };
}

export function extractPrivateResult(
  run: StoredMethodologyRun,
  unadoptedReestimate: StoredMethodologyRun | null = null,
): PrivateMethodologyResult {
  const calculation = run.calculation;
  const base = shell(run);
  if (!calculation || run.dataSufficiency === "insufficient" || run.executionStatus.startsWith("failed")) {
    return {
      ...base,
      headline: "The stored run did not produce a calculation.",
      standing: "This is a diagnostic, not an operational assessment. Not approved for publication.",
      diagnostic: (run.missingDataReason ?? run.statisticalInterpretation) || "No calculation was stored.",
    };
  }
  const specific = extractByMethod(run, calculation, unadoptedReestimate);
  return { ...base, ...specific, limitations: uniqueLimitations(run, specific.limitations ?? []) };
}

function adoptedParameterVersion(calculation: Record<string, unknown> | null): boolean {
  if (!calculation || !("loadings_ip_income_sales_payroll" in calculation)) return false;
  return calculation.adopted_parameter_version !== false;
}

function shell(run: StoredMethodologyRun): PrivateMethodologyResult {
  return {
    runId: run.runId,
    methodId: run.methodId,
    methodVersion: run.methodVersion,
    executedAt: run.executedAt,
    publicationAllowed: run.publicationAllowed,
    analysisMode: run.analysisMode,
    headline: "",
    standing: publicationStanding(run.publicationAllowed),
    facts: [],
    series: null,
    dates: [],
    limitations: run.limitations,
    diagnostic: null,
  };
}

function extractByMethod(
  run: StoredMethodologyRun,
  calculation: Record<string, unknown>,
  unadopted: StoredMethodologyRun | null,
): Partial<PrivateMethodologyResult> {
  switch (run.methodId) {
    case "BRY_BOSCHAN_SPENCER15_VARIANT":
      return bryBoschan(calculation, run);
    case MODERN_REFIT:
      return stockWatson(calculation, run, unadopted);
    case "RESTRICTED_COINCIDENT_DIFFUSION":
      return diffusion(calculation, run);
    case "HARDING_PAGAN_CHARACTERISTICS":
      return hardingPagan(calculation, run);
    case "HAMILTON_MONTHLY_REGIME_SWITCHING":
      return hamilton(calculation, run);
    case "BAI_PERRON_MEAN_SHIFTS":
      return baiPerron(calculation, run);
    case "AUTOREGRESSIVE_BENCHMARK":
      return autoregression(calculation, run);
    case "LEAD_LAG_CROSS_CORRELATION":
      return leadLag(calculation, run);
    case "SAHM_UNEMPLOYMENT_GAP":
      return sahm(calculation, run);
    default:
      return {
        headline: "A stored run exists. This page has no reader for that calculation.",
        standing: `${publicationStanding(run.publicationAllowed)} No figure is invented for ${run.methodId}.`,
        diagnostic: run.statisticalInterpretation || null,
      };
  }
}

function bryBoschan(
  calculation: Record<string, unknown>,
  run: StoredMethodologyRun,
): Partial<PrivateMethodologyResult> {
  const peaks = stringList(calculation.peaks);
  const troughs = stringList(calculation.troughs);
  const chronology = text(calculation.chronology_class) ?? "not recorded on this payload";
  return {
    headline: `${countNoun(peaks.length, "peak", "peaks")} and ${countNoun(troughs.length, "trough", "troughs")} are stored.`,
    standing:
      "Labelled Spencer-15 variant. Retrospective full sample on latest-revised data. Not the 1971 programme listing, not a FORTRAN reproduction, and not a contemporaneous recession call. Not approved for publication.",
    facts: [
      fact("Variant", text(calculation.variant_id) ?? run.methodId),
      fact("Chronology", chronology),
      fact("Months for cyclical dominance", figureOrText(calculation.mcd_months)),
      fact("Sample", vintageFact(run, calculation)),
      fact("Peaks", String(peaks.length)),
      fact("Troughs", String(troughs.length)),
    ],
    dates: [
      ...peaks.map((period) => ({ kind: "Peak" as const, period })),
      ...troughs.map((period) => ({ kind: "Trough" as const, period })),
    ],
    limitations: [
      "The centred Spencer smoother means these dates are not a call that could have been made at the time.",
      "Revision sensitivity stays blocked on latest-revised inputs.",
    ],
  };
}

function stockWatson(
  calculation: Record<string, unknown>,
  run: StoredMethodologyRun,
  unadopted: StoredMethodologyRun | null,
): Partial<PrivateMethodologyResult> {
  const adopted = calculation.adopted_parameter_version !== false;
  const growthStart = text(calculation.growth_start);
  const smootherStored = Array.isArray(calculation.smoothed_factor) && calculation.smoothed_factor.length > 0;
  const filtered = growthStart
    ? monthlyPath(
        growthStart,
        calculation.filtered_factor,
        "Filtered coincident factor",
        smootherStored
          ? "Filtered factor from the preserved parameter version. Smoothed values are stored separately and are not plotted. Latest revised, not a real-time vintage."
          : "Filtered factor from the preserved parameter version. This stored run has no smoother. Latest revised, not a real-time vintage.",
        "Filtered factor",
      )
    : null;
  const loadings = numberList(calculation.loadings_ip_income_sales_payroll);
  const likelihood = num(calculation.log_likelihood);
  const facts: PrivateFact[] = [
    fact("Parameter version", adopted ? "Preserved. The later re-estimate was not adopted." : "Not adopted."),
    fact("Operationally accepted", calculation.operationally_accepted === true ? "Yes" : "No"),
    fact("Log likelihood", likelihood === null ? "Not stored" : formatFigure(likelihood, 4)),
    fact("Loadings", loadings.length === 4 ? loadings.map((value) => formatFigure(value, 3)).join(", ") : "Not stored"),
    fact("Sample", sampleRange(calculation.sample_levels)),
    fact("Inputs", vintageFact(run, calculation)),
  ];
  let diagnostic: string | null = null;
  if (unadopted?.calculation && adopted) {
    const other = unadopted.calculation;
    const otherLikelihood = num(other.log_likelihood);
    const gain =
      likelihood !== null && otherLikelihood !== null ? otherLikelihood - likelihood : null;
    facts.push(
      fact("Re-estimate", unadopted.runId),
      fact("Re-estimate adopted", "No"),
      fact(
        "Likelihood difference",
        gain === null ? "Not stored" : formatFigure(gain, 6),
      ),
      fact("Re-estimate gradient norm", smallFigure(other.gradient_norm)),
      fact("Wider-step gradient norm", smallFigure(other.gradient_norm_wide_step)),
    );
    diagnostic =
      "A small likelihood gain does not replace the preserved parameters. The chart uses the preserved filtered factor.";
  }
  if (!adopted) {
    return {
      headline: "The re-estimate is stored and was not adopted as the parameter version.",
      standing:
        "Not operationally accepted. Not a GDP nowcast. The 1988 payroll panel remains blocked. Not approved for publication.",
      facts,
      series: null,
      diagnostic:
        diagnostic ??
        "No preserved filtered path was selected. The unadopted re-estimate is not plotted as the factor.",
    };
  }
  const last = filtered?.points[filtered.points.length - 1];
  return {
    headline: last
      ? `Filtered factor ${formatFigure(last.value, 3)} in ${formatDay(last.period)}.`
      : "The preserved filtered factor is stored.",
    standing:
      "Not operationally accepted. Filtered values are not smoothed values. Latest revised is not real-time. Not a GDP nowcast. The 1988 payroll specification remains blocked. Not approved for publication.",
    facts,
    series: filtered,
    diagnostic,
    limitations: [
      "Static principal components are not this factor.",
      "The filtered path uses parameters estimated on the full revised sample.",
    ],
  };
}

function diffusion(
  calculation: Record<string, unknown>,
  run: StoredMethodologyRun,
): Partial<PrivateMethodologyResult> {
  const months = Array.isArray(calculation.months) ? calculation.months : [];
  const points: PrivateSeriesPoint[] = [];
  for (const month of months) {
    if (!isRecord(month)) continue;
    const period = text(month.period);
    const value = num(month.share);
    if (period && value !== null) points.push({ period, value });
  }
  const last = points[points.length - 1];
  const correlation = num(calculation.correlation_with_stock_watson_filtered_factor);
  return {
    headline: last
      ? `Diffusion share ${formatFigure(last.value, 3)} in ${formatDay(last.period)}.`
      : "The restricted diffusion share is stored.",
    standing:
      "Experimental breadth statistic. Not the Chicago Fed index and not a dynamic factor. A correlation with the factor is not independent confirmation. Not approved for publication.",
    facts: [
      fact("Change", "Three-month arithmetic change in the level"),
      fact("Improvement", "Strictly positive change"),
      fact("Balanced sample", `${formatMaybeDay(calculation.balanced_start)} to ${formatMaybeDay(calculation.balanced_end)}`),
      fact("Inputs", vintageFact(run, calculation)),
      fact(
        "Correlation with the preserved filtered factor",
        correlation === null ? "Not stored on this run" : formatFigure(correlation, 3),
      ),
    ],
    series:
      points.length >= 2
        ? {
            label: "Restricted diffusion share",
            caption:
              "Share of the four series whose level rose over three months. No interpolation. Latest revised, not a real-time vintage.",
            unit: "Share",
            frequency: "monthly",
            points,
          }
        : null,
    limitations: ["Unemployment is not in this measure."],
  };
}

function hardingPagan(
  calculation: Record<string, unknown>,
  run: StoredMethodologyRun,
): Partial<PrivateMethodologyResult> {
  const series = Array.isArray(calculation.series) ? calculation.series.filter(isRecord) : [];
  const pairs = Array.isArray(calculation.concordance) ? calculation.concordance.filter(isRecord) : [];
  const facts: PrivateFact[] = [
    fact("Dating", text(calculation.dating_method) ?? "Spencer-15"),
    fact("Chronology", text(calculation.chronology_class) ?? run.analysisMode),
    fact("Quarterly BBQ", calculation.quarterly_bbq_implemented === true ? "Implemented" : "Not implemented"),
    fact("Inputs", vintageFact(run, calculation)),
  ];
  for (const row of series) {
    const label = text(row.series_label) ?? text(row.dataset_id) ?? "Series";
    if (row.dated !== true && row.eligible !== true) {
      facts.push(fact(label, "Not dated"));
      continue;
    }
    facts.push(
      fact(
        label,
        `${figureOrText(row.peak_count)} peaks, ${figureOrText(row.trough_count)} troughs`,
      ),
    );
  }
  const dates: PrivateDateMark[] = [];
  for (const row of series) {
    const label = text(row.series_label) ?? "";
    if (!/industrial production/i.test(label)) continue;
    for (const period of stringList(row.peaks)) dates.push({ kind: "Peak", period, series: label });
    for (const period of stringList(row.troughs)) dates.push({ kind: "Trough", period, series: label });
  }
  const concordances: number[] = [];
  for (const pair of pairs) {
    if (pair.computed !== true) continue;
    const value = num(pair.concordance);
    const left = text(pair.left_label) ?? "Series";
    const right = text(pair.right_label) ?? "Series";
    facts.push(fact(`Concordance, ${left} and ${right}`, value === null ? "Not stored" : formatFigure(value, 3)));
    if (value !== null) concordances.push(value);
  }
  return {
    headline: concordances.length
      ? `Pairwise concordance from ${formatFigure(Math.min(...concordances), 3)} to ${formatFigure(Math.max(...concordances), 3)}.`
      : "Phase, amplitude, and concordance are stored from Spencer-15 dates.",
    standing:
      "Characteristics of specific cycles. Not quarterly BBQ and not an NBER recession chronology. Payroll, income, and sales turns are not NBER recessions. Not approved for publication.",
    facts,
    limitations: [
      text(calculation.phase_rule) ?? "Phase follows the stored Spencer-15 turns.",
      "Quarterly BBQ was not run on monthly industrial production.",
    ],
    dates,
  };
}

function hamilton(
  calculation: Record<string, unknown>,
  run: StoredMethodologyRun,
): Partial<PrivateMethodologyResult> {
  const durations = isRecord(calculation.expected_regime_durations_months)
    ? calculation.expected_regime_durations_months
    : {};
  const lower = num(durations.lower_mean);
  const sample = isRecord(calculation.sample) ? calculation.sample : {};
  const lag = isRecord(calculation.lag_selection) ? calculation.lag_selection.chosen_lag : null;
  const points = probabilityPath(calculation.filtered_regime_probabilities);
  const alternative = isRecord(calculation.minimum_duration_alternative)
    ? calculation.minimum_duration_alternative
    : null;
  const last = points[points.length - 1];
  return {
    headline: last
      ? `Filtered lower-mean probability ${formatFigure(last.value, 3)} in ${formatDay(last.period)}.`
      : "Filtered and smoothed probabilities are stored separately.",
    standing:
      "Experimental monthly variant. Not empirically qualified and not a recession label. Not Hamilton 1989 quarterly GNP. Not approved for publication.",
    facts: [
      fact("Chosen lag", figureOrText(lag)),
      fact("Lower-mean expected duration", lower === null ? "Not stored" : `${formatFigure(lower, 3)} months`),
      fact("Higher-mean expected duration", figureOrText(durations.higher_mean, " months")),
      fact("Empirically qualified", calculation.empirically_qualified === true ? "Yes" : "No"),
      fact("Operational", calculation.operational === true ? "Yes" : "No"),
      fact("Modelled sample", `${formatMaybeDay(sample.modelled_start)} to ${formatMaybeDay(sample.modelled_end)}`),
      fact("Inputs", vintageFact(run, calculation)),
    ],
    series:
      points.length >= 2
        ? {
            label: "Filtered lower-mean probability",
            caption:
              "Filtered probability of the lower-mean regime. Smoothed probabilities are stored separately and are not plotted. The parameters use the full revised sample, so this is not a real-time path.",
            unit: "Probability",
            frequency: "monthly",
            points,
          }
        : null,
    diagnostic: alternative ? text(alternative.reason) : null,
    limitations: [
      lower !== null && lower < 6
        ? `The stored lower-mean expected duration is ${formatFigure(lower, 3)} months. That is not a recession label.`
        : "The lower-mean regime is not labelled as a recession.",
      "Filtered and smoothed probabilities answer different questions.",
    ],
  };
}

function baiPerron(
  calculation: Record<string, unknown>,
  run: StoredMethodologyRun,
): Partial<PrivateMethodologyResult> {
  const count = num(calculation.break_count);
  const sensitivity = isRecord(calculation.trimming_sensitivity) ? calculation.trimming_sensitivity : {};
  const alternatives = Array.isArray(sensitivity.alternatives) ? sensitivity.alternatives.filter(isRecord) : [];
  const facts: PrivateFact[] = [
    fact("Selected break count", count === null ? "Not stored" : String(count)),
    fact("Primary trim", figureOrText(calculation.minimum_segment_length, " months")),
    fact("Date status", text(calculation.date_status) ?? "Point estimates only"),
    fact("Inputs", vintageFact(run, calculation)),
    fact("Sample", `${formatMaybeDay(calculation.log_growth_sample_start)} to ${formatMaybeDay(calculation.log_growth_sample_end)}`),
  ];
  for (const alternative of alternatives) {
    facts.push(
      fact(
        `Sensitivity, ${text(alternative.label) ?? "alternative trim"}`,
        `${figureOrText(alternative.break_count)} breaks`,
      ),
    );
  }
  return {
    headline:
      count === 0
        ? "The primary trimming rule selected no break."
        : count === null
          ? "The mean-shift search is stored."
          : `The primary trimming rule selected ${count} breaks.`,
    standing:
      "The primary specification is the result. Trimming sensitivity is not a second selected model. Dates are point estimates. Not the general regressor model. Not approved for publication.",
    facts,
    diagnostic: text(sensitivity.note),
    limitations: ["A looser trim is shown as sensitivity only."],
  };
}

function autoregression(
  calculation: Record<string, unknown>,
  run: StoredMethodologyRun,
): Partial<PrivateMethodologyResult> {
  const horizons = Array.isArray(calculation.horizons) ? calculation.horizons.filter(isRecord) : [];
  const facts: PrivateFact[] = [
    fact("AIC lag", figureOrText(calculation.in_sample_aic_lag)),
    fact("Qualified forecast", calculation.empirically_qualified_as_forecast === true ? "Yes" : "No"),
    fact("Inputs", vintageFact(run, calculation)),
    fact("Growth months", figureOrText(calculation.growth_month_count)),
  ];
  for (const horizon of horizons) {
    const months = figureOrText(horizon.horizon_months);
    const beat = horizon.beat_historical_mean === true ? "Beat the historical mean" : "Did not beat the historical mean";
    facts.push(fact(`Horizon ${months} months`, beat));
  }
  const twelve = horizons.find((horizon) => num(horizon.horizon_months) === 12);
  return {
    headline:
      twelve && twelve.beat_historical_mean !== true
        ? "The twelve-month horizon did not beat the historical mean."
        : "The autoregressive comparison is stored.",
    standing:
      "This is a benchmark, not a qualified forecast. Beating the mean at one horizon does not qualify the method. Not approved for publication.",
    facts,
    diagnostic: text(calculation.qualification_statement),
  };
}

function leadLag(
  calculation: Record<string, unknown>,
  run: StoredMethodologyRun,
): Partial<PrivateMethodologyResult> {
  const pairs = Array.isArray(calculation.pairs) ? calculation.pairs.filter(isRecord) : [];
  const facts: PrivateFact[] = [
    fact("Inputs", vintageFact(run, calculation)),
    fact("Growth sample", `${formatMaybeDay(calculation.growth_start)} to ${formatMaybeDay(calculation.growth_end)}`),
    fact("Leading indicator assigned", calculation.fixed_leading_indicator_assigned === true ? "Yes" : "No"),
  ];
  let contemporaneous = 0;
  let unstable = 0;
  for (const pair of pairs) {
    const peak = isRecord(pair.strongest_absolute_correlation) ? pair.strongest_absolute_correlation : null;
    const left = text(pair.first_label) ?? text(pair.first_dataset_id) ?? "Series";
    const right = text(pair.second_label) ?? text(pair.second_dataset_id) ?? "Series";
    const lag = peak ? num(peak.lag) : null;
    const correlation = peak ? num(peak.correlation) : null;
    if (lag === 0) contemporaneous += 1;
    if (pair.same_peak_lag_in_both_subsamples !== true) unstable += 1;
    facts.push(
      fact(
        `${left} and ${right}`,
        peak
          ? `Strongest lag ${lag ?? "not stored"}, correlation ${correlation === null ? "not stored" : formatFigure(correlation, 3)}`
          : "No peak stored",
      ),
    );
  }
  return {
    headline:
      pairs.length > 0
        ? `${contemporaneous} of ${pairs.length} strongest correlations are contemporaneous. ${unstable} are not stable across the predeclared subsamples.`
        : "The cross-correlations are stored.",
    standing:
      "Descriptive diagnostic. Unstable contemporaneous correlations are not a leading-indicator assignment. Not approved for publication.",
    facts,
    limitations: ["A correlation is not a structural lead."],
  };
}

function sahm(
  calculation: Record<string, unknown>,
  run: StoredMethodologyRun,
): Partial<PrivateMethodologyResult> {
  const gap = num(calculation.gap_percentage_points);
  const triggered = calculation.triggered === true;
  const period = text(calculation.evaluation_period);
  return {
    headline: period
      ? `${formatDay(period)} gap ${gap === null ? "not stored" : formatFigure(gap, 2)} percentage points. ${triggered ? "Triggered" : "Not triggered"}.`
      : "The Sahm gap is stored.",
    standing:
      "Short live sample on latest-revised unemployment. Not a long-history comparison and not the real-time Sahm series. October 2025 is not interpolated. Not approved for publication.",
    facts: [
      fact("Three-month average", figureOrText(calculation.three_month_average, "%")),
      fact("Prior twelve-month low", figureOrText(calculation.prior_twelve_month_low_of_average, "%")),
      fact("Gap", gap === null ? "Not stored" : `${formatFigure(gap, 2)} percentage points`),
      fact("Threshold", figureOrText(calculation.threshold_percentage_points, " percentage points")),
      fact("Triggered", triggered ? "Yes" : "No"),
      fact("Inputs", vintageFact(run, calculation)),
    ],
    limitations: [
      ...stringList(calculation.limitations),
      "This stored run is one evaluation month, so there is no gap path to plot. October 2025 is not interpolated.",
    ],
  };
}

function monthlyPath(
  start: string,
  values: unknown,
  label: string,
  caption: string,
  unit: string,
): PrivateSeries | null {
  if (!Array.isArray(values) || values.length < 2) return null;
  const points: PrivateSeriesPoint[] = [];
  for (let index = 0; index < values.length; index += 1) {
    const value = num(values[index]);
    if (value === null) return null;
    points.push({ period: addMonths(start, index), value });
  }
  return { label, caption, unit, frequency: "monthly", points };
}

function probabilityPath(value: unknown): PrivateSeriesPoint[] {
  if (!Array.isArray(value)) return [];
  const points: PrivateSeriesPoint[] = [];
  for (const row of value) {
    if (!isRecord(row)) continue;
    const period = text(row.period);
    const probability = num(row.lower_mean);
    if (period && probability !== null) points.push({ period, value: probability });
  }
  return points;
}

function vintageFact(run: StoredMethodologyRun, calculation: Record<string, unknown>): string {
  const vintage = text(calculation.input_vintage) ?? text(calculation.revision) ?? run.analysisMode;
  if (vintage === "latest_revised") return "Latest revised. Not a real-time vintage.";
  if (calculation.real_time === false || calculation.real_time_assessment === false) {
    return `${vintage}. Not a real-time assessment.`;
  }
  return vintage;
}

function sampleRange(value: unknown): string {
  if (!Array.isArray(value) || value.length < 2) return "Not stored";
  return `${formatMaybeDay(value[0])} to ${formatMaybeDay(value[1])}`;
}

function publicationStanding(publicationAllowed: boolean): string {
  return publicationAllowed
    ? "This run is marked approved for publication."
    : "Not approved for publication.";
}

function uniqueLimitations(run: StoredMethodologyRun, extra: readonly string[]): string[] {
  const seen = new Set<string>();
  const lines: string[] = [];
  for (const line of [...extra, ...run.limitations]) {
    const trimmed = line.trim();
    if (!trimmed || seen.has(trimmed)) continue;
    seen.add(trimmed);
    lines.push(trimmed);
  }
  if (!run.publicationAllowed) lines.push("Publication allowed is false.");
  if (run.analysisMode === "latest_revised") {
    lines.push("Latest revised history is not a real-time vintage.");
  }
  return lines;
}

function countNoun(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function fact(label: string, value: string): PrivateFact {
  return { label, value };
}

function smallFigure(value: unknown): string {
  const parsed = num(value);
  return parsed === null ? "Not stored" : formatFigure(parsed, 6);
}

function figureOrText(value: unknown, suffix = ""): string {
  const parsed = num(value);
  if (parsed !== null) return `${formatFigure(parsed, 4)}${suffix}`;
  const raw = text(value);
  return raw ? `${raw}${suffix}` : "Not stored";
}

export function formatFigure(value: number, digits: number): string {
  const magnitude = Math.abs(value);
  const places = magnitude > 0 && magnitude < 0.001 ? Math.max(digits, 6) : digits;
  return value.toLocaleString("en-GB", {
    maximumFractionDigits: places,
    minimumFractionDigits: 0,
  });
}

function formatMaybeDay(value: unknown): string {
  const raw = text(value);
  return raw ? formatDay(raw) : "Not stored";
}

function formatDay(iso: string): string {
  const when = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(when.getTime())) return iso;
  return DAY.format(when);
}

function addMonths(iso: string, months: number): string {
  const year = Number(iso.slice(0, 4));
  const month = Number(iso.slice(5, 7));
  const day = Number(iso.slice(8, 10));
  const date = new Date(Date.UTC(year, month - 1 + months, day));
  return date.toISOString().slice(0, 10);
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function numberList(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  const numbers: number[] = [];
  for (const item of value) {
    const parsed = num(item);
    if (parsed === null) return [];
    numbers.push(parsed);
  }
  return numbers;
}

function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && /^-?\d+(\.\d+)?$/.test(value.trim())) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
