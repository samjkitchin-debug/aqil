import assert from "node:assert/strict";
import test from "node:test";

import { deployCapital, type ApprovedInstrument, type DeployCapitalInput } from "./deploy.ts";

const equity: ApprovedInstrument = {
  id: "example-world",
  name: "Example world equity",
  assetClass: "global_equity",
  currency: "SGD",
  minimumUnit: 1n,
  priceMinor: 3000n,
};

function input(overrides: Partial<DeployCapitalInput> = {}): DeployCapitalInput {
  return {
    reportingCurrency: "SGD",
    classValues: [{ assetClass: "global_equity", currency: "SGD", amountMinor: 0n }],
    targets: [{ assetClass: "global_equity", targetWeightBps: 10000 }],
    additionalCashMinor: 10001n,
    instruments: [equity],
    fx: [],
    ...overrides,
  };
}

test("unit rounding leaves the dust unallocated", () => {
  const result = deployCapital(input());
  assert.deepEqual(result.missing, []);
  assert.equal(result.instruments.length, 1);
  assert.equal(result.instruments[0]?.units, 3n);
  assert.equal(result.instruments[0]?.spendMinor, 9000n);
  assert.equal(result.unallocatedMinor, 1001n);
  assert.equal(result.exposures[0]?.deploymentMinor, 10001n);
});

test("an overweight class receives none of the new cash", () => {
  const result = deployCapital(
    input({
      classValues: [
        { assetClass: "global_equity", currency: "SGD", amountMinor: 8000n },
        { assetClass: "cash_investable", currency: "SGD", amountMinor: 2000n },
      ],
      targets: [
        { assetClass: "global_equity", targetWeightBps: 5000 },
        { assetClass: "cash_investable", targetWeightBps: 5000 },
      ],
      additionalCashMinor: 1000n,
      instruments: [
        equity,
        {
          id: "example-cash",
          name: "Example cash instrument",
          assetClass: "cash_investable",
          currency: "SGD",
          minimumUnit: 1n,
          priceMinor: 100n,
        },
      ],
    }),
  );
  const equityExposure = result.exposures.find((row) => row.assetClass === "global_equity");
  const cashExposure = result.exposures.find((row) => row.assetClass === "cash_investable");
  assert.equal(equityExposure?.side, "overweight");
  assert.equal(equityExposure?.deploymentMinor, 0n);
  assert.equal(cashExposure?.side, "underweight");
  assert.equal(cashExposure?.deploymentMinor, 1000n);
  assert.equal(
    result.instruments.some((row) => row.assetClass === "global_equity" && row.status === "planned"),
    false,
  );
});

test("a foreign instrument without a verified rate is unavailable", () => {
  const result = deployCapital(
    input({
      instruments: [{ ...equity, currency: "USD", priceMinor: 1000n }],
    }),
  );
  assert.equal(result.instruments[0]?.status, "unavailable");
  assert.equal(result.instruments[0]?.spendMinor, null);
  assert.match(result.instruments[0]?.reason ?? "", /fx USD to SGD/);
  assert.equal(result.unallocatedMinor, 10001n);
});

test("a zero budget is not configured", () => {
  const result = deployCapital(input({ additionalCashMinor: 0n }));
  assert.ok(result.missing.includes("investment budget"));
  assert.equal(result.instruments.length, 0);
  assert.equal(result.unallocatedMinor, null);
  assert.equal(result.exposures[0]?.deploymentMinor, 0n);
});

test("a missing budget is not configured", () => {
  const result = deployCapital(input({ additionalCashMinor: null }));
  assert.ok(result.missing.includes("investment budget"));
  assert.equal(result.exposures.length > 0, true);
  assert.equal(result.instruments.length, 0);
});

test("targets that do not total 10000 basis points are not configured", () => {
  const result = deployCapital(
    input({
      targets: [{ assetClass: "global_equity", targetWeightBps: 6000 }],
    }),
  );
  assert.deepEqual(result.missing, ["allocation targets"]);
  assert.equal(result.exposures.length, 0);
});

test("an empty approved list is not configured", () => {
  const result = deployCapital(input({ instruments: [] }));
  assert.ok(result.missing.includes("approved instruments"));
  assert.equal(result.instruments.length, 0);
  assert.equal(result.exposures[0]?.deploymentMinor, 10001n);
});

test("a held class with no target is overweight and receives no new cash", () => {
  const result = deployCapital(
    input({
      classValues: [
        { assetClass: "global_equity", currency: "SGD", amountMinor: 0n },
        { assetClass: "thematic_technology", currency: "SGD", amountMinor: 5000n },
      ],
      additionalCashMinor: 1000n,
      instruments: [equity],
    }),
  );
  const thematic = result.exposures.find((row) => row.assetClass === "thematic_technology");
  assert.equal(thematic?.targetWeightBps, 0);
  assert.equal(thematic?.side, "overweight");
  assert.equal(thematic?.deploymentMinor, 0n);
  assert.equal(result.instruments.some((row) => row.assetClass === "thematic_technology"), false);
});

test("listed instruments are filled in order and a per-unit cost is kept", () => {
  const result = deployCapital(
    input({
      additionalCashMinor: 250n,
      instruments: [
        { ...equity, id: "first", priceMinor: 100n, costMinorPerUnit: 0n },
        { ...equity, id: "second", name: "Example second", priceMinor: 40n },
      ],
    }),
  );
  assert.equal(result.instruments[0]?.id, "first");
  assert.equal(result.instruments[0]?.units, 2n);
  assert.equal(result.instruments[0]?.spendMinor, 200n);
  assert.equal(result.instruments[1]?.id, "second");
  assert.equal(result.instruments[1]?.units, 1n);
  assert.equal(result.instruments[1]?.spendMinor, 40n);
  assert.equal(result.unallocatedMinor, 10n);
});

test("a balanced book keeps a one-unit top-up as unallocated cash", () => {
  const result = deployCapital(
    input({
      classValues: [
        { assetClass: "global_equity", currency: "SGD", amountMinor: 5000n },
        { assetClass: "cash_investable", currency: "SGD", amountMinor: 5000n },
      ],
      targets: [
        { assetClass: "global_equity", targetWeightBps: 5000 },
        { assetClass: "cash_investable", targetWeightBps: 5000 },
      ],
      additionalCashMinor: 1n,
      instruments: [
        { ...equity, priceMinor: 1n },
        {
          id: "example-cash",
          name: "Example cash instrument",
          assetClass: "cash_investable",
          currency: "SGD",
          minimumUnit: 1n,
          priceMinor: 1n,
        },
      ],
    }),
  );
  assert.equal(result.exposures.every((row) => row.deploymentMinor === 0n), true);
  assert.equal(result.instruments.length, 0);
  assert.equal(result.unallocatedMinor, 1n);
});

test("converted unit totals stay inside the budget", () => {
  const result = deployCapital(
    input({
      additionalCashMinor: 40n,
      instruments: [{ ...equity, currency: "USD", priceMinor: 3n }],
      fx: [{ baseCurrency: "USD", quoteCurrency: "SGD", rate: "1.499" }],
    }),
  );
  const planned = result.instruments.find((row) => row.status === "planned");
  assert.equal(planned?.units, 9n);
  assert.equal(planned?.spendMinor, 40n);
  assert.equal(result.unallocatedMinor, 0n);
  assert.ok((planned?.spendMinor ?? 0n) <= 40n);
});
