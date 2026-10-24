import assert from "node:assert/strict";
import test from "node:test";

import {
  ETF_DATABASE_LOCAL_ONLY,
  ETF_DATABASE_UNAVAILABLE,
  RESEARCH_DATABASE_LOCAL_REFUSED,
  RESEARCH_DATABASE_UNAVAILABLE,
  resolveEtfDatabaseUrl,
  resolveResearchDatabaseUrl,
} from "./private-database-url.ts";

const LOCAL_RESEARCH = "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres";
const LOCAL_ETF = "postgresql://research_worker:research_worker@127.0.0.1:55432/aqil_etf";
const HOSTED = "postgresql://research_worker:secret@db.example:5432/research";

test("development keeps the local research default only when the URL is unset", () => {
  assert.deepEqual(resolveResearchDatabaseUrl({ nodeEnv: "development", configuredUrl: undefined }), {
    status: "configured",
    url: LOCAL_RESEARCH,
  });
  assert.deepEqual(resolveResearchDatabaseUrl({ nodeEnv: "test", configuredUrl: "  " }), {
    status: "configured",
    url: LOCAL_RESEARCH,
  });
});

test("development uses an explicit research URL", () => {
  assert.deepEqual(resolveResearchDatabaseUrl({ nodeEnv: "development", configuredUrl: HOSTED }), {
    status: "configured",
    url: HOSTED,
  });
});

test("production does not fall back to the local research database", () => {
  assert.deepEqual(resolveResearchDatabaseUrl({ nodeEnv: "production", configuredUrl: undefined }), {
    status: "unavailable",
    reason: RESEARCH_DATABASE_UNAVAILABLE,
  });
  assert.deepEqual(resolveResearchDatabaseUrl({ nodeEnv: "production", configuredUrl: "" }), {
    status: "unavailable",
    reason: RESEARCH_DATABASE_UNAVAILABLE,
  });
  assert.deepEqual(resolveResearchDatabaseUrl({ nodeEnv: "production", configuredUrl: LOCAL_RESEARCH }), {
    status: "unavailable",
    reason: RESEARCH_DATABASE_LOCAL_REFUSED,
  });
  const resolved = resolveResearchDatabaseUrl({ nodeEnv: "production", configuredUrl: undefined });
  assert.equal(resolved.status === "configured" ? resolved.url : "", "");
});

test("production uses a configured non-local research URL", () => {
  assert.deepEqual(resolveResearchDatabaseUrl({ nodeEnv: "production", configuredUrl: `  ${HOSTED}  ` }), {
    status: "configured",
    url: HOSTED,
  });
  assert.deepEqual(
    resolveResearchDatabaseUrl({
      nodeEnv: "production",
      configuredUrl: "postgresql://research_worker:x@[2001:db8::1]:5432/research",
    }),
    {
      status: "configured",
      url: "postgresql://research_worker:x@[2001:db8::1]:5432/research",
    },
  );
});

test("production refuses loopback spellings other than 127.0.0.1", () => {
  const localUrls = [
    "postgresql://research_worker:research_worker@127.0.0.2:55432/postgres",
    "postgresql://research_worker:x@[::1]:55432/postgres",
    "postgresql://research_worker:x@[::ffff:127.0.0.1]:55432/postgres",
    "postgresql://research_worker:x@0.0.0.0:55432/postgres",
    "postgresql://research_worker:x@[::]:55432/postgres",
  ];
  for (const configuredUrl of localUrls) {
    assert.deepEqual(resolveResearchDatabaseUrl({ nodeEnv: "production", configuredUrl }), {
      status: "unavailable",
      reason: RESEARCH_DATABASE_LOCAL_REFUSED,
    });
    assert.deepEqual(resolveEtfDatabaseUrl({ nodeEnv: "production", configuredUrl }), {
      status: "unavailable",
      reason: RESEARCH_DATABASE_LOCAL_REFUSED,
    });
  }
});

test("development keeps the local ETF default and refuses other addresses", () => {
  assert.deepEqual(resolveEtfDatabaseUrl({ nodeEnv: "development", configuredUrl: undefined }), {
    status: "configured",
    url: LOCAL_ETF,
  });
  assert.deepEqual(resolveEtfDatabaseUrl({ nodeEnv: "development", configuredUrl: HOSTED }), {
    status: "unavailable",
    reason: ETF_DATABASE_LOCAL_ONLY,
  });
});

test("production does not fall back to the local ETF database", () => {
  assert.deepEqual(resolveEtfDatabaseUrl({ nodeEnv: "production", configuredUrl: undefined }), {
    status: "unavailable",
    reason: ETF_DATABASE_UNAVAILABLE,
  });
  assert.deepEqual(resolveEtfDatabaseUrl({ nodeEnv: "production", configuredUrl: LOCAL_ETF }), {
    status: "unavailable",
    reason: RESEARCH_DATABASE_LOCAL_REFUSED,
  });
  assert.deepEqual(resolveEtfDatabaseUrl({ nodeEnv: "production", configuredUrl: HOSTED }), {
    status: "configured",
    url: HOSTED,
  });
});
