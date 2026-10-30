import assert from "node:assert/strict";
import test from "node:test";

import {
  extractPrivateResult,
  selectDisplayRun,
  type StoredMethodologyRun,
} from "./private-methodology-result.ts";

function stored(overrides: Partial<StoredMethodologyRun>): StoredMethodologyRun {
  return {
    runId: "run-1",
    methodId: "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT",
    methodVersion: "0.1.0",
    executedAt: "2026-10-25T08:00:00.000Z",
    executionStatus: "completed",
    publicationAllowed: false,
    dataSufficiency: "sufficient",
    analysisMode: "latest_revised",
    primaryDatasetId: "fed.g17.IP.B50001.S",
    missingDataReason: null,
    statisticalInterpretation: "Stored.",
    limitations: [],
    calculation: null,
    ...overrides,
  };
}

test("a small likelihood gain does not replace the preserved filtered factor", () => {
  const preserved = stored({
    runId: "3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a",
    executedAt: "2026-10-25T08:00:00.000Z",
    calculation: {
      adopted_parameter_version: true,
      operationally_accepted: false,
      log_likelihood: -1590.5375,
      growth_start: "1997-02-01",
      sample_levels: ["1997-01-01", "2026-07-01"],
      loadings_ip_income_sales_payroll: [0.907, 0.592, 0.747, 0.834],
      filtered_factor: [0.1, -0.2, -2.5],
      smoothed_factor: [9, 9, 9],
      filtered_factor_is_not_the_smoother: true,
      input_vintage: "latest_revised",
      real_time: false,
    },
  });
  const reestimate = stored({
    runId: "940955f1-50d5-4c06-9d90-5ceebd05d352",
    executedAt: "2026-10-30T08:00:00.000Z",
    calculation: {
      adopted_parameter_version: false,
      operationally_accepted: false,
      log_likelihood: -1590.5372,
      gradient_norm: 0.000629,
      preserved_run_id: preserved.runId,
      growth_start: "1997-02-01",
      filtered_factor: [4, 4, 4],
      loadings_ip_income_sales_payroll: [0.1, 0.1, 0.1, 0.1],
    },
  });
  const selected = selectDisplayRun([reestimate, preserved]);
  assert.equal(selected.display?.runId, preserved.runId);
  assert.equal(selected.unadoptedReestimate?.runId, reestimate.runId);
  const display = selected.display;
  assert.ok(display);
  const result = extractPrivateResult(display, selected.unadoptedReestimate);
  assert.equal(result.publicationAllowed, false);
  assert.equal(result.series?.points[0]?.value, 0.1);
  assert.equal(result.series?.points[0]?.period, "1997-02-01");
  assert.equal(result.series?.points[2]?.value, -2.5);
  assert.match(result.standing, /Not operationally accepted/);
  assert.match(result.standing, /Not approved for publication/);
  assert.match(result.diagnostic ?? "", /preserved filtered factor/);
  assert.equal(JSON.stringify(result.series).includes("4,4,4") || JSON.stringify(result.series).includes('"value":4'), false);
});

test("an insufficient run is a diagnostic and has no chart", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "BRY_BOSCHAN_MONTHLY_1971",
      executionStatus: "completed_insufficient",
      dataSufficiency: "insufficient",
      missingDataReason: "The 1971 programme listing is not in the volume.",
      calculation: null,
    }),
  );
  assert.equal(result.series, null);
  assert.match(result.standing, /not an operational assessment/);
  assert.match(result.diagnostic ?? "", /1971 programme listing/);
  assert.equal(result.publicationAllowed, false);
});

test("Hamilton plots the filtered probability and keeps the short regime unqualified", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "HAMILTON_MONTHLY_REGIME_SWITCHING",
      calculation: {
        empirically_qualified: false,
        operational: false,
        real_time_assessment: false,
        revision: "latest_revised",
        lag_selection: { chosen_lag: 2 },
        expected_regime_durations_months: { lower_mean: 2.04, higher_mean: 18 },
        sample: { modelled_start: "1919-02-01", modelled_end: "1919-04-01" },
        filtered_regime_probabilities: [
          { period: "1919-02-01", lower_mean: 0.2, higher_mean: 0.8 },
          { period: "1919-03-01", lower_mean: 0.7, higher_mean: 0.3 },
        ],
        smoothed_regime_probabilities: [
          { period: "1919-02-01", lower_mean: 0.99, higher_mean: 0.01 },
          { period: "1919-03-01", lower_mean: 0.99, higher_mean: 0.01 },
        ],
        minimum_duration_alternative: {
          identified: false,
          adopted: false,
          reason: "The constrained specification was not estimated and is not a recession label.",
        },
      },
    }),
  );
  assert.equal(result.series?.points[1]?.value, 0.7);
  assert.equal(JSON.stringify(result.series).includes("0.99"), false);
  assert.match(result.standing, /Not empirically qualified/);
  assert.match(result.limitations.join(" "), /2\.04 months/);
  assert.match(result.diagnostic ?? "", /not a recession label/);
});

test("the Sahm gap is the stored month and is not a plotted path", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "SAHM_UNEMPLOYMENT_GAP",
      calculation: {
        evaluation_period: "2025-09-01",
        gap_percentage_points: "0.23",
        three_month_average: "4.33",
        prior_twelve_month_low_of_average: "4.10",
        threshold_percentage_points: "0.50",
        triggered: false,
      },
    }),
  );
  assert.equal(result.series, null);
  assert.match(result.headline, /0\.23/);
  assert.match(result.headline, /Not triggered/);
  assert.match(result.standing, /October 2025 is not interpolated/);
  assert.match(result.limitations.join(" "), /no gap path/);
  assert.equal(result.publicationAllowed, false);
});
