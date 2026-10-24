import assert from "node:assert/strict";
import test from "node:test";

import { JOURNAL_NOT_SAXO, WEALTH_UNKNOWNS } from "./wealth-limits.ts";

test("My Wealth states the missing contribution split, benchmark and return", () => {
  assert.match(WEALTH_UNKNOWNS, /Contributions are not separated from account value/);
  assert.match(WEALTH_UNKNOWNS, /includes contributions and is not investment return/);
  assert.match(WEALTH_UNKNOWNS, /No cashflow-matched benchmark is stored/);
  assert.match(WEALTH_UNKNOWNS, /Money-weighted return is not shown on this page/);
  assert.match(WEALTH_UNKNOWNS, /not the Saxo ledger/);
  assert.doesNotMatch(WEALTH_UNKNOWNS, /\d/);
});

test("the manual journal is not described as the Saxo ledger", () => {
  assert.equal(JOURNAL_NOT_SAXO, "This journal is a manual record. It is not the Saxo ledger.");
});
