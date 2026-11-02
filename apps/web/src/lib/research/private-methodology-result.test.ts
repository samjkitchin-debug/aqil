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
  assert.match(result.limitations.join(" "), /longer revised unemployment history was not used/);
  assert.equal(result.publicationAllowed, false);
});

test("CPI persistence is read from the stored calculation", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "CPI_U_INFLATION_AUTREGRESSION",
      primaryDatasetId: "bls.cu.CUSR0000SA0",
      calculation: {
        aic_lag: 2,
        persistence: 0.25,
        modelled_transformation: "monthly_log_change",
        persistence_estimator: "ols_sum_of_ar_coefficients",
        input_vintage: "latest_revised",
        product_forecast: false,
        empirically_qualified_as_forecast: false,
        andrews_chen_median_unbiased: false,
        growth_start: "1950-02-01",
        growth_end: "1951-01-01",
      },
    }),
  );
  assert.match(result.headline, /AIC lag 2/);
  assert.match(result.headline, /0\.25/);
  assert.match(result.standing, /Not a forecast/);
  assert.match(result.standing, /Not the Andrews–Chen median-unbiased estimator/);
  assert.match(result.limitations.join(" "), /monthly log change/);
  assert.equal(result.limitations.join(" ").includes("October 2025"), false);
  assert.equal(result.headline.includes("0.803"), false);
  assert.equal(result.publicationAllowed, false);
});

test("a CPI sample that ends in September 2025 records the missing October print", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "CPI_U_INFLATION_AUTREGRESSION",
      calculation: {
        aic_lag: 1,
        persistence: 0.1,
        growth_end: "2025-09-01",
        andrews_chen_median_unbiased: false,
        product_forecast: false,
        empirically_qualified_as_forecast: false,
        input_vintage: "latest_revised",
      },
    }),
  );
  assert.match(result.limitations.join(" "), /October 2025 CPI is missing/);
  assert.equal(result.headline.includes("0.803"), false);
});

test("the ex-post real rate is the stored identity and not a Taylor rule", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "EX_POST_REAL_FEDERAL_FUNDS_RATE",
      calculation: {
        latest_period: "1999-01-01",
        latest_federal_funds_rate_percent: "1.50",
        latest_cpi_u_inflation_percent: "1.25",
        latest_ex_post_real_rate_percentage_points: "0.25",
        not_taylor_rule: true,
        not_ex_ante: true,
        input_vintage: "latest_revised",
        months: [
          { period: "1998-12-01", ex_post_real_rate_percentage_points: "0.10" },
          { period: "1999-01-01", ex_post_real_rate_percentage_points: "0.25" },
        ],
      },
    }),
  );
  assert.match(result.headline, /1 January 1999/);
  assert.match(result.headline, /1\.5 percent/);
  assert.match(result.headline, /1\.25/);
  assert.match(result.headline, /0\.25 percentage points/);
  assert.match(result.standing, /Not a Taylor rule/);
  assert.match(result.standing, /Not an ex-ante real rate/);
  assert.equal(result.series?.points[1]?.value, 0.25);
  assert.equal(result.headline.includes("3.7173"), false);
  assert.equal(result.headline.includes("3.75"), false);
  assert.equal(result.publicationAllowed, false);
});

test("Engle–Granger reads the stored decision and stays non-causal", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "ENGLE_GRANGER_COINTEGRATION",
      calculation: {
        statistic: -1.5,
        critical_value_five_percent: -3.1,
        rejects_no_cointegration_at_five_percent: false,
        causal_claim: false,
        null_hypothesis: "no_cointegration",
        input_vintage: "latest_revised",
      },
    }),
  );
  assert.match(result.headline, /does not reject no-cointegration/);
  assert.match(result.headline, /-1\.5/);
  assert.match(result.headline, /-3\.1/);
  assert.match(result.standing, /Not causal/);
  assert.equal(result.series, null);
  assert.equal(result.headline.includes("-2.865"), false);
});

test("CUSUM reads the stored extreme and does not invent a break date", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "CUSUM_RECURSIVE_RESIDUALS",
      calculation: {
        crosses_conventional_boundary: false,
        maximum_absolute_cusum: 10.5,
        boundary_at_extreme: 20.25,
        extreme_period: "1980-01-01",
        selected_break_date: null,
        input_vintage: "latest_revised",
      },
    }),
  );
  assert.match(result.headline, /does not cross the five percent boundary/);
  assert.match(result.headline, /10\.5/);
  assert.match(result.headline, /1 January 1980/);
  assert.match(result.headline, /20\.25/);
  assert.match(result.standing, /Not a selected break date/);
  assert.equal(result.series, null);
  assert.equal(result.headline.includes("47.93"), false);
});

test("a V1 calculation without its figures says the result is unavailable", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "CPI_U_INFLATION_AUTREGRESSION",
      calculation: { input_vintage: "latest_revised" },
    }),
  );
  assert.equal(result.headline, "The stored result is unavailable.");
  assert.equal(result.headline.includes("0.803"), false);
  assert.equal(result.publicationAllowed, false);
});

test("the ex-post real funds rate is subsequent inflation and not a Taylor rule", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "EX_POST_REAL_FUNDS_RATE",
      calculation: {
        funds_month: "2019-01-01",
        inflation_end_month: "2020-01-01",
        federal_funds_percent_per_year: "2.50",
        inflation_percent: "1.25",
        real_funds_rate_percent_per_year: "1.25",
        taylor_rule: false,
        input_vintage: "latest_revised",
      },
    }),
  );
  assert.match(result.headline, /1\.25/);
  assert.match(result.standing, /Not a Taylor rule/);
  assert.match(result.standing, /Subsequent twelve-month inflation/);
  assert.equal(result.series, null);
  assert.equal(JSON.stringify(result).includes("Taylor rule recommendation"), false);
});

test("an accepted probit states it is not the New York Fed model", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT",
      calculation: {
        fit_status: "estimated",
        fit_stable: true,
        probabilities_accepted: true,
        intercept: "-0.4",
        spread_coefficient: "-0.8",
        new_york_fed_parameterisation: false,
        input_vintage: "latest_revised",
        probabilities: [
          { spread_quarter: "2006-01-01", window: "evaluation", probability: "0.2", nber_contraction: 0 },
          { spread_quarter: "2006-04-01", window: "evaluation", probability: "0.4", nber_contraction: 1 },
          { spread_quarter: "2005-10-01", window: "estimation", probability: "0.9", nber_contraction: 0 },
        ],
      },
    }),
  );
  assert.match(result.headline, /Intercept -0\.4/);
  assert.match(result.headline, /Spread coefficient -0\.8/);
  assert.match(result.standing, /Not the New York Fed model/);
  assert.match(result.standing, /Not the June 1996 Treasury-bill specification/);
  assert.equal(result.series?.frequency, "quarterly");
  assert.equal(result.series?.points.length, 2);
  assert.equal(result.series?.points.some((point) => point.period === "2005-10-01"), false);
  assert.equal(result.publicationAllowed, false);
});

test("an unstable probit does not present an unaccepted probability", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT",
      calculation: {
        fit_status: "unstable",
        fit_stable: false,
        fit_failure: "perfect_separation",
        probabilities_accepted: false,
        new_york_fed_parameterisation: false,
        input_vintage: "latest_revised",
        probabilities: [
          { spread_quarter: "2006-01-01", window: "evaluation", probability: "0.99", nber_contraction: 1 },
        ],
      },
    }),
  );
  const text = JSON.stringify(result);
  assert.match(result.headline, /Perfect separation/);
  assert.match(result.standing, /Not the New York Fed model/);
  assert.equal(result.series, null);
  assert.equal(text.includes("0.99"), false);
  assert.equal(result.facts.find((item) => item.label === "Probabilities accepted")?.value, "No");
});

test("the term spread is a yield difference and not a recession probability", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "ESTRELLA_MISHKIN_TERM_SPREAD",
      calculation: {
        evaluation_period: "2020-01-01",
        ten_year_yield: "1.80",
        three_month_yield: "1.50",
        spread: "0.30",
        real_time_probability: false,
        probit_estimated: false,
        input_vintage: "latest_revised",
      },
    }),
  );
  assert.match(result.headline, /0\.3/);
  assert.match(result.standing, /Not a recession probability/);
  assert.match(result.facts.map((item) => item.value).join(" "), /No/);
  assert.equal(JSON.stringify(result).toLowerCase().includes("recession probability is"), false);
  assert.equal(result.publicationAllowed, false);
});

test("an unknown method keeps the fallback sentence and invents no figure", () => {
  const result = extractPrivateResult(
    stored({
      methodId: "NOT_A_REGISTERED_PRESENTER",
      calculation: { invented: 1 },
      statisticalInterpretation: "Stored and unread.",
    }),
  );
  assert.equal(result.headline, "A stored run exists. This page has no reader for that calculation.");
  assert.match(result.standing, /No figure is invented for NOT_A_REGISTERED_PRESENTER/);
  assert.equal(result.series, null);
  assert.equal(result.facts.length, 0);
});
