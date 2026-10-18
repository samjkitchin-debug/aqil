import assert from "node:assert/strict";
import test from "node:test";

import { catalogueJson } from "./redact.ts";

test("catalogue keeps field types and drops identifier values", () => {
  const catalogue = catalogueJson({
    Data: [
      {
        AccountKey: "secret-account-key",
        AccountId: "192134INET",
        Currency: "USD",
        PositionBase: {
          Amount: 10,
          ExecutionTimeOpen: "2016-09-02T10:25:00Z",
          Uic: 31,
        },
      },
    ],
  });
  const serialised = JSON.stringify(catalogue);
  assert.equal(serialised.includes("secret-account-key"), false);
  assert.equal(serialised.includes("192134INET"), false);
  assert.equal(serialised.includes("USD"), false);
  const amount = catalogue.find((field) => field.path === "$.Data[].PositionBase.Amount");
  assert.equal(amount?.types.includes("number"), true);
  const opened = catalogue.find((field) => field.path === "$.Data[].PositionBase.ExecutionTimeOpen");
  assert.equal(opened?.isoTimestamp, true);
  const account = catalogue.find((field) => field.path === "$.Data[].AccountKey");
  assert.equal(account?.types.includes("string"), true);
  assert.equal(catalogue.some((field) => field.path.includes("Isin")), false);
});
