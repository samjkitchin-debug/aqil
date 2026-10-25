import assert from "node:assert/strict";
import test from "node:test";

import { METHODOLOGY_CATALOGUE, methodologyBySlug } from "./methodology-catalogue.ts";
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

test("the catalogue names the two programme methodologies and no invented output", () => {
  assert.deepEqual(
    METHODOLOGY_CATALOGUE.map((entry) => entry.slug),
    ["bry-boschan-spencer15", "stock-watson-1988"],
  );
  assert.equal(bry?.queryMethodIds.includes("BRY_BOSCHAN_SPENCER15_VARIANT"), true);
  assert.equal(factor?.outputKind, "time-series");
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
