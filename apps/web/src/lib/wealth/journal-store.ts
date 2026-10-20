import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { currencyExponent } from "./money.ts";
import { replayJournal, JOURNAL_EVENT_TYPES, type JournalEvent, type JournalEventType } from "./journal.ts";
import { assertJournalCurrency, isIsoDate } from "./journal-entry.ts";
import { CSV_MAX_CHARS } from "./journal-csv.ts";
import {
  type SuppliedPrice,
  type SuppliedRate,
} from "./journal-valuation.ts";

const USER_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const MINOR = /^-?\d+$/;

export type JournalFile = {
  schemaVersion: 1;
  reportingCurrency: "SGD";
  events: JournalEvent[];
  prices: SuppliedPrice[];
  rates: SuppliedRate[];
  previewCsv: string | null;
};

export function emptyJournalFile(): JournalFile {
  return {
    schemaVersion: 1,
    reportingCurrency: "SGD",
    events: [],
    prices: [],
    rates: [],
    previewCsv: null,
  };
}

export function assertJournalUserId(userId: string): string {
  if (!USER_ID.test(userId)) throw new Error("invalid user");
  return userId.toLowerCase();
}

export function journalPath(webRoot: string, userId: string): string {
  const id = assertJournalUserId(userId);
  return path.join(webRoot, ".local", "journal", `${id}.json`);
}

export function webRootFrom(cwd: string): string {
  const normalised = cwd.replace(/\\/g, "/");
  return normalised.endsWith("/apps/web") ? cwd : path.join(cwd, "apps", "web");
}

export async function readJournalFile(userId: string, root = webRootFrom(process.cwd())): Promise<JournalFile> {
  const target = journalPath(root, userId);
  try {
    const raw = await readFile(target, "utf8");
    return parseJournalFile(JSON.parse(raw) as unknown);
  } catch (error) {
    if (isMissingFile(error)) return emptyJournalFile();
    throw new Error("unreadable");
  }
}

export async function writeJournalFile(
  userId: string,
  file: JournalFile,
  root = webRootFrom(process.cwd()),
): Promise<void> {
  const target = journalPath(root, userId);
  await mkdir(path.dirname(target), { recursive: true });
  await writeFile(target, `${JSON.stringify(serialiseJournalFile(file), null, 2)}\n`, {
    encoding: "utf8",
    mode: 0o600,
  });
}

export function parseJournalFile(raw: unknown): JournalFile {
  if (!isRecord(raw)) throw new Error("unreadable");
  if (raw.schemaVersion !== 1 || raw.reportingCurrency !== "SGD") throw new Error("unreadable");
  if (!Array.isArray(raw.events) || !Array.isArray(raw.prices) || !Array.isArray(raw.rates)) {
    throw new Error("unreadable");
  }
  const events = raw.events.map(parseEvent);
  const prices = raw.prices.map(parsePrice);
  const rates = raw.rates.map(parseRate);
  assertUnique(prices.map(priceKey));
  assertUnique(rates.map(rateKey));
  const previewCsv = raw.previewCsv === null ? null : raw.previewCsv;
  if (previewCsv !== null && (typeof previewCsv !== "string" || previewCsv.length > CSV_MAX_CHARS)) {
    throw new Error("unreadable");
  }
  if (events.length > 0) replayJournal(events, "SGD");
  return { schemaVersion: 1, reportingCurrency: "SGD", events, prices, rates, previewCsv };
}

function serialiseJournalFile(file: JournalFile): unknown {
  return {
    schemaVersion: 1,
    reportingCurrency: "SGD",
    events: file.events.map(serialiseEvent),
    prices: file.prices.map((price) => ({ ...price, unitPriceMinor: price.unitPriceMinor.toString() })),
    rates: file.rates,
    previewCsv: file.previewCsv,
  };
}

function serialiseEvent(event: JournalEvent): unknown {
  return {
    ...event,
    unitPriceMinor: event.unitPriceMinor?.toString() ?? null,
    cashAmountMinor: event.cashAmountMinor?.toString() ?? null,
  };
}

function parseEvent(raw: unknown): JournalEvent {
  if (!isRecord(raw)) throw new Error("unreadable");
  const eventType = raw.eventType;
  if (typeof eventType !== "string" || !JOURNAL_EVENT_TYPES.includes(eventType as JournalEventType)) {
    throw new Error("unreadable");
  }
  return {
    eventId: requireString(raw.eventId),
    accountId: requireString(raw.accountId),
    eventType: eventType as JournalEventType,
    occurredOn: requireDate(raw.occurredOn),
    instrumentId: requireNullableString(raw.instrumentId),
    quantity: requireNullableString(raw.quantity),
    unitPriceMinor: requireMinor(raw.unitPriceMinor),
    cashAmountMinor: requireMinor(raw.cashAmountMinor),
    currency: requireString(raw.currency),
    idempotencyKey: requireString(raw.idempotencyKey),
    correctionOf: requireNullableString(raw.correctionOf),
    transferGroupId: requireNullableString(raw.transferGroupId),
    splitNumerator: requireNullableInt(raw.splitNumerator),
    splitDenominator: requireNullableInt(raw.splitDenominator),
  };
}

function parsePrice(raw: unknown): SuppliedPrice {
  if (!isRecord(raw) || raw.source !== "supplied") throw new Error("unreadable");
  const unitPriceMinor = requireMinor(raw.unitPriceMinor);
  if (unitPriceMinor === null || unitPriceMinor <= 0n) throw new Error("unreadable");
  return {
    instrumentId: requireString(raw.instrumentId),
    currency: checkedCurrency(raw.currency),
    unitPriceMinor,
    asOf: requireDate(raw.asOf),
    source: "supplied",
  };
}

function parseRate(raw: unknown): SuppliedRate {
  if (!isRecord(raw) || raw.source !== "supplied") throw new Error("unreadable");
  const rate = requireString(raw.rate);
  if (!/^\d+(\.\d{1,10})?$/.test(rate) || /^0+(?:\.0+)?$/.test(rate)) throw new Error("unreadable");
  const baseCurrency = checkedCurrency(raw.baseCurrency);
  const quoteCurrency = checkedCurrency(raw.quoteCurrency);
  if (baseCurrency === quoteCurrency || currencyExponent(baseCurrency) !== currencyExponent(quoteCurrency)) {
    throw new Error("unreadable");
  }
  return {
    baseCurrency,
    quoteCurrency,
    rate,
    asOf: requireDate(raw.asOf),
    source: "supplied",
  };
}

function checkedCurrency(value: unknown): string {
  try {
    return assertJournalCurrency(requireString(value));
  } catch {
    throw new Error("unreadable");
  }
}

function priceKey(price: SuppliedPrice): string {
  return `${price.instrumentId}\u0000${price.currency}\u0000${price.asOf}`;
}

function rateKey(rate: SuppliedRate): string {
  return `${rate.baseCurrency}\u0000${rate.quoteCurrency}\u0000${rate.asOf}`;
}

function assertUnique(keys: string[]): void {
  if (new Set(keys).size !== keys.length) throw new Error("unreadable");
}

function requireString(value: unknown): string {
  if (typeof value !== "string" || value.trim() === "") throw new Error("unreadable");
  return value;
}

function requireNullableString(value: unknown): string | null {
  if (value === null) return null;
  if (typeof value !== "string") throw new Error("unreadable");
  return value;
}

function requireDate(value: unknown): string {
  if (typeof value !== "string" || !isIsoDate(value)) throw new Error("unreadable");
  return value;
}

function requireMinor(value: unknown): bigint | null {
  if (value === null) return null;
  if (typeof value !== "string" || !MINOR.test(value)) throw new Error("unreadable");
  return BigInt(value);
}

function requireNullableInt(value: unknown): number | null {
  if (value === null) return null;
  if (typeof value !== "number" || !Number.isInteger(value)) throw new Error("unreadable");
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isMissingFile(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && error.code === "ENOENT";
}
