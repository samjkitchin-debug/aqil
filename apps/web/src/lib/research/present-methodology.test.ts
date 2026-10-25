import assert from "node:assert/strict";
import test from "node:test";

import {
  EXCLUDED_REGISTER_ROWS,
  METHODOLOGY_CATALOGUE,
  methodologyBySlug,
} from "./methodology-catalogue.ts";
import { presentMethodology, type MethodologyRunMeta } from "./present-methodology.ts";

const bry = methodologyBySlug("bry-boschan-spencer15");
const factor = methodologyBySlug("stock-watson-1988");

function run(overrides: Partial<MethodologyRunMeta> = {}): MethodologyRunMeta {
  return {
    methodId: "BRY_BOSCHAN_SPENCER15_VARIANT",
    methodVersion: "1.0.0",
    executedAt: "2026-10-25T08:00:00.000Z",
    executionStatus: "completed",
    publicationAllowed: false,
    dataSufficiency: "sufficient",
    ...overrides,
  };
}

function prose(entrySlug: string, runs: MethodologyRunMeta[]): string {
  const entry = methodologyBySlug(entrySlug);
  assert.ok(entry);
  return JSON.stringify(presentMethodology(entry, { status: "ready", runs }));
}

const REGISTER_ROWS = [
  "BRY_BOSCHAN_MONTHLY",
  "STOCK_WATSON_DFM",
  "STATIC_PCA",
  "CFNAI",
  "KALMAN_FILTER",
  "DIFFUSION_INDEX",
  "HARDING_PAGAN_BBQ",
  "MIXED_FREQUENCY_NOWCAST",
  "HAMILTON_MARKOV_SWITCHING",
  "YIELD_CURVE_PROBIT",
  "FINANCIAL_CONDITIONS",
  "GILCHRIST_ZAKRAJSEK_EBP",
  "BIS_CREDIT_GAP",
  "GROWTH_AT_RISK",
  "INFLATION_TREND",
  "PHILLIPS_CURVE",
  "BAI_PERRON_BREAKS",
  "ADVANCED_FORECASTING",
  "PORTFOLIO_RESEARCH",
] as const;

test("the catalogue keeps the two in-development methods and names every other programme row", () => {
  assert.equal(bry?.queryMethodIds.includes("BRY_BOSCHAN_SPENCER15_VARIANT"), true);
  assert.equal(factor?.outputKind, "time-series");
  assert.equal(bry?.stage, "in-development");
  assert.equal(factor?.stage, "in-development");
  const shown = new Set(METHODOLOGY_CATALOGUE.map((entry) => entry.registerId));
  const excluded = new Set(EXCLUDED_REGISTER_ROWS.map((row) => row.id));
  assert.deepEqual(
    REGISTER_ROWS.filter((id) => !shown.has(id)).sort(),
    [...excluded].sort(),
  );
  for (const id of REGISTER_ROWS) {
    assert.equal(shown.has(id) !== excluded.has(id), true, id);
  }
  const slugs = METHODOLOGY_CATALOGUE.map((entry) => entry.slug);
  assert.equal(new Set(slugs).size, slugs.length);
});

test("planned methods have no run query and no fabricated result", () => {
  const planned = METHODOLOGY_CATALOGUE.filter((entry) => entry.stage === "planned");
  assert.equal(planned.length > 0, true);
  for (const entry of planned) {
    assert.deepEqual(entry.queryMethodIds, []);
    const view = presentMethodology(entry, {
      status: "ready",
      runs: [run({ methodId: entry.registerId, publicationAllowed: true })],
    });
    const text = JSON.stringify(view);
    assert.equal(view.statusLine, "Planned.");
    assert.equal(view.latestLine, null);
    assert.match(text, /has not calculated/);
    assert.equal(text.includes(entry.registerId), false);
    assert.equal(/\d+\.\d{3}/.test(text), false);
  }
});

test("a closed publication withholds calculated output", () => {
  assert.ok(bry);
  const view = presentMethodology(bry, { status: "ready", runs: [run()] });
  const text = JSON.stringify(view);
  assert.match(view.statusLine, /not eligible for publication/);
  assert.match(text, /withheld/);
  assert.equal(text.includes("18 peaks"), false);
  assert.equal(text.includes("likelihood"), false);
  assert.equal(text.includes("0.907"), false);
  assert.equal("output" in view, false);
});

test("an eligible run still has no presenter", () => {
  assert.ok(bry);
  const view = presentMethodology(bry, {
    status: "ready",
    runs: [run({ publicationAllowed: true })],
  });
  assert.match(view.statusLine, /no presenter/);
  const current = view.sections.find((section) => section.id === "current-result");
  assert.match(current?.paragraphs.join(" ") ?? "", /stay hidden/);
});

test("Stock–Watson without a run does not invent a factor", () => {
  const text = prose("stock-watson-1988", []);
  assert.match(text, /No stored run matches this methodology/);
  assert.equal(text.includes("converged"), false);
  assert.match(text, /not selected/);
});

test("run metadata failure is stated and not replaced with a result", () => {
  assert.ok(factor);
  const view = presentMethodology(factor, {
    status: "unavailable",
    reason: "Methodology run metadata could not be read.",
  });
  assert.equal(view.statusLine, "Methodology run metadata could not be read.");
  const current = view.sections.find((section) => section.id === "current-result");
  assert.match(current?.paragraphs.join(" ") ?? "", /No output is invented/);
});
