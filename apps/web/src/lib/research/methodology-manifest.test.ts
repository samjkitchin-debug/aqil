import assert from "node:assert/strict";
import test from "node:test";

import { METHODOLOGY_CATALOGUE } from "./methodology-catalogue.ts";
import { METHODOLOGY_BINDINGS, bindingForMethod } from "./methodology-manifest.ts";
import { methodologyPresenters } from "./private-methodology-result.ts";

test("catalogue method ids, empty states, and presenters share one manifest", () => {
  for (const entry of METHODOLOGY_CATALOGUE) {
    for (const methodId of entry.queryMethodIds) {
      const binding = bindingForMethod(methodId);
      assert.ok(binding, methodId);
      assert.equal(binding.catalogueSlug, entry.slug);
    }
  }
  const presenterKeys = Object.keys(methodologyPresenters).sort();
  const boundPresenters = METHODOLOGY_BINDINGS.flatMap((row) => (row.presenterKey === row.methodId ? [row.methodId] : [])).sort();
  assert.deepEqual(boundPresenters, presenterKeys);
});
