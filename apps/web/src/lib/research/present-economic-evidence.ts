/**
 * Present stored macro-method results. This does not recompute a change,
 * rank, or spread, and it does not call a model.
 */

import { displayChange, displayLevel, type CountNoun } from "./format-indicator.ts";

export const ECONOMIC_READING_HEADING = "Economic reading";
export const UNANSWERED_HEADING = "Not answered from this evidence";
export const READING_INSUFFICIENT = "Insufficient evidence";
export const READING_STABLE = "Broadly stable";
export const READING_MIXED = "Mixed";
export const LATEST_REVISED_SENTENCE =
  "The file is latest revised and is not a vintage panel.";
export const THREE_MONTH_PAYROLL_NOTE =
  "Three-month payroll acceleration is not calculated.";
export const HICP_EXCLUSION =
  "Euro-area HICP is excluded from this reading and ends in December 2025.";
export const NOT_INVESTMENT_CONCLUSION =
  "An economic reading is not an investment conclusion.";
export const OVERALL_SENTENCE =
  "Every included family has a reading, and the stored synthesis does not report a divergence.";

export const UNANSWERED_QUESTIONS = [
  "Broad equity performance",
  "Regional relative performance",
  "Sector leadership",
  "Valuation",
  "Earnings revisions",
  "Credit spreads",
  "Benchmark total returns",
] as const;

const UNEMPLOYMENT_DATASET = "bls.ln.LNS14000000";
const PAYROLLS_DATASET = "bls.ce.CES0000000001";
const OPENINGS_DATASET = "bls.jt.JTS000000000000000JOL";

export const SERIES_SOURCE = {
  unemployment: "bls_cps_unemployment_rate",
  payrolls: "bls_ces_total_nonfarm_payrolls",
  openings: "bls_jolts_total_nonfarm_job_openings",
  cpi: "bls_cpi_u_all_items",
  production: "federal_reserve_g17_total_ip",
  sloos: "federal_reserve_sloos_cil",
  bankCredit: "federal_reserve_h8_bank_credit",
  funds: "federal_reserve_h15_federal_funds_effective",
  treasury: "federal_reserve_h15_treasury_10y_constant_maturity",
  hicp: "ecb_sdw_hicp_sa",
} as const;

const BLS_RELEASE: Record<string, string> = {
  [SERIES_SOURCE.unemployment]: "Employment Situation",
  [SERIES_SOURCE.payrolls]: "Employment Situation",
  [SERIES_SOURCE.cpi]: "Consumer Price Index",
  [SERIES_SOURCE.openings]: "Job Openings and Labor Turnover Survey",
};

const NO_DIVERGENCE = /no stored latest month diverges/i;

export type StoredMethodRun = {
  methodId: string;
  methodVersion: string;
  runId: string;
  payloadHash: string;
  dataSufficiency: string;
  missingDataReason: string | null;
  analysisMode: string | null;
  calculation: Record<string, unknown> | null;
  limitations: readonly string[];
};

export type EconomicEvidenceInput = {
  synthesis: StoredMethodRun | null;
  labour: StoredMethodRun | null;
  prices: StoredMethodRun | null;
  production: StoredMethodRun | null;
  credit: StoredMethodRun | null;
  blsCalendarSourceIds: readonly string[];
};

export type FamilyId = "labour" | "inflation" | "production" | "credit" | "rates";

export type FamilyBrief = {
  id: FamilyId;
  label: string;
  observation: string;
  trend: string;
  context: string;
  reading: string;
  contradiction: string;
  limitation: string;
  next: string;
  nextHref: "/calendar" | null;
};

export type SeriesReadingLine = {
  sourceId: string;
  compact: string;
};

export type EconomicEvidenceView = {
  methodId: string;
  methodVersion: string;
  runId: string | null;
  payloadHash: string | null;
  overall: string | null;
  families: FamilyBrief[];
  limitations: string[];
  seriesLines: SeriesReadingLine[];
  unansweredHeading: string;
  unanswered: readonly string[];
  unansweredNote: string;
  hicpNote: string;
};

type SeriesPiece = {
  sourceId: string;
  name: string;
  period: string | null;
  sign: -1 | 0 | 1 | null;
  observation: string;
  trend: string;
  says: string;
  rank: string | null;
};

type BuiltFamily = {
  brief: FamilyBrief;
  lines: SeriesReadingLine[];
};

export function presentEconomicEvidence(input: EconomicEvidenceInput): EconomicEvidenceView {
  const calendar = new Set(input.blsCalendarSourceIds);
  const synthesisCalc = usableCalculation(input.synthesis);
  const divergences = stringList(synthesisCalc?.divergences);
  const storedLimitations = synthesisLimitations(input.synthesis, synthesisCalc);
  const labour = presentLabour(input.labour, divergences, storedLimitations, calendar);
  const prices = presentPrices(input.prices, divergences, storedLimitations, calendar);
  const production = presentProduction(input.production, divergences, storedLimitations, calendar);
  const credit = presentCredit(input.credit, divergences, storedLimitations, calendar);
  const ordered = [labour.brief, prices.inflation, production.brief, credit.brief, prices.rates];
  return {
    methodId: input.synthesis?.methodId ?? "MACRO_READING_SYNTHESIS",
    methodVersion: input.synthesis?.methodVersion ?? "1.0.0",
    runId: input.synthesis?.runId ?? null,
    payloadHash: input.synthesis?.payloadHash || null,
    overall: overallSentence(ordered, divergences, input.synthesis),
    families: ordered,
    limitations: pageLimitations(input.synthesis, storedLimitations, divergences),
    seriesLines: [...labour.lines, ...prices.lines, ...production.lines, ...credit.lines, hicpLine()],
    unansweredHeading: UNANSWERED_HEADING,
    unanswered: UNANSWERED_QUESTIONS,
    unansweredNote: NOT_INVESTMENT_CONCLUSION,
    hicpNote: HICP_EXCLUSION,
  };
}

function presentLabour(
  run: StoredMethodRun | null,
  divergences: string[],
  limitations: string[],
  calendar: ReadonlySet<string>,
): BuiltFamily {
  const calculation = usableCalculation(run);
  const rows = Array.isArray(calculation?.series) ? calculation.series : [];
  const specs = [
    { datasetId: UNEMPLOYMENT_DATASET, sourceId: SERIES_SOURCE.unemployment, name: "Unemployment rate", kind: "points" as const },
    { datasetId: PAYROLLS_DATASET, sourceId: SERIES_SOURCE.payrolls, name: "Payrolls", kind: "jobs" as const, noun: "jobs" as const },
    { datasetId: OPENINGS_DATASET, sourceId: SERIES_SOURCE.openings, name: "Job openings", kind: "jobs" as const, noun: "openings" as const },
  ];
  const pieces: SeriesPiece[] = [];
  let missing = calculation === null;
  for (const spec of specs) {
    const row = rows.find((item) => isRecord(item) && item.dataset_id === spec.datasetId);
    const piece = spec.kind === "points"
      ? unemploymentPiece(isRecord(row) ? row : null)
      : countPiece(isRecord(row) ? row : null, spec.name, spec.sourceId, spec.noun);
    if (piece.sign === null) missing = true;
    pieces.push(piece);
  }
  const october = limitations.find((item) => /october 2025/i.test(item)) ?? null;
  return assemble({
    id: "labour",
    label: "Labour",
    pieces,
    missing,
    revised: revisedSentence(run),
    extraContext: [jointSentence(calculation?.joint)],
    extraLimitation: [
      periodsDiffer(pieces) ? "The labour series do not share one latest month." : null,
      THREE_MONTH_PAYROLL_NOTE,
      october,
    ],
    divergences,
    needles: ["unemployment", "payrolls", "job openings", "joint labour"],
    calendar,
    calendarSourceIds: [SERIES_SOURCE.unemployment, SERIES_SOURCE.payrolls, SERIES_SOURCE.openings],
  });
}

function presentPrices(
  run: StoredMethodRun | null,
  divergences: string[],
  limitations: string[],
  calendar: ReadonlySet<string>,
): { inflation: FamilyBrief; rates: FamilyBrief; lines: SeriesReadingLine[] } {
  const calculation = usableCalculation(run);
  const cpi = isRecord(calculation?.cpi_u) ? calculation.cpi_u : null;
  const funds = isRecord(calculation?.federal_funds) ? calculation.federal_funds : null;
  const treasury = isRecord(calculation?.treasury_10_year) ? calculation.treasury_10_year : null;
  const cpiPiece = cpiPieceFrom(cpi);
  const fundsPiece = ratePiece(funds, "Federal funds rate", SERIES_SOURCE.funds);
  const treasuryPiece = ratePiece(treasury, "10-year yield", SERIES_SOURCE.treasury);
  const october = limitations.find((item) => /cpi-u|october 2025/i.test(item)) ?? null;
  const inflation = assemble({
    id: "inflation",
    label: "Inflation",
    pieces: [cpiPiece],
    missing: calculation === null || cpiPiece.sign === null,
    revised: revisedSentence(run),
    extraContext: ["The 12-month percent change is not the index level."],
    extraLimitation: [october],
    divergences,
    needles: ["cpi-u", "cpi"],
    calendar,
    calendarSourceIds: [SERIES_SOURCE.cpi],
  });
  const seasonalUnknown = funds?.seasonal_adjustment === "unknown" || treasury?.seasonal_adjustment === "unknown";
  const rates = assemble({
    id: "rates",
    label: "Interest rates",
    pieces: [fundsPiece, treasuryPiece],
    missing: calculation === null || fundsPiece.sign === null || treasuryPiece.sign === null,
    revised: revisedSentence(run),
    extraContext: ["Interest rates stay separate from the CPI inflation rate."],
    extraLimitation: [seasonalUnknown ? "H.15 seasonal adjustment is unknown." : null],
    divergences,
    needles: ["federal funds", "10-year"],
    calendar,
    calendarSourceIds: [],
  });
  return { inflation: inflation.brief, rates: rates.brief, lines: [...inflation.lines, ...rates.lines] };
}

function presentProduction(
  run: StoredMethodRun | null,
  divergences: string[],
  limitations: string[],
  calendar: ReadonlySet<string>,
): BuiltFamily {
  const calculation = usableCalculation(run);
  const piece = productionPiece(calculation);
  const gdp = limitations.find((item) => /not a gdp figure/i.test(item)) ?? "Industrial production is not a GDP figure.";
  return assemble({
    id: "production",
    label: "Production",
    pieces: [piece],
    missing: calculation === null || piece.sign === null,
    revised: revisedSentence(run),
    extraContext: [],
    extraLimitation: [gdp],
    divergences,
    needles: ["industrial production"],
    calendar,
    calendarSourceIds: [],
  });
}

function presentCredit(
  run: StoredMethodRun | null,
  divergences: string[],
  limitations: string[],
  calendar: ReadonlySet<string>,
): BuiltFamily {
  const calculation = usableCalculation(run);
  const standards = isRecord(calculation?.lending_standards) ? calculation.lending_standards : null;
  const volume = isRecord(calculation?.bank_credit) ? calculation.bank_credit : null;
  const sloos = sloosPiece(standards);
  const bank = bankPiece(volume);
  const missingReason = text(volume?.missing_reason);
  const dollars = limitations.find((item) => /not converted into dollars/i.test(item)) ??
    "The survey share is not converted into dollars.";
  return assemble({
    id: "credit",
    label: "Credit",
    pieces: [sloos, bank],
    missing: calculation === null || sloos.sign === null || bank.sign === null,
    revised: revisedSentence(run),
    extraContext: [],
    extraLimitation: [
      sloos.period && bank.period && sloos.period !== bank.period
        ? "The SLOOS quarter and the bank-credit week are not the same period."
        : null,
      bank.sign === null ? missingReason ?? "The 52-week bank-credit change is missing." : null,
      dollars,
    ],
    divergences,
    needles: ["sloos", "bank credit"],
    calendar,
    calendarSourceIds: [],
  });
}

function assemble(input: {
  id: FamilyId;
  label: string;
  pieces: SeriesPiece[];
  missing: boolean;
  revised: string | null;
  extraContext: (string | null)[];
  extraLimitation: (string | null)[];
  divergences: string[];
  needles: string[];
  calendar: ReadonlySet<string>;
  calendarSourceIds: readonly string[];
}): BuiltFamily {
  const included = input.pieces.filter((piece) => piece.sign !== null) as (SeriesPiece & { sign: -1 | 0 | 1 })[];
  const reading = input.missing || included.length !== input.pieces.length ? READING_INSUFFICIENT : labelFor(included);
  const opposite = oppositeClause(included);
  const named = namedDivergences(input.divergences, input.needles);
  const contradiction = input.missing
    ? "A missing comparison endpoint is not read as a change."
    : [opposite, ...named].filter((item): item is string => Boolean(item)).join(" ") ||
      "Nothing stored in this family has the opposite sign.";
  const chartContradiction = input.missing
    ? "A missing comparison endpoint is not read as a change."
    : opposite ||
      (named.length > 0
        ? "The stored synthesis records a divergence that names this family."
        : "Nothing stored in this family has the opposite sign.");
  const next = nextRelease(input.calendarSourceIds, input.calendar);
  const context = [
    ...input.pieces.map((piece) => piece.rank).filter((item): item is string => Boolean(item)),
    ...input.extraContext.filter((item): item is string => Boolean(item)),
    input.revised,
  ].filter((item): item is string => Boolean(item)).join(" ");
  const limitation = input.extraLimitation.filter((item): item is string => Boolean(item)).join(" ") ||
    "No further limitation is stored for this family.";
  return {
    brief: {
      id: input.id,
      label: input.label,
      observation: input.pieces.map((piece) => piece.observation).join(" "),
      trend: input.pieces.map((piece) => `${piece.trend} ${piece.says}`.trim()).join(" "),
      context: context || LATEST_REVISED_SENTENCE,
      reading,
      contradiction,
      limitation,
      next: next.next,
      nextHref: next.nextHref,
    },
    lines: input.pieces.map((piece) => ({
      sourceId: piece.sourceId,
      compact: `${piece.observation} ${piece.trend} ${piece.says} ${chartContradiction}`,
    })),
  };
}

function labelFor(pieces: (SeriesPiece & { sign: -1 | 0 | 1 })[]): string {
  if (pieces.some((piece) => !piece.period)) return READING_INSUFFICIENT;
  const periods = new Set(pieces.map((piece) => piece.period));
  if (periods.size !== 1) return READING_MIXED;
  const signs = new Set(pieces.map((piece) => piece.sign));
  if (signs.size === 1 && signs.has(0)) return READING_STABLE;
  if (signs.size !== 1) return READING_MIXED;
  return pieces.map((piece) => piece.says).join(" ");
}

function unemploymentPiece(row: Record<string, unknown> | null): SeriesPiece {
  const change = isRecord(row?.twelve_month_change) ? row.twelve_month_change : null;
  const points = text(change?.change_percentage_points);
  const period = text(row?.latest_period);
  const level = text(row?.level);
  const sign = points === null ? null : signOf(points);
  const says = sign === null
    ? READING_INSUFFICIENT
    : sign === 0
      ? "The unemployment rate is unchanged over 12 months."
      : `The unemployment rate is ${sign > 0 ? "higher" : "lower"} than 12 months earlier.`;
  return {
    sourceId: SERIES_SOURCE.unemployment,
    name: "Unemployment rate",
    period,
    sign,
    observation: level && period
      ? `${monthLabel(period)}: unemployment ${levelPhrase(level, "percent")}.`
      : "Unemployment: the stored level is missing.",
    trend: points ? `Stored 12-month change: ${pointsPhrase(points)}.` : "The stored 12-month comparison endpoint is missing.",
    says,
    rank: rankPhrase(row, "unemployment rate"),
  };
}

function countPiece(row: Record<string, unknown> | null, name: string, sourceId: string, noun: CountNoun): SeriesPiece {
  const change = isRecord(row?.twelve_month_change) ? row.twelve_month_change : null;
  const jobs = text(change?.change_thousands);
  const percent = text(change?.percent_change);
  const period = text(row?.latest_period);
  const level = text(row?.level);
  const jobsSign = jobs === null ? null : signOf(jobs);
  const percentSign = percent === null ? null : signOf(percent);
  const sign = jobsSign !== null && jobsSign === percentSign ? jobsSign : null;
  const higher = noun === "jobs" ? "more jobs" : "more job openings";
  const lower = noun === "jobs" ? "fewer jobs" : "fewer job openings";
  const says = sign === null
    ? READING_INSUFFICIENT
    : sign === 0
      ? `${name} are unchanged over 12 months.`
      : `${name} are ${sign > 0 ? "higher" : "lower"} than 12 months earlier. That means ${sign > 0 ? higher : lower} than 12 months earlier.`;
  return {
    sourceId,
    name,
    period,
    sign,
    observation: level && period ? `${monthLabel(period)}: ${levelPhrase(level, "thousands", noun)}.` : `${name}: the stored level is missing.`,
    trend: sign !== null && jobs && percent
      ? `Stored 12-month change: ${jobsPhrase(jobs, noun)}, ${percentPhrase(percent)}.`
      : "The stored 12-month comparison endpoint is missing.",
    says,
    rank: rankPhrase(row, name.toLowerCase()),
  };
}

function cpiPieceFrom(row: Record<string, unknown> | null): SeriesPiece {
  const change = text(row?.twelve_month_percent_change);
  const period = text(row?.period);
  const earlier = text(row?.comparison_index_level);
  const later = text(row?.index_level);
  const unit = text(row?.unit) ?? "1982-84=100";
  const sign = change === null ? null : signOf(change);
  const says = sign === null
    ? READING_INSUFFICIENT
    : sign === 0
      ? "The CPI-U 12-month percent change is zero."
      : `CPI-U is ${sign > 0 ? "higher" : "lower"} than 12 months earlier.`;
  const endpoints = earlier && later ? ` from index ${indexPhrase(earlier, unit)} to index ${indexPhrase(later, unit)}` : "";
  return {
    sourceId: SERIES_SOURCE.cpi,
    name: "CPI-U",
    period,
    sign,
    observation: later && period ? `${monthLabel(period)}: CPI-U index ${indexPhrase(later, unit)}.` : "CPI-U: the stored index level is missing.",
    trend: change
      ? `Stored 12-month percent change: ${percentPhrase(change)}${endpoints}. Those index levels are the endpoints, not the inflation rate.`
      : "The stored 12-month comparison endpoint is missing.",
    says,
    rank: rankPhrase(row ? { ...row, history_count: row.change_count ?? row.history_count } : null, "CPI-U"),
  };
}

function ratePiece(row: Record<string, unknown> | null, name: string, sourceId: string): SeriesPiece {
  const change = text(row?.one_month_change_percentage_points);
  const period = text(row?.period);
  const level = text(row?.level_percent_per_year);
  const sign = change === null ? null : signOf(change);
  const says = sign === null
    ? READING_INSUFFICIENT
    : sign === 0
      ? `${name} is unchanged over one month.`
      : `${name} is ${sign > 0 ? "higher" : "lower"} than one month earlier.`;
  return {
    sourceId,
    name,
    period,
    sign,
    observation: level && period ? `${monthLabel(period)}: ${name} ${levelPhrase(level, "percent_per_year")}.` : `${name}: the stored level is missing.`,
    trend: change ? `Stored one-month change: ${pointsPhrase(change)}.` : "The stored one-month comparison endpoint is missing.",
    says,
    rank: rankPhrase(row ? { ...row, history_count: row.level_count ?? row.history_count } : null, name.toLowerCase()),
  };
}

function productionPiece(row: Record<string, unknown> | null): SeriesPiece {
  const change = text(row?.twelve_month_percent_change);
  const period = text(row?.latest_period);
  const later = text(row?.latest_level);
  const earlier = text(row?.earlier_level);
  const unit = text(row?.unit) ?? "index_2017_100";
  const sign = change === null ? null : signOf(change);
  const says = sign === null
    ? READING_INSUFFICIENT
    : sign === 0
      ? "Industrial production is unchanged over 12 months."
      : `Industrial production is ${sign > 0 ? "higher" : "lower"} than 12 months earlier.`;
  const endpoints = earlier && later ? ` from index ${indexPhrase(earlier, unit)} to index ${indexPhrase(later, unit)}` : "";
  return {
    sourceId: SERIES_SOURCE.production,
    name: "Industrial production",
    period,
    sign,
    observation: later && period
      ? `${monthLabel(period)}: industrial production index ${indexPhrase(later, unit)}.`
      : "Industrial production: the stored index level is missing.",
    trend: change ? `Stored 12-month percent change: ${percentPhrase(change)}${endpoints}.` : "The stored 12-month comparison endpoint is missing.",
    says,
    rank: rankPhrase(
      row
        ? { ...row, rank: row.historical_rank ?? row.rank, history_count: row.stored_change_count ?? row.stored_value_count ?? row.history_count }
        : null,
      "industrial production",
    ),
  };
}

function sloosPiece(row: Record<string, unknown> | null): SeriesPiece {
  const diff = text(row?.difference_percentage_points);
  const share = text(row?.latest_share);
  const period = text(row?.latest_period_start);
  const sign = diff === null ? null : signOf(diff);
  return {
    sourceId: SERIES_SOURCE.sloos,
    name: "Business credit standards",
    period,
    sign,
    observation: share && period
      ? `${quarterLabel(period)}: net tightening share ${levelPhrase(share, "percent_net_tightening")}.`
      : "SLOOS: the stored share is missing.",
    trend: diff ? `Stored change in the net tightening share: ${pointsPhrase(diff)}.` : "The stored prior-quarter comparison endpoint is missing.",
    says: sloosSays(sign, share),
    rank: null,
  };
}

function bankPiece(row: Record<string, unknown> | null): SeriesPiece {
  const change = text(row?.change_usd_millions);
  const level = text(row?.latest_level_usd_millions);
  const period = text(row?.latest_period_start);
  const ready = row?.sufficiency === undefined || row.sufficiency === "sufficient";
  const sign = change === null || !ready ? null : signOf(change);
  const says = sign === null
    ? READING_INSUFFICIENT
    : sign === 0
      ? "Bank credit is unchanged over 52 weeks."
      : `Bank credit is ${sign > 0 ? "higher" : "lower"} than 52 weeks earlier.`;
  return {
    sourceId: SERIES_SOURCE.bankCredit,
    name: "Bank credit",
    period,
    sign,
    observation: level && period ? `Week of ${dayLabel(period)}: bank credit ${levelPhrase(level, "usd_millions")}.` : "Bank credit: the stored level is missing.",
    trend: sign !== null && change ? `Stored 52-week change: ${moneyPhrase(change)}.` : "The stored 52-week comparison endpoint is missing.",
    says,
    rank: null,
  };
}

function sloosSays(sign: -1 | 0 | 1 | null, share: string | null): string {
  if (sign === null) return READING_INSUFFICIENT;
  if (share !== null && signOf(share) === -1) return "The latest net tightening share is below zero, so this is net easing.";
  if (sign < 0 && share !== null && signOf(share) === 0) {
    return "The latest net tightening share is zero after a negative difference. That is less net tightening, not net easing.";
  }
  if (sign < 0) return "The net tightening share is lower. That is less net tightening, not net easing.";
  if (sign > 0) return "The net tightening share is higher.";
  return "The net tightening share is unchanged.";
}

function hicpLine(): SeriesReadingLine {
  return {
    sourceId: SERIES_SOURCE.hicp,
    compact: "Euro-area HICP stays on this chart as a stale series. It is excluded from the economic reading and ends in December 2025. It is not evidence that a measured US series moved.",
  };
}

function overallSentence(families: FamilyBrief[], divergences: string[], synthesis: StoredMethodRun | null): string | null {
  if (!synthesis || usableCalculation(synthesis) === null) return null;
  if (divergences.length === 0 || divergences.some((item) => !NO_DIVERGENCE.test(item))) return null;
  const ready = families.every((family) => family.reading !== READING_INSUFFICIENT && family.reading !== READING_MIXED);
  return ready ? OVERALL_SENTENCE : null;
}

function pageLimitations(synthesis: StoredMethodRun | null, stored: string[], divergences: string[]): string[] {
  const reported = divergences.filter((item) => !NO_DIVERGENCE.test(item));
  const base = synthesis ? stored : ["The stored MACRO_READING_SYNTHESIS 1.0.0 run is missing.", ...stored];
  return [...base, ...reported.filter((item) => !base.includes(item))];
}

function synthesisLimitations(run: StoredMethodRun | null, calculation: Record<string, unknown> | null): string[] {
  const fromCalculation = stringList(calculation?.limitations);
  if (fromCalculation.length > 0) return fromCalculation;
  return run ? [...run.limitations] : [];
}

function usableCalculation(run: StoredMethodRun | null): Record<string, unknown> | null {
  if (!run || run.dataSufficiency !== "sufficient" || !isRecord(run.calculation)) return null;
  if (run.analysisMode && run.analysisMode !== "latest_revised") return null;
  return run.calculation;
}

function revisedSentence(run: StoredMethodRun | null): string | null {
  if (!run || (run.analysisMode && run.analysisMode !== "latest_revised")) return null;
  return LATEST_REVISED_SENTENCE;
}

function namedDivergences(divergences: string[], needles: string[]): string[] {
  return divergences.filter((item) => {
    if (NO_DIVERGENCE.test(item)) return false;
    const lower = item.toLowerCase();
    if (/do not share one sign/.test(lower) && !needles.some((needle) => lower.includes(needle))) return false;
    return needles.some((needle) => lower.includes(needle));
  });
}

function oppositeClause(pieces: (SeriesPiece & { sign: -1 | 0 | 1 })[]): string | null {
  const higher = pieces.filter((piece) => piece.sign > 0).map((piece) => piece.name);
  const lower = pieces.filter((piece) => piece.sign < 0).map((piece) => piece.name);
  if (higher.length === 0 || lower.length === 0) return null;
  return `${joinNames(higher)} ${higher.length === 1 ? "is" : "are"} higher, and ${joinNames(lower)} ${lower.length === 1 ? "is" : "are"} lower.`;
}

function periodsDiffer(pieces: SeriesPiece[]): boolean {
  const periods = pieces.map((piece) => piece.period).filter((period): period is string => Boolean(period));
  return new Set(periods).size > 1;
}

function nextRelease(sourceIds: readonly string[], calendar: ReadonlySet<string>): { next: string; nextHref: "/calendar" | null } {
  const titles: string[] = [];
  for (const sourceId of sourceIds) {
    if (!calendar.has(sourceId)) continue;
    const title = BLS_RELEASE[sourceId];
    if (!title || titles.includes(title)) continue;
    titles.push(title);
  }
  if (titles.length === 0) return { next: "A next release is not in the verified calendar.", nextHref: null };
  const verb = titles.length === 1 ? "release is on" : "releases are on";
  return { next: `The next ${joinNames(titles)} ${verb}`, nextHref: "/calendar" };
}

function jointSentence(value: unknown): string | null {
  if (!isRecord(value)) return null;
  const period = text(value.latest_common_period);
  if (!period) return null;
  return `The joint reading uses ${monthLabel(period)}, the latest month present in all three series.`;
}

function rankPhrase(row: Record<string, unknown> | null, subject: string): string | null {
  if (!row) return null;
  const rank = text(row.rank);
  const count = text(row.history_count);
  if (!rank || !count) return null;
  const basis = text(row.rank_basis);
  const definition = basis === "overlapping_twelve_month_percent_change"
    ? `overlapping 12-month percent changes in ${subject}`
    : basis === "level"
      ? `the ${subject} level`
      : subject;
  return `Rank of ${definition}: ${rank} of ${count}.`;
}

function pointsPhrase(raw: string): string {
  return signOf(raw) === 0 ? "0 percentage points" : `${raw.trim()} percentage points`;
}

function percentPhrase(raw: string): string {
  return signOf(raw) === 0 ? "0 percent" : `${raw.trim()} percent`;
}

function jobsPhrase(raw: string, noun: CountNoun): string {
  if (signOf(raw) === 0) return noun === "jobs" ? "0 jobs" : "0 job openings";
  return displayChange(raw, "thousands", noun) ?? `${raw.trim()} thousand`;
}

function moneyPhrase(raw: string): string {
  if (signOf(raw) === 0) return "0";
  return displayChange(raw, "usd_millions") ?? `${raw.trim()} millions of US dollars`;
}

function levelPhrase(raw: string, unit: string, noun?: CountNoun): string {
  return displayLevel(raw, unit, noun)?.headline ?? raw;
}

function indexPhrase(raw: string, unit: string): string {
  return displayLevel(raw, unit)?.headline ?? raw;
}

function signOf(raw: string): -1 | 0 | 1 | null {
  const trimmed = raw.trim();
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) return null;
  const negative = trimmed.startsWith("-");
  const body = negative ? trimmed.slice(1) : trimmed;
  if (/^0+(\.0+)?$/.test(body)) return 0;
  return negative ? -1 : 1;
}

function monthLabel(iso: string): string {
  return formatUtc(iso, { month: "long", year: "numeric" });
}

function dayLabel(iso: string): string {
  return formatUtc(iso, { day: "numeric", month: "long", year: "numeric" });
}

function quarterLabel(iso: string): string {
  return `Quarter starting ${dayLabel(iso)}`;
}

function formatUtc(iso: string, options: Intl.DateTimeFormatOptions): string {
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return iso;
  return new Intl.DateTimeFormat("en-GB", { ...options, timeZone: "UTC" }).format(new Date(Date.UTC(year, month - 1, day)));
}

function joinNames(names: string[]): string {
  if (names.length <= 1) return names[0] ?? "";
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function text(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
