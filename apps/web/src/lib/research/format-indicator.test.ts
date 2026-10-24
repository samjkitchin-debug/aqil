import assert from "node:assert/strict";
import test from "node:test";

import { displayChange, displayLevel } from "./format-indicator.ts";

test("levels use readable units and keep a precise chart value", () => {
  const payrolls = displayLevel("159044", "thousands", "jobs");
  assert.equal(payrolls?.headline, "159.0 million jobs");
  assert.equal(payrolls?.precise, "159.044 million jobs");
  assert.equal(payrolls?.axisUnit, "Million jobs");
  const unnamed = displayLevel("159044", "thousands");
  assert.equal(unnamed?.axisUnit, "Thousands");
  assert.equal(unnamed?.rescaled, false);
  assert.equal(payrolls?.chartValue, 159.044);

  const openings = displayLevel("7079", "thousands", "openings");
  assert.equal(openings?.headline, "7.08 million job openings");
  assert.equal(openings?.precise, "7.079 million job openings");
  assert.equal(openings?.axisUnit, "Million job openings");

  const credit = displayLevel("19948526.8", "usd_millions");
  assert.equal(credit?.headline, "$19.95 trillion");
  assert.equal(credit?.axisUnit, "US$ trillion");
  assert.ok(Math.abs((credit?.chartValue ?? 0) - 19.9485268) < 1e-6);

  const hicp = displayLevel("129.7338491760366", "index, 2015 = 100");
  assert.equal(hicp?.headline, "129.7");
  assert.equal(hicp?.precise, "129.73");
  assert.equal(hicp?.beside, "Index (2015 = 100)");

  const prices = displayLevel("336.298", "1982-84=100");
  assert.equal(prices?.headline, "336.298");
  assert.equal(prices?.beside, "Index (1982–84 = 100)");

  const output = displayLevel("103.9506", "index_2017_100");
  assert.equal(output?.headline, "103.95");
  assert.equal(output?.beside, "Index (2017 = 100)");

  assert.equal(displayLevel("4.2", "percent")?.headline, "4.2%");
  assert.equal(displayLevel("3.75", "percent_per_year")?.headline, "3.75% per year");
  assert.equal(displayLevel("0.0", "percent_net_tightening")?.headline, "0.0% net tightening");
});

test("changes use percentage points, jobs, openings, dollars or index points", () => {
  assert.equal(displayChange("0.1", "percent"), "+0.1 percentage points");
  assert.equal(displayChange("0.12", "percent_per_year"), "+0.12 percentage points");
  assert.equal(displayChange("-8.1", "percent_net_tightening"), "-8.1 percentage points");
  assert.equal(displayChange("0", "percent"), "Unchanged");
  assert.equal(displayChange("29", "thousands", "jobs"), "+29,000 jobs");
  assert.equal(displayChange("-256", "thousands", "openings"), "-256,000 job openings");
  assert.equal(displayChange("0.001", "thousands", "jobs"), "+1 job");
  assert.equal(displayChange("29", "thousands"), "+29 thousand");
  assert.equal(displayChange("57132", "usd_millions"), "+$57.13 billion");
  assert.equal(displayChange("2.167", "1982-84=100"), "+2.167 index points");
  assert.equal(displayChange("0.6842", "index_2017_100"), "+0.68 index points");
  assert.equal(displayChange("0.06066122519262", "index, 2015 = 100"), "+0.06 index points");
  assert.equal(displayChange("not-a-number", "percent"), null);
});
