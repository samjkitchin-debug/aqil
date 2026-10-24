import assert from "node:assert/strict";
import test from "node:test";

import {
  HICP_EXCLUSION,
  LATEST_REVISED_SENTENCE,
  NOT_INVESTMENT_CONCLUSION,
  OVERALL_SENTENCE,
  READING_INSUFFICIENT,
  READING_MIXED,
  READING_STABLE,
  SERIES_SOURCE,
  THREE_MONTH_PAYROLL_NOTE,
  UNANSWERED_HEADING,
  UNANSWERED_QUESTIONS,
  presentEconomicEvidence,
  type EconomicEvidenceInput,
  type StoredMethodRun,
} from "./present-economic-evidence.ts";

const BANNED = /favourable|unfavourable|unfavorable|asset return|outperform|bullish|bearish|total return/i;

function run(
  methodId: string,
  methodVersion: string,
  calculation: Record<string, unknown> | null,
  sufficiency = "sufficient",
): StoredMethodRun {
  return {
    methodId,
    methodVersion,
    runId: `${methodId}-run`,
    payloadHash: `${methodId}-hash`,
    dataSufficiency: sufficiency,
    missingDataReason: sufficiency === "sufficient" ? null : "A comparison endpoint is missing.",
    analysisMode: "latest_revised",
    calculation,
    limitations: [],
  };
}

function input(overrides: Partial<EconomicEvidenceInput> = {}): EconomicEvidenceInput {
  const base: EconomicEvidenceInput = {
    synthesis: run("MACRO_READING_SYNTHESIS", "1.0.0", {
      summary: "The reading is internal.",
      divergences: ["No stored latest month diverges from the shared monthly month."],
      limitations: [
        "The reading is internal.",
        "No composite score is calculated.",
        "Euro-area HICP is excluded and ends in December 2025.",
        "The stored files are latest_revised. They are not a vintage panel.",
      ],
      composite_score: null,
    }),
    labour: run("LABOUR_MARKET_CONDITIONS", "1.1.0", {
      analysis_mode: "latest_revised",
      series: [
        labourRow("bls.ln.LNS14000000", "4.2", "percent", "0.00", null, null),
        labourRow("bls.ce.CES0000000001", "159044", "thousands", null, "0", "0.00"),
        labourRow("bls.jt.JTS000000000000000JOL", "7079", "thousands", null, "0", "0.00"),
      ],
      joint: { latest_common_period: "2026-09-01" },
    }),
    prices: run("PRICES_AND_POLICY", "1.1.0", {
      cpi_u: cpiRow("0.0000"),
      federal_funds: rateRow("3.75", "0.0000"),
      treasury_10_year: rateRow("4.99", "0.0000"),
    }),
    production: run("INDUSTRIAL_PRODUCTION_ACTIVITY", "1.1.0", {
      latest_period: "2026-09-01",
      earlier_period: "2025-09-01",
      latest_level: "103.9506",
      earlier_level: "103.9506",
      unit: "index_2017_100",
      twelve_month_percent_change: "0.0000",
      historical_rank: 10,
      stored_change_count: 20,
      rank_basis: "overlapping_twelve_month_percent_change",
    }),
    credit: run("CREDIT_STANDARDS_AND_VOLUMES", "1.0.0", {
      lending_standards: {
        latest_period_start: "2026-09-01",
        latest_share: "0",
        difference_percentage_points: "0",
        unit: "percent_net_tightening",
      },
      bank_credit: {
        latest_period_start: "2026-09-01",
        latest_level_usd_millions: "19948526.8",
        change_usd_millions: "0",
        sufficiency: "sufficient",
      },
    }),
    blsCalendarSourceIds: [
      SERIES_SOURCE.unemployment,
      SERIES_SOURCE.payrolls,
      SERIES_SOURCE.openings,
      SERIES_SOURCE.cpi,
    ],
  };
  return { ...base, ...overrides };
}

function labourRow(
  datasetId: string,
  level: string,
  unit: string,
  points: string | null,
  thousands: string | null,
  percent: string | null,
) {
  const change: Record<string, unknown> = { window_start: "2025-09-01", window_end: "2026-09-01" };
  if (points !== null) {
    change.change_percentage_points = points;
    change.change_unit = "percentage_points";
  }
  if (thousands !== null && percent !== null) {
    change.change_thousands = thousands;
    change.percent_change = percent;
  }
  return {
    dataset_id: datasetId,
    latest_period: "2026-09-01",
    level,
    unit,
    rank: 2,
    history_count: 10,
    rank_basis: datasetId === "bls.ce.CES0000000001" ? "overlapping_twelve_month_percent_change" : "level",
    twelve_month_change: change,
  };
}

function cpiRow(change: string | null, extra: Record<string, unknown> = {}) {
  return {
    period: "2026-09-01",
    comparison_period: "2025-09-01",
    unit: "1982-84=100",
    index_level: "336.298",
    comparison_index_level: "324.245",
    twelve_month_percent_change: change,
    rank: 4,
    change_count: 10,
    rank_basis: "overlapping_twelve_month_percent_change",
    ...extra,
  };
}

function rateRow(level: string, change: string) {
  return {
    period: "2026-09-01",
    prior_period: "2026-08-01",
    level_percent_per_year: level,
    one_month_change_percentage_points: change,
    seasonal_adjustment: "unknown",
    rank: 3,
    level_count: 12,
    rank_basis: "level",
  };
}

function familyText(view: ReturnType<typeof presentEconomicEvidence>, id: string): string {
  const family = view.families.find((item) => item.id === id);
  assert.ok(family, id);
  return [family.observation, family.trend, family.context, family.reading, family.contradiction, family.limitation].join(" ");
}

test("CPI is read as the stored 12-month percent change", () => {
  const prices = input().prices;
  assert.ok(prices?.calculation);
  prices.calculation.cpi_u = cpiRow("3.7173");
  const view = presentEconomicEvidence(input({ prices }));
  const text = familyText(view, "inflation");
  assert.match(text, /Stored 12-month percent change: 3\.7173 percent/);
  assert.match(text, /from index 324\.245 to index 336\.298/);
  assert.match(text, /Those index levels are the endpoints, not the inflation rate/);
  assert.match(text, /CPI-U is higher than 12 months earlier/);
  assert.doesNotMatch(text, /percentage points/);
});

test("payrolls are a change in jobs, with the stored percent", () => {
  const labour = input().labour;
  assert.ok(labour?.calculation);
  labour.calculation.series = [
    labourRow("bls.ln.LNS14000000", "4.2", "percent", "0.10", null, null),
    labourRow("bls.ce.CES0000000001", "159044", "thousands", null, "496", "0.31"),
    labourRow("bls.jt.JTS000000000000000JOL", "7079", "thousands", null, "160", "2.31"),
  ];
  const text = familyText(presentEconomicEvidence(input({ labour })), "labour");
  assert.match(text, /million jobs/);
  assert.match(text, /0\.31 percent/);
  assert.match(text, /more jobs than 12 months earlier/);
  assert.equal(text.toLowerCase().includes("people"), false);
});

test("unemployment and interest rates use percentage points, and CPI stays in percent", () => {
  const base = input();
  assert.ok(base.labour?.calculation && base.prices?.calculation);
  base.labour.calculation.series = [
    labourRow("bls.ln.LNS14000000", "4.2", "percent", "-0.20", null, null),
    labourRow("bls.ce.CES0000000001", "159044", "thousands", null, "496", "0.31"),
    labourRow("bls.jt.JTS000000000000000JOL", "7079", "thousands", null, "160", "2.31"),
  ];
  base.prices.calculation.cpi_u = cpiRow("3.7173");
  base.prices.calculation.federal_funds = rateRow("3.75", "0.1200");
  base.prices.calculation.treasury_10_year = rateRow("4.99", "0.3100");
  const view = presentEconomicEvidence(base);
  assert.match(familyText(view, "labour"), /-0\.20 percentage points/);
  const inflation = familyText(view, "inflation");
  assert.match(inflation, /3\.7173 percent/);
  assert.doesNotMatch(inflation, /percentage points/);
  const rates = familyText(view, "rates");
  assert.match(rates, /0\.1200 percentage points/);
  assert.match(rates, /0\.3100 percentage points/);
  assert.match(rates, /Interest rates stay separate from the CPI inflation rate/);
  assert.doesNotMatch(rates, /12-month percent change/);
});

test("a zero SLOOS share after a negative difference is not called net easing", () => {
  const credit = input().credit;
  assert.ok(credit?.calculation);
  credit.calculation.lending_standards = {
    latest_period_start: "2026-07-01",
    latest_share: "0.0",
    prior_share: "8.1",
    difference_percentage_points: "-8.1",
    unit: "percent_net_tightening",
  };
  credit.calculation.bank_credit = {
    latest_period_start: "2026-10-07",
    latest_level_usd_millions: "19948526.8",
    change_usd_millions: "1157236.1",
    sufficiency: "sufficient",
  };
  const view = presentEconomicEvidence(input({ credit }));
  const line = view.seriesLines.find((item) => item.sourceId === SERIES_SOURCE.sloos);
  const text = `${familyText(view, "credit")} ${line?.compact ?? ""}`;
  assert.match(text, /zero after a negative difference/);
  assert.match(text, /less net tightening, not net easing/);
  assert.doesNotMatch(text, /this is net easing/);
  assert.equal(view.families.find((item) => item.id === "credit")?.reading, READING_MIXED);
});

test("net easing is stated only when the latest stored share is below zero", () => {
  const credit = input().credit;
  assert.ok(credit?.calculation);
  credit.calculation.lending_standards = {
    latest_period_start: "2026-07-01",
    latest_share: "-1.5",
    difference_percentage_points: "-2.0",
  };
  credit.calculation.bank_credit = {
    latest_period_start: "2026-07-01",
    latest_level_usd_millions: "1000000",
    change_usd_millions: "-10",
    sufficiency: "sufficient",
  };
  assert.match(familyText(presentEconomicEvidence(input({ credit })), "credit"), /this is net easing/);
});

test("a missing comparison endpoint is insufficient evidence and is not invented", () => {
  const prices = input().prices;
  assert.ok(prices?.calculation);
  const cpi = cpiRow(null);
  delete cpi.twelve_month_percent_change;
  prices.calculation.cpi_u = cpi;
  const inflation = presentEconomicEvidence(input({ prices })).families.find((item) => item.id === "inflation");
  assert.equal(inflation?.reading, READING_INSUFFICIENT);
  assert.match(inflation?.trend ?? "", /comparison endpoint is missing/);
  assert.doesNotMatch(inflation?.trend ?? "", /Stored 12-month percent change:/);
});

test("opposite signs in one family are labelled mixed", () => {
  const labour = input().labour;
  assert.ok(labour?.calculation);
  labour.calculation.series = [
    labourRow("bls.ln.LNS14000000", "4.2", "percent", "-0.20", null, null),
    labourRow("bls.ce.CES0000000001", "159044", "thousands", null, "496", "0.31"),
    labourRow("bls.jt.JTS000000000000000JOL", "7079", "thousands", null, "160", "2.31"),
  ];
  const view = presentEconomicEvidence(input({ labour }));
  const family = view.families.find((item) => item.id === "labour");
  assert.equal(family?.reading, READING_MIXED);
  assert.match(family?.contradiction ?? "", /higher/);
  assert.match(family?.contradiction ?? "", /lower/);
  assert.equal(view.overall, null);
});

test("stale euro-area HICP stays out of the US family readings", () => {
  const view = presentEconomicEvidence(input());
  assert.equal(view.hicpNote, HICP_EXCLUSION);
  for (const family of view.families) {
    assert.equal(/HICP/.test(`${family.reading} ${family.observation} ${family.trend}`), false);
  }
  const line = view.seriesLines.find((item) => item.sourceId === SERIES_SOURCE.hicp);
  assert.match(line?.compact ?? "", /excluded/);
  assert.match(line?.compact ?? "", /December 2025/);
  assert.match(view.limitations.join(" "), /Euro-area HICP is excluded and ends in December 2025/);
});

test("each family says the file is latest revised and not a vintage panel", () => {
  const view = presentEconomicEvidence(input());
  for (const family of view.families) {
    assert.match(family.context, /latest revised/);
    assert.match(family.context, /not a vintage panel/);
  }
  assert.match(familyText(view, "labour"), /Three-month payroll acceleration is not calculated/);
  assert.equal(THREE_MONTH_PAYROLL_NOTE, "Three-month payroll acceleration is not calculated.");
});

test("the reading does not state an investment implication", () => {
  const view = presentEconomicEvidence(input());
  const text = [
    view.overall ?? "",
    view.hicpNote,
    ...view.families.flatMap((family) => [family.observation, family.trend, family.context, family.reading, family.contradiction, family.limitation]),
    ...view.seriesLines.map((line) => line.compact),
  ].join(" ");
  assert.doesNotMatch(text, BANNED);
  assert.equal(view.unansweredHeading, UNANSWERED_HEADING);
  assert.deepEqual(view.unanswered, UNANSWERED_QUESTIONS);
  assert.equal(view.unansweredNote, NOT_INVESTMENT_CONCLUSION);
  assert.match(view.limitations.join(" "), /No composite score is calculated/);
});

test("an overall sentence appears only when every family has a reading and no divergence is reported", () => {
  const stable = presentEconomicEvidence(input());
  for (const family of stable.families) assert.equal(family.reading, READING_STABLE);
  assert.equal(stable.overall, OVERALL_SENTENCE);
  assert.match(stable.families.find((item) => item.id === "labour")?.next ?? "", /Employment Situation/);
  assert.equal(stable.families.find((item) => item.id === "labour")?.nextHref, "/calendar");
  assert.match(stable.families.find((item) => item.id === "production")?.next ?? "", /not in the verified calendar/);
  assert.equal(stable.families.find((item) => item.id === "production")?.nextHref, null);
  const synthesis = input().synthesis;
  assert.ok(synthesis?.calculation);
  synthesis.calculation.divergences = [
    "The stored changes do not share one sign.",
    "Latest months that do not match September 2026: Job openings August 2026.",
  ];
  const diverged = presentEconomicEvidence(input({ synthesis }));
  assert.equal(diverged.overall, null);
  assert.match(familyText(diverged, "labour"), /Job openings August 2026/);
});

test("a missing stored run stays insufficient", () => {
  const labour = presentEconomicEvidence(input({ labour: null })).families.find((item) => item.id === "labour");
  assert.equal(labour?.reading, READING_INSUFFICIENT);
  assert.match(labour?.trend ?? "", /missing/);
  assert.equal(labour?.trend.includes("496"), false);
});

test("the context repeats the stored rank definition", () => {
  const view = presentEconomicEvidence(input());
  const text = familyText(view, "labour");
  assert.match(text, /Rank of overlapping 12-month percent changes in payrolls: 2 of 10/);
  assert.match(text, /Rank of the unemployment rate level: 2 of 10/);
  assert.match(view.families.map((item) => item.context).join(" "), new RegExp(LATEST_REVISED_SENTENCE.replace(/[.]/g, "\\.")));
});
