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
  "HARDING_PAGAN_CHARACTERISTICS",
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
  "AUTOREGRESSIVE_BENCHMARK",
  "LEAD_LAG_CROSS_CORRELATION",
] as const;

test("the catalogue names the stored methods and every other programme row", () => {
  assert.equal(bry?.queryMethodIds.includes("BRY_BOSCHAN_SPENCER15_VARIANT"), true);
  assert.equal(factor?.outputKind, "time-series");
  assert.equal(bry?.stage, "in-development");
  assert.equal(factor?.stage, "in-development");
  const inDevelopment = METHODOLOGY_CATALOGUE.filter((entry) => entry.stage === "in-development")
    .map((entry) => entry.slug)
    .sort();
  assert.deepEqual(inDevelopment, [
    "autoregressive-benchmark",
    "bai-perron-breaks",
    "bry-boschan-spencer15",
    "diffusion-index",
    "hamilton-markov-switching",
    "harding-pagan-characteristics",
    "lead-lag",
    "stock-watson-1988",
  ]);
  const bbq = methodologyBySlug("harding-pagan-bbq");
  assert.equal(bbq?.stage, "planned");
  assert.deepEqual(bbq?.queryMethodIds, []);
  assert.equal(bbq?.registerId, "HARDING_PAGAN_BBQ");
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

test("unpublished diffusion and characteristics stay withheld", () => {
  const diffusion = methodologyBySlug("diffusion-index");
  const characteristics = methodologyBySlug("harding-pagan-characteristics");
  assert.ok(diffusion);
  assert.ok(characteristics);
  assert.deepEqual(diffusion.queryMethodIds, ["RESTRICTED_COINCIDENT_DIFFUSION"]);
  assert.deepEqual(characteristics.queryMethodIds, ["HARDING_PAGAN_CHARACTERISTICS"]);
  for (const entry of [diffusion, characteristics]) {
    const view = presentMethodology(entry, {
      status: "ready",
      runs: [run({ methodId: entry.queryMethodIds[0], publicationAllowed: false })],
    });
    const text = JSON.stringify(view);
    assert.match(view.statusLine, /not eligible for publication/);
    assert.match(text, /withheld/);
    assert.equal(text.includes("0.336"), false);
    assert.equal(text.includes("0.000629"), false);
    assert.equal("output" in view, false);
  }
  const bbq = methodologyBySlug("harding-pagan-bbq");
  assert.ok(bbq);
  const bbqView = presentMethodology(bbq, {
    status: "ready",
    runs: [run({ methodId: "HARDING_PAGAN_BBQ", publicationAllowed: true })],
  });
  assert.equal(bbqView.statusLine, "Planned.");
  assert.equal(JSON.stringify(bbqView).includes("HARDING_PAGAN_BBQ"), false);
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

test("unpublished batch 2 methods stay withheld", () => {
  const cases = [
    ["hamilton-markov-switching", "HAMILTON_MONTHLY_REGIME_SWITCHING"],
    ["bai-perron-breaks", "BAI_PERRON_MEAN_SHIFTS"],
    ["autoregressive-benchmark", "AUTOREGRESSIVE_BENCHMARK"],
    ["lead-lag", "LEAD_LAG_CROSS_CORRELATION"],
  ] as const;
  for (const [slug, methodId] of cases) {
    const entry = methodologyBySlug(slug);
    assert.ok(entry);
    assert.equal(entry.stage, "in-development");
    assert.deepEqual(entry.queryMethodIds, [methodId]);
    const view = presentMethodology(entry, {
      status: "ready",
      runs: [run({ methodId, publicationAllowed: false })],
    });
    const text = JSON.stringify(view);
    assert.match(view.statusLine, /not eligible for publication/);
    assert.match(text, /withheld/);
    assert.equal(text.includes("0.016"), false);
    assert.equal(text.includes("4629b31d"), false);
    assert.equal(text.includes("is a leading indicator"), false);
    assert.equal("output" in view, false);
  }
  const hamilton = methodologyBySlug("hamilton-markov-switching");
  const bai = methodologyBySlug("bai-perron-breaks");
  const benchmark = methodologyBySlug("autoregressive-benchmark");
  const leadLag = methodologyBySlug("lead-lag");
  assert.match(hamilton?.measures ?? "", /not a reproduction/);
  assert.match(bai?.measures ?? "", /not the general Bai–Perron regressor model/);
  assert.match(benchmark?.measures ?? "", /not a qualified forecast/);
  assert.match(leadLag?.measures ?? "", /no series receives leading-indicator status/);
  const bbq = methodologyBySlug("harding-pagan-bbq");
  assert.equal(bbq?.stage, "planned");
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
