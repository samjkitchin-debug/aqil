import { decryptJson, encryptJson } from "./token-crypto.ts";
import type { SaxoEnvironment, SaxoTokens } from "./sim-guard.ts";

export type VaultStatus = "idle" | "refreshing";

/** Ciphertext only. Callers must not put access or refresh tokens in logs. */
export type VaultRow = {
  userId: string;
  environment: SaxoEnvironment;
  ciphertext: string;
  generation: number;
  status: VaultStatus;
};

export type VaultStore = {
  read(userId: string, environment: SaxoEnvironment): Promise<VaultRow | null>;
  /**
   * Move an idle row from expectedGeneration to expectedGeneration + 1 and mark it refreshing.
   * A false result means another worker owns the refresh.
   */
  claim(
    userId: string,
    environment: SaxoEnvironment,
    expectedGeneration: number,
  ): Promise<{ ok: true; generation: number } | { ok: false }>;
  commit(
    userId: string,
    environment: SaxoEnvironment,
    generation: number,
    ciphertext: string,
  ): Promise<boolean>;
  abort(userId: string, environment: SaxoEnvironment, generation: number): Promise<void>;
};

export class VaultOwnerError extends Error {
  constructor() {
    super("token vault owner mismatch");
    this.name = "VaultOwnerError";
  }
}

/** Checked before any service-role read. The database role is not proof of ownership. */
export function assertVaultOwner(sessionUserId: string, ownerUserId: string): void {
  if (!sessionUserId || sessionUserId !== ownerUserId) throw new VaultOwnerError();
}

export function sealTokens(tokens: SaxoTokens, key: Buffer): string {
  return encryptJson(
    {
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      expiresIn: tokens.expiresIn,
      refreshExpiresIn: tokens.refreshExpiresIn,
    },
    key,
  );
}

export function openTokens(ciphertext: string, key: Buffer): SaxoTokens | null {
  const value = decryptJson(ciphertext, key);
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  if (typeof record.accessToken !== "string" || typeof record.refreshToken !== "string") return null;
  if (typeof record.expiresIn !== "number" || typeof record.refreshExpiresIn !== "number") return null;
  return {
    accessToken: record.accessToken,
    refreshToken: record.refreshToken,
    expiresIn: record.expiresIn,
    refreshExpiresIn: record.refreshExpiresIn,
  };
}

type RefreshOutcome =
  | { ok: true; tokens: SaxoTokens }
  | { ok: false; status: number; errorCode: string | null };

/**
 * One Saxo refresh for a claimed generation.
 * A caller that loses the claim does not call Saxo and does not persist.
 */
export async function rotateHostedTokens(input: {
  sessionUserId: string;
  ownerUserId: string;
  environment: SaxoEnvironment;
  store: VaultStore;
  encryptionKey: Buffer;
  refresh: (refreshToken: string) => Promise<RefreshOutcome>;
}): Promise<
  | { ok: true; tokens: SaxoTokens; generation: number }
  | { ok: false; reason: "owner" | "missing" | "conflict" | "unreadable" | "refresh_failed" | "discarded" }
> {
  try {
    assertVaultOwner(input.sessionUserId, input.ownerUserId);
  } catch (error) {
    if (error instanceof VaultOwnerError) return { ok: false, reason: "owner" };
    throw error;
  }
  const current = await input.store.read(input.ownerUserId, input.environment);
  if (!current) return { ok: false, reason: "missing" };
  const claim = await input.store.claim(input.ownerUserId, input.environment, current.generation);
  if (!claim.ok) return { ok: false, reason: "conflict" };
  const release = () => input.store.abort(input.ownerUserId, input.environment, claim.generation);
  try {
    const opened = openTokens(current.ciphertext, input.encryptionKey);
    if (!opened) {
      await release();
      return { ok: false, reason: "unreadable" };
    }
    const refreshed = await input.refresh(opened.refreshToken);
    if (!refreshed.ok) {
      await release();
      return { ok: false, reason: "refresh_failed" };
    }
    const ciphertext = sealTokens(refreshed.tokens, input.encryptionKey);
    const committed = await input.store.commit(
      input.ownerUserId,
      input.environment,
      claim.generation,
      ciphertext,
    );
    if (!committed) {
      await release();
      return { ok: false, reason: "discarded" };
    }
    return { ok: true, tokens: refreshed.tokens, generation: claim.generation };
  } catch (error) {
    try {
      await release();
    } catch {
      // The original failure is the one the caller must see.
    }
    throw error;
  }
}

export type SqlExecutor = (statement: string, params: readonly unknown[]) => Promise<Record<string, unknown>[]>;

function asGeneration(value: unknown): number | null {
  if (typeof value === "number" && Number.isInteger(value) && value > 0) return value;
  if (typeof value === "string" && /^[1-9]\d*$/.test(value)) {
    const parsed = Number(value);
    return Number.isSafeInteger(parsed) ? parsed : null;
  }
  return null;
}

function rowFromSql(record: Record<string, unknown>): VaultRow | null {
  const generation = asGeneration(record.generation);
  if (
    typeof record.user_id !== "string" ||
    (record.environment !== "live" && record.environment !== "simulation") ||
    typeof record.ciphertext !== "string" ||
    generation === null ||
    (record.status !== "idle" && record.status !== "refreshing")
  ) {
    return null;
  }
  return {
    userId: record.user_id,
    environment: record.environment,
    ciphertext: record.ciphertext,
    generation,
    status: record.status,
  };
}

/**
 * Compare-and-swap statements for saxo_token_vault.
 * The executor must be a service-role client created only after assertVaultOwner.
 */
export function createSqlVaultStore(execute: SqlExecutor): VaultStore {
  return {
    async read(userId, environment) {
      const rows = await execute(
        "select user_id, environment, ciphertext, generation, status from public.saxo_token_vault where user_id = $1 and environment = $2",
        [userId, environment],
      );
      return rows[0] ? rowFromSql(rows[0]) : null;
    },
    async claim(userId, environment, expectedGeneration) {
      const rows = await execute(
        "update public.saxo_token_vault set generation = generation + 1, status = 'refreshing' where user_id = $1 and environment = $2 and generation = $3 and status = 'idle' returning generation",
        [userId, environment, expectedGeneration],
      );
      const generation = asGeneration(rows[0]?.generation);
      return generation === null ? { ok: false } : { ok: true, generation };
    },
    async commit(userId, environment, generation, ciphertext) {
      if (!ciphertext.startsWith("v1.")) return false;
      const rows = await execute(
        "update public.saxo_token_vault set ciphertext = $4, status = 'idle' where user_id = $1 and environment = $2 and generation = $3 and status = 'refreshing' returning generation",
        [userId, environment, generation, ciphertext],
      );
      return rows.length === 1;
    },
    async abort(userId, environment, generation) {
      await execute(
        "update public.saxo_token_vault set status = 'idle' where user_id = $1 and environment = $2 and generation = $3 and status = 'refreshing'",
        [userId, environment, generation],
      );
    },
  };
}

/** In-memory stand-in for the hosted compare-and-swap. Claims are serialised per row. */
export function createMemoryVaultStore(initial: VaultRow): VaultStore {
  let row: VaultRow | null = { ...initial };
  let chain: Promise<void> = Promise.resolve();
  function exclusive<T>(fn: () => T): Promise<T> {
    const run = chain.then(fn);
    chain = run.then(
      () => undefined,
      () => undefined,
    );
    return run;
  }
  return {
    read(userId, environment) {
      return exclusive(() => {
        if (!row || row.userId !== userId || row.environment !== environment) return null;
        return { ...row };
      });
    },
    claim(userId, environment, expectedGeneration) {
      return exclusive(() => {
        if (!row || row.userId !== userId || row.environment !== environment) return { ok: false };
        if (row.status !== "idle" || row.generation !== expectedGeneration) return { ok: false };
        row = { ...row, status: "refreshing", generation: expectedGeneration + 1 };
        return { ok: true, generation: row.generation };
      });
    },
    commit(userId, environment, generation, ciphertext) {
      return exclusive(() => {
        if (!row || row.userId !== userId || row.environment !== environment) return false;
        if (row.status !== "refreshing" || row.generation !== generation) return false;
        if (!ciphertext.startsWith("v1.")) return false;
        row = { ...row, status: "idle", ciphertext };
        return true;
      });
    },
    abort(userId, environment, generation) {
      return exclusive(() => {
        if (!row || row.userId !== userId || row.environment !== environment) return;
        if (row.status !== "refreshing" || row.generation !== generation) return;
        row = { ...row, status: "idle" };
      });
    },
  };
}
