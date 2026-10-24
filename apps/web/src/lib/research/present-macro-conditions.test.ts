import assert from "node:assert/strict";
import test from "node:test";

import {
  EXCLUDED_PRESS_SOURCE_IDS,
  MACRO_CONDITIONS_WINDOW,
  MACRO_SERIES,
  type StoredSeriesWindow,
} from "./macro-conditions.ts";
import {
  frequencySparkline,
  gapsInWindow,
  isStale,
  presentMacroConditions,
  revisionLimitLine,
  subtractDecimal,
  type MacroConditionsView,
} from "./present-macro-conditions.ts";

const AS_OF = new Date("2026-10-24T12:00:00.000Z");

const UNEMPLOYMENT_PERIODS = [
  "2025-08-01",
  "2025-09-01",
  "2025-11-01",
  "2025-12-01",
  "2026-01-01",
  "2026-02-01",
  "2026-03-01",
  "2026-04-01",
  "2026-05-01",
  "2026-06-01",
  "2026-07-01",
  "2026-08-01",
  "2026-09-01",
];

function series(partial: Partial<StoredSeriesWindow> & Pick<StoredSeriesWindow, "sourceId">): StoredSeriesWindow {
  return {
    datasetId: "dataset",
    retrievedAt: "2026-10-22T21:59:18.000Z",
    seriesProvenance: "latest_revised",
    unit: "percent",
    seasonalAdjustment: "seasonally_adjusted",
    frequency: "monthly",
    observations: [],
    ...partial,
  };
}

function unemployment(): StoredSeriesWindow {
  return series({
    sourceId: "bls_cps_unemployment_rate",
    datasetId: "bls.ln.LNS14000000",
    observations: UNEMPLOYMENT_PERIODS.map((period) => ({
      period,
      rawValue: period === "2026-09-01" ? "4.2" : period === "2026-08-01" ? "4.1" : "4.0",
    })),
  });
}

function panel(view: MacroConditionsView, sourceId: string) {
  const found = view.groups.flatMap((group) => group.panels).find((item) => item.sourceId === sourceId);
  assert.ok(found, sourceId);
  return found;
}

function visibleCopy(view: MacroConditionsView): string {
  const chunks = [view.intro, view.freshnessRule, view.completenessLine, view.revisionLimit];
  for (const group of view.groups) {
    chunks.push(group.label);
    for (const item of group.panels) {
      chunks.push(
        item.name,
        item.stateLine,
        item.description,
        item.detailLine ?? "",
        item.sourceLine ?? "",
        item.windowLine ?? "",
        item.chart?.caption ?? "",
        item.gapLine ?? "",
        item.chartNote ?? "",
        item.freshnessLine,
      );
    }
  }
  for (const item of view.unavailable) chunks.push(item.name, item.detail);
  return chunks.join("\n");
}

test("the ten live series are grouped and monetary-policy press is not a rates panel", () => {
  assert.equal(MACRO_SERIES.length, 10);
  assert.deepEqual(
    MACRO_SERIES.map((item) => item.sourceId),
    [
      "bls_cps_unemployment_rate",
      "bls_ces_total_nonfarm_payrolls",
      "bls_jolts_total_nonfarm_job_openings",
      "bls_cpi_u_all_items",
      "federal_reserve_g17_total_ip",
      "federal_reserve_sloos_cil",
      "federal_reserve_h8_bank_credit",
      "federal_reserve_h15_federal_funds_effective",
      "federal_reserve_h15_treasury_10y_constant_maturity",
      "ecb_sdw_hicp_sa",
    ],
  );
  assert.deepEqual(
    MACRO_SERIES.filter((item) => item.groupId === "rates").map((item) => item.sourceId),
    [
      "federal_reserve_h15_federal_funds_effective",
      "federal_reserve_h15_treasury_10y_constant_maturity",
    ],
  );
  for (const sourceId of EXCLUDED_PRESS_SOURCE_IDS) {
    assert.equal(MACRO_SERIES.some((item) => item.sourceId === sourceId), false);
  }
  assert.equal(MACRO_CONDITIONS_WINDOW, 12);
});

test("decimal differences keep the stored scale", () => {
  assert.equal(subtractDecimal("4.2", "4.1"), "0.1");
  assert.equal(subtractDecimal("0.0", "8.1"), "-8.1");
  assert.equal(subtractDecimal("159044", "159015"), "29");
  assert.equal(subtractDecimal("19948526.8", "19891394.8"), "57132");
  assert.equal(subtractDecimal("336.298", "334.131"), "2.167");
  assert.equal(subtractDecimal("4.20", "4.2"), "0");
  assert.equal(subtractDecimal("not-a-number", "1"), null);
});

test("freshness respects monthly, weekly and quarterly lags", () => {
  assert.equal(isStale("monthly", "2026-09-01", AS_OF), false);
  assert.equal(isStale("monthly", "2026-08-01", AS_OF), false);
  assert.equal(isStale("monthly", "2026-07-01", AS_OF), true);
  assert.equal(isStale("monthly", "2025-12-01", AS_OF), true);
  assert.equal(isStale("weekly", "2026-10-07", AS_OF), false);
  assert.equal(isStale("weekly", "2026-10-03", AS_OF), false);
  assert.equal(isStale("weekly", "2026-09-16", AS_OF), true);
  assert.equal(isStale("quarterly", "2026-07-01", AS_OF), false);
  assert.equal(isStale("quarterly", "2026-04-01", AS_OF), false);
  assert.equal(isStale("quarterly", "2026-01-01", AS_OF), true);
});

test("a missing month is named and the line is not drawn through it", () => {
  assert.deepEqual(gapsInWindow(["2025-09-01", "2025-11-01", "2025-12-01"], "monthly"), ["2025-10-01"]);
  const marks = frequencySparkline(
    [
      { period: "2026-01-01", value: 1 },
      { period: "2026-02-01", value: 2 },
      { period: "2026-04-01", value: 4 },
    ],
    "monthly",
  );
  assert.equal(marks.length, 2);
  assert.equal(marks[0]?.kind, "line");
  assert.equal(marks[1]?.kind, "point");
  if (marks[0]?.kind === "line") assert.equal(marks[0].points.split(" ").length, 2);
  const view = presentMacroConditions({ series: [unemployment()], asOf: AS_OF });
  const item = panel(view, "bls_cps_unemployment_rate");
  assert.equal(item.state, "current");
  assert.match(item.chart?.caption ?? "", /latest 12 stored monthly observations, from September 2025 to September 2026/);
  assert.doesNotMatch(item.chart?.caption ?? "", /August 2025/);
  assert.match(item.gapLine ?? "", /Permanently missing: October 2025/);
  assert.match(item.gapLine ?? "", /did not publish this month/);
  assert.match(item.gapLine ?? "", /Nothing was filled in/);
  assert.equal(item.chart?.marks.length, 2);
  assert.equal(item.chart?.marks[0]?.kind, "point");
  assert.equal(item.chart?.marks[1]?.kind, "line");
  assert.match(
    item.description,
    /Latest observation: 4\.2 percent for September 2026\. Previous stored observation: 4\.1 percent for August 2026\. Difference: 0\.1 percentage points higher\./,
  );
  assert.equal(item.evidenceHref, "/research");
  assert.match(item.detailLine ?? "", /Stored unit percent\. Seasonally adjusted\. Monthly\. Latest revised\./);
});

test("a continuous monthly span is one line and an unchanged value is not a direction", () => {
  const marks = frequencySparkline(
    [
      { period: "2026-01-01", value: 1 },
      { period: "2026-02-01", value: 2 },
      { period: "2026-03-01", value: 3 },
    ],
    "monthly",
  );
  assert.equal(marks.length, 1);
  assert.equal(marks[0]?.kind, "line");
  const view = presentMacroConditions({
    series: [
      series({
        sourceId: "bls_cps_unemployment_rate",
        observations: [
          { period: "2026-08-01", rawValue: "4.1" },
          { period: "2026-09-01", rawValue: "4.1" },
        ],
      }),
    ],
    asOf: AS_OF,
  });
  const item = panel(view, "bls_cps_unemployment_rate");
  assert.equal(item.gapLine, null);
  assert.match(item.description, /Difference: unchanged\./);
});

test("weekly and quarterly series keep their own period and difference unit", () => {
  const weeklyGap = frequencySparkline(
    [
      { period: "2026-09-30", value: 1 },
      { period: "2026-10-14", value: 2 },
    ],
    "weekly",
  );
  assert.equal(weeklyGap.length, 2);
  assert.equal(weeklyGap[0]?.kind, "point");
  assert.equal(weeklyGap[1]?.kind, "point");
  const view = presentMacroConditions({
    series: [
      series({
        sourceId: "federal_reserve_h8_bank_credit",
        datasetId: "fed.h8.B1001NCBA",
        unit: "usd_millions",
        frequency: "weekly",
        observations: [
          { period: "2026-09-30", rawValue: "19891394.8" },
          { period: "2026-10-07", rawValue: "19948526.8" },
        ],
      }),
      series({
        sourceId: "federal_reserve_sloos_cil",
        datasetId: "fed.sloos.SUBLPDCILS_N.Q",
        unit: "percent_net_tightening",
        seasonalAdjustment: "not_seasonally_adjusted",
        frequency: "quarterly",
        observations: [
          { period: "2026-04-01", rawValue: "8.1" },
          { period: "2026-07-01", rawValue: "0.0" },
        ],
      }),
      series({
        sourceId: "bls_ces_total_nonfarm_payrolls",
        unit: "thousands",
        observations: [
          { period: "2026-08-01", rawValue: "159015" },
          { period: "2026-09-01", rawValue: "159044" },
        ],
      }),
    ],
    asOf: AS_OF,
  });
  const credit = panel(view, "federal_reserve_h8_bank_credit");
  assert.match(credit.description, /week of 7 October 2026/);
  assert.match(credit.description, /57132 millions of US dollars higher/);
  assert.doesNotMatch(credit.description, /percentage points/);
  const sloos = panel(view, "federal_reserve_sloos_cil");
  assert.match(sloos.description, /quarter starting 1 July 2026/);
  assert.match(sloos.description, /8\.1 percentage points lower/);
  assert.match(sloos.detailLine ?? "", /Not seasonally adjusted\. Quarterly\./);
  const payrolls = panel(view, "bls_ces_total_nonfarm_payrolls");
  assert.match(payrolls.description, /29 thousands higher/);
  assert.doesNotMatch(payrolls.description, /percentage points/);
});

test("a stale series is still shown and a missing series says so", () => {
  const view = presentMacroConditions({
    series: [
      series({
        sourceId: "ecb_sdw_hicp_sa",
        datasetId: "ecb.icp.M.U2.Y.000000.3.INX",
        unit: "index, 2015 = 100",
        observations: [
          { period: "2025-11-01", rawValue: "129.67" },
          { period: "2025-12-01", rawValue: "129.73" },
        ],
      }),
    ],
    asOf: AS_OF,
  });
  const hicp = panel(view, "ecb_sdw_hicp_sa");
  assert.equal(hicp.state, "stale");
  assert.match(hicp.stateLine, /Data state: stale/);
  assert.match(hicp.description, /129\.73 index, 2015 = 100 for December 2025/);
  assert.equal(hicp.evidenceHref, "/research");
  const missing = panel(view, "bls_cps_unemployment_rate");
  assert.equal(missing.state, "missing");
  assert.match(missing.description, /No live observation is stored/);
  assert.equal(missing.evidenceHref, null);
  assert.equal(missing.chart, null);
  assert.match(view.completenessLine, /1 of 10 tracked series has a stored observation/);
  assert.match(view.completenessLine, /9 have no live observation/);
  assert.match(view.completenessLine, /1 is stale for its frequency/);
  assert.match(view.freshnessRule, /Comparison date: 24 October 2026 UTC/);
  assert.equal(view.unavailable.map((item) => item.id).join(","), "liquidity,monetary_policy_stance");
  const copy = visibleCopy(view);
  assert.match(copy, /There is no composite score/);
  assert.match(copy, /not a judgement about the investment environment/);
  assert.match(copy, /Monetary-policy press is a publication record, not a rates panel/);
  assert.doesNotMatch(copy, /favourable|favorable|bullish|bearish|caused by|because|gauge|recession|improved/i);
});

test("one stored observation is insufficient for a change or a trend", () => {
  const view = presentMacroConditions({
    series: [
      series({
        sourceId: "bls_jolts_total_nonfarm_job_openings",
        observations: [{ period: "2026-08-01", rawValue: "7079" }],
      }),
    ],
    asOf: AS_OF,
  });
  const item = panel(view, "bls_jolts_total_nonfarm_job_openings");
  assert.equal(item.state, "insufficient");
  assert.match(item.description, /no difference is stated/);
  assert.match(item.chartNote ?? "", /insufficient observation points/);
  assert.equal(item.chart, null);
  assert.match(item.windowLine ?? "", /latest 1 stored monthly observation/);
  assert.match(item.windowLine ?? "", /The limit is 12/);
  assert.match(view.revisionLimit, /These stored series are latest revised/);
  assert.doesNotMatch(view.revisionLimit, /because|gauge|composite score/i);
});

test("a historical date is withheld when revision basis is missing or mixed", () => {
  assert.match(
    revisionLimitLine([]),
    /No live series is stored, so no revision basis is shown/,
  );
  assert.match(
    revisionLimitLine([series({ sourceId: "bls_cps_unemployment_rate", seriesProvenance: null, observations: [{ period: "2026-09-01", rawValue: "4.2" }] })]),
    /Revision basis is not stored/,
  );
  assert.match(
    revisionLimitLine([
      series({ sourceId: "bls_cps_unemployment_rate", observations: [{ period: "2026-09-01", rawValue: "4.2" }] }),
      series({
        sourceId: "bls_cpi_u_all_items",
        seriesProvenance: "provider_vintage",
        observations: [{ period: "2026-09-01", rawValue: "100" }],
      }),
    ]),
    /Revision basis is not only latest revised/,
  );
});
