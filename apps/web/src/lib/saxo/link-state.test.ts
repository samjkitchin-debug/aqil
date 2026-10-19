import assert from "node:assert/strict";
import test from "node:test";

import { classifySaxoLink } from "./link-state.ts";

test("an unexpired access token is an active connection", () => {
  assert.equal(classifySaxoLink({ accessExpiresAt: 2_000, refreshExpiresAt: 5_000 }, 1_000), "active");
});

test("a valid refresh token with an expired access token can still be refreshed", () => {
  assert.equal(classifySaxoLink({ accessExpiresAt: 1_000, refreshExpiresAt: 5_000 }, 1_500), "refreshable");
});

test("an expired refresh token needs a new sign-in", () => {
  assert.equal(classifySaxoLink({ accessExpiresAt: 1_000, refreshExpiresAt: 1_200 }, 1_500), "expired");
});

test("a missing session is absent", () => {
  assert.equal(classifySaxoLink(null, 1_500), "absent");
});
