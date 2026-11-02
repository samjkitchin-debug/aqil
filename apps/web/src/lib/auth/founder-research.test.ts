import assert from "node:assert/strict";
import test from "node:test";

import { researchAuthorisationFromMetadata } from "./session-policy.ts";

test("a signed-out claim is not founder access", () => {
  assert.equal(researchAuthorisationFromMetadata(undefined), "none");
  assert.equal(researchAuthorisationFromMetadata(null), "none");
});

test("a signed-in account without the claim stays unauthorised", () => {
  assert.equal(researchAuthorisationFromMetadata({ provider: "google" }), "none");
  assert.equal(researchAuthorisationFromMetadata({ aqil_research: "reader" }), "none");
  assert.equal(researchAuthorisationFromMetadata({ email: "founder@example.com" }), "none");
});

test("the founder claim is the account role, not an email", () => {
  assert.equal(researchAuthorisationFromMetadata({ aqil_research: "founder" }), "founder");
});
