import { mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import path from "node:path";

import { decryptJson, encryptJson } from "./token-crypto.ts";

export type ManifestStatus = "pending" | "partial" | "complete" | "absent" | "inaccessible";

export type ManifestEntry = {
  dataset: string;
  scope: string;
  window: string;
  version: number;
  latest: boolean;
  status: ManifestStatus;
  cursor: string | null;
  unitId: string | null;
};

export type AcquisitionManifest = {
  version: 1;
  entries: ManifestEntry[];
};

const EMPTY_MANIFEST: AcquisitionManifest = { version: 1, entries: [] };

export function entryKey(entry: Pick<ManifestEntry, "dataset" | "scope" | "window">): string {
  return `${entry.dataset}|${entry.scope}|${entry.window}`;
}

export function latestVerified(manifest: AcquisitionManifest, entry: Pick<ManifestEntry, "dataset" | "scope" | "window">): ManifestEntry | null {
  return (
    manifest.entries.find((item) => entryKey(item) === entryKey(entry) && item.latest && item.status === "complete") ?? null
  );
}

export async function readAcquisitionManifest(root: string, key: Buffer): Promise<AcquisitionManifest> {
  const parsed = await readEncrypted(manifestPath(root), key);
  return normaliseManifest(parsed) ?? (await readEncrypted(manifestBackup(root), key).then(normaliseManifest)) ?? EMPTY_MANIFEST;
}

export async function writeEncryptedUnit(input: {
  root: string;
  key: Buffer;
  entry: Pick<ManifestEntry, "dataset" | "scope" | "window">;
  unitId: string;
  body: unknown;
  complete: boolean;
  cursor?: string | null;
}): Promise<"stored" | "kept-complete"> {
  const current = await readAcquisitionManifest(input.root, input.key);
  const verified = latestVerified(current, input.entry);
  const version = nextVersion(current, input.entry);
  if (!input.complete && verified && input.body == null) {
    await writeManifest(
      input.root,
      input.key,
      remember(current, {
        dataset: input.entry.dataset,
        scope: input.entry.scope,
        window: input.entry.window,
        version,
        latest: false,
        status: "partial",
        cursor: input.cursor ?? null,
        unitId: null,
      }),
    );
    return "kept-complete";
  }
  const unitId = `${safeName(input.unitId)}`;
  const target = path.join(input.root, "units", `${safeName(entryKey(input.entry))}-v${version}-${unitId}.bin`);
  await publishEncrypted(target, { body: input.body, complete: input.complete }, input.key);
  await writeManifest(
    input.root,
    input.key,
    remember(current, {
      dataset: input.entry.dataset,
      scope: input.entry.scope,
      window: input.entry.window,
      version,
      latest: input.complete,
      status: input.complete ? "complete" : "partial",
      cursor: input.cursor ?? null,
      unitId,
    }),
  );
  return "stored";
}

export async function markManifest(input: {
  root: string;
  key: Buffer;
  entry: Pick<ManifestEntry, "dataset" | "scope" | "window">;
  status: Exclude<ManifestStatus, "complete">;
  cursor: string | null;
}): Promise<void> {
  const current = await readAcquisitionManifest(input.root, input.key);
  if (latestVerified(current, input.entry)) return;
  await writeManifest(
    input.root,
    input.key,
    remember(current, {
      dataset: input.entry.dataset,
      scope: input.entry.scope,
      window: input.entry.window,
      version: nextVersion(current, input.entry),
      latest: false,
      status: input.status,
      cursor: input.cursor,
      unitId: null,
    }),
  );
}

export function resumableEntries(manifest: AcquisitionManifest): ManifestEntry[] {
  const verified = new Set(
    manifest.entries.filter((entry) => entry.latest && entry.status === "complete").map((entry) => entryKey(entry)),
  );
  return manifest.entries.filter(
    (entry) => (entry.status === "pending" || entry.status === "partial") && !verified.has(entryKey(entry)),
  );
}

async function writeManifest(root: string, key: Buffer, manifest: AcquisitionManifest): Promise<void> {
  await publishEncrypted(manifestPath(root), manifest, key);
}

async function publishEncrypted(target: string, value: unknown, key: Buffer): Promise<void> {
  await mkdir(path.dirname(target), { recursive: true });
  const temporary = `${target}.${process.pid}.tmp`;
  const backup = `${target}.bak`;
  await writeFile(temporary, encryptJson(value, key), { encoding: "utf8", mode: 0o600 });
  await rename(target, backup).catch((error: NodeJS.ErrnoException) => {
    if (error.code !== "ENOENT") throw error;
  });
  try {
    await rename(temporary, target);
  } catch (error) {
    await rename(backup, target).catch(() => undefined);
    throw error;
  }
  await unlink(backup).catch(() => undefined);
  await unlink(temporary).catch(() => undefined);
}

async function readEncrypted(file: string, key: Buffer): Promise<unknown> {
  try {
    return decryptJson(await readFile(file, "utf8"), key);
  } catch {
    return null;
  }
}

function nextVersion(manifest: AcquisitionManifest, entry: Pick<ManifestEntry, "dataset" | "scope" | "window">): number {
  const versions = manifest.entries.filter((item) => entryKey(item) === entryKey(entry)).map((item) => item.version);
  return versions.length === 0 ? 1 : Math.max(...versions) + 1;
}

function remember(manifest: AcquisitionManifest, entry: ManifestEntry): AcquisitionManifest {
  const entries = manifest.entries.map((item) =>
    entry.latest && entryKey(item) === entryKey(entry) ? { ...item, latest: false } : item,
  );
  entries.push(entry);
  return { version: 1, entries };
}

function normaliseManifest(value: unknown): AcquisitionManifest | null {
  const record = value && typeof value === "object" ? (value as { version?: unknown; entries?: unknown }) : null;
  if (!record || record.version !== 1 || !Array.isArray(record.entries)) return null;
  const entries: ManifestEntry[] = [];
  for (const item of record.entries) {
    if (!item || typeof item !== "object") continue;
    const row = item as Partial<ManifestEntry>;
    if (typeof row.dataset !== "string" || typeof row.scope !== "string" || typeof row.window !== "string") continue;
    if (!isStatus(row.status)) continue;
    entries.push({
      dataset: row.dataset,
      scope: row.scope,
      window: row.window,
      version: typeof row.version === "number" ? row.version : 1,
      latest: typeof row.latest === "boolean" ? row.latest : row.status === "complete",
      status: row.status,
      cursor: typeof row.cursor === "string" ? row.cursor : null,
      unitId: typeof row.unitId === "string" ? row.unitId : null,
    });
  }
  return { version: 1, entries };
}

function isStatus(value: unknown): value is ManifestStatus {
  return value === "pending" || value === "partial" || value === "complete" || value === "absent" || value === "inaccessible";
}

function manifestPath(root: string): string {
  return path.join(root, "manifest.bin");
}

function manifestBackup(root: string): string {
  return `${manifestPath(root)}.bak`;
}

function safeName(value: string): string {
  return value.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 120);
}
