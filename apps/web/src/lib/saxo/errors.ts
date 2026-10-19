export const MAX_RETRY_WAIT_MS = 5_000;
export const MAX_TRANSPORT_RETRIES = 3;

export type SaxoErrorKind =
  | "ok"
  | "invalid_window"
  | "malformed"
  | "absent"
  | "not_found"
  | "unauthorised"
  | "forbidden"
  | "rate_limited"
  | "outage";

export type SaxoErrorAction = "accept" | "stop" | "retry" | "refresh";

export type ClassifiedSaxoError = {
  kind: SaxoErrorKind;
  errorCode: string | null;
  action: SaxoErrorAction;
};

/** Reads a Saxo or OAuth error code. Descriptions are ignored because they can echo request data. */
export function saxoErrorCode(body: unknown): string | null {
  const record = asRecord(body);
  if (!record) return null;
  const direct = text(record.ErrorCode) ?? text(record.error);
  if (direct) return direct;
  const info = asRecord(record.ErrorInfo);
  return text(info?.ErrorCode);
}

export function classifySaxoResponse(input: {
  status: number;
  body: unknown;
  endpointFamily: string;
}): ClassifiedSaxoError {
  const errorCode = saxoErrorCode(input.body);
  if (input.status === 200) return { kind: "ok", errorCode, action: "accept" };
  if (input.status === 401) return { kind: "unauthorised", errorCode, action: "refresh" };
  if (input.status === 403) return { kind: "forbidden", errorCode, action: "stop" };
  if (input.status === 429) return { kind: "rate_limited", errorCode, action: "retry" };
  if (input.status === 503 || input.status === 0) return { kind: "outage", errorCode, action: "retry" };
  if (input.status === 404 && input.endpointFamily === "/hist/v3/perf") {
    return { kind: "absent", errorCode, action: "stop" };
  }
  if (input.status === 404) return { kind: "not_found", errorCode, action: "stop" };
  if (input.status === 400 && (errorCode === "InvalidDateRange" || errorCode === "InvalidYear")) {
    return { kind: "invalid_window", errorCode, action: "stop" };
  }
  if (input.status === 400) return { kind: "malformed", errorCode, action: "stop" };
  return { kind: "malformed", errorCode, action: "stop" };
}

/** A delay above this stays out of the current request and is resumed later. */
export function retryPlan(retryAfter: string | null, attempt: number): { waitMs: number; defer: boolean } {
  const instructed = retryAfterSeconds(retryAfter);
  if (instructed !== null) {
    const waitMs = instructed * 1_000;
    return { waitMs, defer: waitMs > MAX_RETRY_WAIT_MS };
  }
  return { waitMs: Math.min(250 * (attempt + 1), MAX_RETRY_WAIT_MS), defer: false };
}

export function retryWaitMs(retryAfter: string | null, attempt: number): number {
  return retryPlan(retryAfter, attempt).waitMs;
}

export function readQuota(headers: { get(name: string): string | null } | undefined): { remaining: number | null; resetMs: number | null } {
  if (!headers) return { remaining: null, resetMs: null };
  const remaining = headerNumber(headers, ["x-ratelimit-remaining", "X-RateLimit-Remaining"]);
  const reset = headerNumber(headers, ["x-ratelimit-reset", "X-RateLimit-Reset"]);
  if (reset === null) return { remaining, resetMs: null };
  const resetMs = reset > 1_000_000_000 ? reset * 1_000 : Date.now() + reset * 1_000;
  return { remaining, resetMs };
}

/** Leave spare quota. A long reset is deferred instead of being slept through. */
export function quotaPace(remaining: number | null, resetMs: number | null, nowMs: number): { waitMs: number; defer: boolean } {
  if (remaining === null || remaining > 8) return { waitMs: 400, defer: false };
  if (resetMs === null) return { waitMs: 5_000, defer: false };
  const waitMs = Math.max(0, resetMs - nowMs + 250);
  return { waitMs, defer: waitMs > 20_000 };
}

export async function attemptClassified(input: {
  endpointFamily: string;
  call: () => Promise<{ status: number; body: unknown; retryAfter: string | null; rateRemaining?: number | null; rateResetMs?: number | null }>;
  sleep: (ms: number) => Promise<void>;
  refresh: () => Promise<boolean>;
}): Promise<{ status: number; body: unknown; classification: ClassifiedSaxoError; attempts: number; deferredMs: number | null; rateRemaining: number | null; rateResetMs: number | null }> {
  let refreshed = false;
  let transportRetries = 0;
  let attempts = 0;
  let last: { status: number; body: unknown; classification: ClassifiedSaxoError; deferredMs: number | null; rateRemaining: number | null; rateResetMs: number | null } = {
    status: 0,
    body: null,
    classification: { kind: "outage", errorCode: null, action: "stop" },
    deferredMs: null,
    rateRemaining: null,
    rateResetMs: null,
  };
  while (attempts < MAX_TRANSPORT_RETRIES + 2) {
    attempts += 1;
    const response = await input.call();
    const classification = classifySaxoResponse({
      status: response.status,
      body: response.body,
      endpointFamily: input.endpointFamily,
    });
    last = {
      status: response.status,
      body: response.body,
      classification,
      deferredMs: null,
      rateRemaining: response.rateRemaining ?? null,
      rateResetMs: response.rateResetMs ?? null,
    };
    if (classification.action === "accept" || classification.action === "stop") return { ...last, attempts };
    if (classification.action === "refresh") {
      if (refreshed) return { ...last, attempts };
      refreshed = true;
      const ok = await input.refresh();
      if (!ok) return { ...last, attempts };
      continue;
    }
    transportRetries += 1;
    const plan = retryPlan(response.retryAfter, transportRetries);
    if (plan.defer) return { ...last, attempts, deferredMs: plan.waitMs };
    if (transportRetries > MAX_TRANSPORT_RETRIES) return { ...last, attempts };
    await input.sleep(plan.waitMs);
  }
  return { ...last, attempts };
}

function headerNumber(headers: { get(name: string): string | null }, names: string[]): number | null {
  for (const name of names) {
    const value = headers.get(name);
    if (!value) continue;
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function retryAfterSeconds(value: string | null): number | null {
  if (!value) return null;
  const seconds = Number(value.trim());
  if (!Number.isFinite(seconds) || seconds < 0) return null;
  return seconds;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}
