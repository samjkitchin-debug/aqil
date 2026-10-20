import assert from "node:assert/strict";
import test from "node:test";

import {
  compareCashflowMatchedPassive,
  type CashflowMatchedInput,
} from "./cashflow-matched.ts";

/** Synthetic fixture levels. Not a market index. */
function supplied(overrides: Partial<CashflowMatchedInput> = {}): CashflowMatchedInput {
  return {
    cashflows: [
      {
        cashflowId: "contribution-1",
        occurredOn: "2024-03-01",
        amountMinor: 10_000n,
        currency: "SGD",
      },
    ],
    benchmarkSeries: [
      { occurredOn: "2024-03-01", level: "74.00", currency: "USD" },
      { occurredOn: "2024-04-01", level: "80.00", currency: "USD" },
    ],
    fx: {
      rates: [
        {
          occurredOn: "2024-03-01",
          baseCurrency: "SGD",
          quoteCurrency: "USD",
          rate: "0.74",
        },
      ],
    },
    costs: { entryCostBps: "100", exitCostBps: "0" },
    valuationDate: "2024-04-01",
    reportingCurrency: "USD",
    portfolioEndingValueMinor: 8_000n,
    ...overrides,
  };
}

test("comparison stays unavailable until series, foreign exchange and costs are supplied", () => {
  const missingSeries = compareCashflowMatchedPassive(supplied({ benchmarkSeries: undefined }));
  assert.equal(missingSeries.status, "unavailable");
  assert.equal(missingSeries.reason, "Benchmark series was not supplied.");
  assert.equal("passiveEndingValueMinor" in missingSeries, false);

  const missingFx = compareCashflowMatchedPassive(supplied({ fx: undefined }));
  assert.equal(missingFx.status, "unavailable");
  assert.equal(missingFx.reason, "Foreign-exchange assumptions were not supplied.");

  const missingCosts = compareCashflowMatchedPassive(supplied({ costs: undefined }));
  assert.equal(missingCosts.status, "unavailable");
  assert.equal(missingCosts.reason, "Cost assumptions were not supplied.");
});

test("matched dates, costs and foreign exchange reproduce the passive value", () => {
  const comparison = compareCashflowMatchedPassive(supplied());
  assert.equal(comparison.status, "available");
  if (comparison.status !== "available") return;

  assert.equal(comparison.execution, "same-day");
  assert.equal(comparison.legs.length, 1);
  assert.equal(comparison.legs[0]?.occurredOn, "2024-03-01");
  assert.equal(comparison.legs[0]?.benchmarkDate, "2024-03-01");
  assert.equal(comparison.legs[0]?.fxDate, "2024-03-01");
  assert.equal(comparison.legs[0]?.costBps, "100");
  assert.equal(comparison.costs.entryCostBps, "100");
  assert.equal(comparison.costs.exitCostBps, "0");
  assert.match(comparison.assumptions.join(" "), /100 basis points/);
  assert.equal(comparison.passiveUnits, "0.99000000");
  assert.equal(comparison.benchmarkLevelOnValuationDate, "80.00");
  assert.equal(comparison.passiveEndingValueMinor, 7_920n);
  assert.equal(comparison.portfolioEndingValueMinor, 8_000n);
  assert.equal(comparison.valueDifferenceMinor, 80n);
  assert.equal("return" in comparison, false);
});

test("a foreign-exchange rate on another date is not used", () => {
  const comparison = compareCashflowMatchedPassive(
    supplied({
      fx: {
        rates: [
          {
            occurredOn: "2024-03-02",
            baseCurrency: "SGD",
            quoteCurrency: "USD",
            rate: "0.74",
          },
        ],
      },
    }),
  );
  assert.equal(comparison.status, "unavailable");
  if (comparison.status !== "unavailable") return;
  assert.match(comparison.reason, /does not match the cashflow date/);
  assert.equal("passiveEndingValueMinor" in comparison, false);
});

test("a benchmark level on another date is not used", () => {
  const comparison = compareCashflowMatchedPassive(
    supplied({
      benchmarkSeries: [
        { occurredOn: "2024-03-02", level: "74.00", currency: "USD" },
        { occurredOn: "2024-04-01", level: "80.00", currency: "USD" },
      ],
    }),
  );
  assert.equal(comparison.status, "unavailable");
  if (comparison.status !== "unavailable") return;
  assert.match(comparison.reason, /Benchmark level date does not match 2024-03-01/);
});

test("an opposite foreign-exchange rate is not inverted", () => {
  const comparison = compareCashflowMatchedPassive(
    supplied({
      fx: {
        rates: [
          {
            occurredOn: "2024-03-01",
            baseCurrency: "USD",
            quoteCurrency: "SGD",
            rate: "1.3513513514",
          },
        ],
      },
    }),
  );
  assert.equal(comparison.status, "unavailable");
  if (comparison.status !== "unavailable") return;
  assert.match(comparison.reason, /missing on 2024-03-01 from SGD to USD/);
});

test("same-currency identity does not invent a rate, but foreign exchange must still be supplied", () => {
  const base: CashflowMatchedInput = {
    cashflows: [
      {
        cashflowId: "contribution-1",
        occurredOn: "2024-01-02",
        amountMinor: 10_000n,
        currency: "USD",
      },
    ],
    benchmarkSeries: [
      { occurredOn: "2024-01-02", level: "100", currency: "USD" },
      { occurredOn: "2024-02-02", level: "110", currency: "USD" },
    ],
    fx: { rates: [] },
    costs: { entryCostBps: "0", exitCostBps: "0" },
    valuationDate: "2024-02-02",
    reportingCurrency: "USD",
    portfolioEndingValueMinor: 11_000n,
  };
  const comparison = compareCashflowMatchedPassive(base);
  assert.equal(comparison.status, "available");
  if (comparison.status !== "available") return;
  assert.equal(comparison.legs[0]?.fxDate, null);
  assert.equal(comparison.passiveUnits, "1.00000000");
  assert.equal(comparison.passiveEndingValueMinor, 11_000n);
  assert.equal(comparison.valueDifferenceMinor, 0n);

  const omitted = compareCashflowMatchedPassive({ ...base, fx: undefined });
  assert.equal(omitted.status, "unavailable");
});

test("exit cost and same-day ordering follow the stated rules", () => {
  const withExit = compareCashflowMatchedPassive({
    cashflows: [
      {
        cashflowId: "in",
        occurredOn: "2024-05-01",
        amountMinor: 10_000n,
        currency: "USD",
      },
      {
        cashflowId: "out",
        occurredOn: "2024-05-02",
        amountMinor: -5_000n,
        currency: "USD",
      },
    ],
    benchmarkSeries: [
      { occurredOn: "2024-05-01", level: "100", currency: "USD" },
      { occurredOn: "2024-05-02", level: "100", currency: "USD" },
      { occurredOn: "2024-06-01", level: "100", currency: "USD" },
    ],
    fx: { rates: [] },
    costs: { entryCostBps: "0", exitCostBps: "100" },
    valuationDate: "2024-06-01",
    reportingCurrency: "USD",
    portfolioEndingValueMinor: 4_949n,
  });
  assert.equal(withExit.status, "available");
  if (withExit.status !== "available") return;
  assert.equal(withExit.passiveUnits, "0.49490000");
  assert.equal(withExit.passiveEndingValueMinor, 4_949n);
  assert.equal(withExit.valueDifferenceMinor, 0n);
  assert.equal(withExit.legs[1]?.benchmarkDate, "2024-05-02");
  assert.equal(withExit.legs[1]?.costBps, "100");

  const sameDay = compareCashflowMatchedPassive({
    cashflows: [
      {
        cashflowId: "out",
        occurredOn: "2024-05-01",
        amountMinor: -10_000n,
        currency: "USD",
      },
      {
        cashflowId: "in",
        occurredOn: "2024-05-01",
        amountMinor: 10_000n,
        currency: "USD",
      },
    ],
    benchmarkSeries: [
      { occurredOn: "2024-05-01", level: "100", currency: "USD" },
      { occurredOn: "2024-06-01", level: "100", currency: "USD" },
    ],
    fx: { rates: [] },
    costs: { entryCostBps: "0", exitCostBps: "0" },
    valuationDate: "2024-06-01",
    reportingCurrency: "USD",
    portfolioEndingValueMinor: 0n,
  });
  assert.equal(sameDay.status, "available");
  if (sameDay.status !== "available") return;
  assert.equal(sameDay.passiveEndingValueMinor, 0n);
  assert.deepEqual(
    sameDay.legs.map((leg) => leg.cashflowId),
    ["in", "out"],
  );
});

test("a withdrawal larger than the passive holding stays unavailable", () => {
  const comparison = compareCashflowMatchedPassive({
    cashflows: [
      {
        cashflowId: "in",
        occurredOn: "2024-06-01",
        amountMinor: 10_000n,
        currency: "USD",
      },
      {
        cashflowId: "out",
        occurredOn: "2024-06-02",
        amountMinor: -20_000n,
        currency: "USD",
      },
    ],
    benchmarkSeries: [
      { occurredOn: "2024-06-01", level: "100", currency: "USD" },
      { occurredOn: "2024-06-02", level: "100", currency: "USD" },
    ],
    fx: { rates: [] },
    costs: { entryCostBps: "0", exitCostBps: "0" },
    valuationDate: "2024-06-02",
    reportingCurrency: "USD",
    portfolioEndingValueMinor: 0n,
  });
  assert.equal(comparison.status, "unavailable");
  if (comparison.status !== "unavailable") return;
  assert.match(comparison.reason, /Withdrawal exceeds passive units/);
});

test("different minor-unit scales stay unavailable", () => {
  const comparison = compareCashflowMatchedPassive(
    supplied({
      cashflows: [
        {
          cashflowId: "contribution-1",
          occurredOn: "2024-03-01",
          amountMinor: 10_000n,
          currency: "JPY",
        },
      ],
      fx: {
        rates: [
          {
            occurredOn: "2024-03-01",
            baseCurrency: "JPY",
            quoteCurrency: "USD",
            rate: "0.01",
          },
        ],
      },
    }),
  );
  assert.equal(comparison.status, "unavailable");
  if (comparison.status !== "unavailable") return;
  assert.match(comparison.reason, /Minor-unit scales differ between JPY and USD/);
});

test("reporting-currency conversion uses only the valuation-date rate", () => {
  const comparison = compareCashflowMatchedPassive(
    supplied({
      reportingCurrency: "SGD",
      portfolioEndingValueMinor: 9_900n,
      fx: {
        rates: [
          {
            occurredOn: "2024-03-01",
            baseCurrency: "SGD",
            quoteCurrency: "USD",
            rate: "0.74",
          },
          {
            occurredOn: "2024-04-01",
            baseCurrency: "USD",
            quoteCurrency: "SGD",
            rate: "1.25",
          },
        ],
      },
    }),
  );
  assert.equal(comparison.status, "available");
  if (comparison.status !== "available") return;
  assert.equal(comparison.passiveEndingValueMinor, 9_900n);
  assert.equal(comparison.valueDifferenceMinor, 0n);

  const missingValuationRate = compareCashflowMatchedPassive(
    supplied({
      reportingCurrency: "SGD",
      portfolioEndingValueMinor: 9_900n,
    }),
  );
  assert.equal(missingValuationRate.status, "unavailable");
  if (missingValuationRate.status !== "unavailable") return;
  assert.match(missingValuationRate.reason, /missing on 2024-04-01 from USD to SGD/);
});
