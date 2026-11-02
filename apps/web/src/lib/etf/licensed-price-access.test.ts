import assert from "node:assert/strict";
import test from "node:test";

import { licensedEtfPricesAllowed, LICENSED_PRICE_WITHHELD } from "./licensed-price-access.ts";

test("ordinary sign-in cannot read licensed ETF prices", () => {
  assert.equal(licensedEtfPricesAllowed("none"), false);
  assert.match(LICENSED_PRICE_WITHHELD, /founder session/);
  assert.match(LICENSED_PRICE_WITHHELD, /Ordinary sign-in is not enough/);
});

test("the founder claim can read licensed ETF prices", () => {
  assert.equal(licensedEtfPricesAllowed("founder"), true);
});
