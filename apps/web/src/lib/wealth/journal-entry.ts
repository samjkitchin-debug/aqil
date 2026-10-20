import { currencyExponent, parseMajorToMinor } from "./money.ts";
import { replayJournal, type JournalEvent } from "./journal.ts";

export const MANUAL_EVENT_TYPES = ["deposit", "withdrawal", "buy", "sell", "fee", "distribution", "split"] as const;

export type ManualEventType = (typeof MANUAL_EVENT_TYPES)[number];

const QUANTITY_SCALE = 100_000_000n;
const LABEL = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/;
const DRAFT_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export type ManualEntryInput = {
  eventType: string;
  occurredOn: string;
  accountId: string;
  currency: string;
  cashAmount: string;
  instrumentId: string;
  quantity: string;
  unitPrice: string;
  splitNumerator: string;
  splitDenominator: string;
  draftId: string;
};

export function isIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return false;
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

export function assertJournalCurrency(currency: string): string {
  const normalised = currency.trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(normalised)) throw new Error("invalid currency");
  try {
    currencyExponent(normalised);
  } catch {
    throw new Error("invalid currency");
  }
  return normalised;
}

export function journalCanonical(event: JournalEvent): string {
  return JSON.stringify({
    eventId: event.eventId,
    accountId: event.accountId,
    eventType: event.eventType,
    occurredOn: event.occurredOn,
    instrumentId: event.instrumentId,
    quantity: event.quantity,
    unitPriceMinor: event.unitPriceMinor?.toString() ?? null,
    cashAmountMinor: event.cashAmountMinor?.toString() ?? null,
    currency: event.currency,
    correctionOf: event.correctionOf,
    transferGroupId: event.transferGroupId,
    splitNumerator: event.splitNumerator,
    splitDenominator: event.splitDenominator,
  });
}

export function parseManualEntry(input: ManualEntryInput): JournalEvent {
  const eventType = input.eventType.trim();
  if (!MANUAL_EVENT_TYPES.includes(eventType as ManualEventType)) throw new Error("missing field");
  const draftId = input.draftId.trim().toLowerCase();
  if (!DRAFT_ID.test(draftId)) throw new Error("missing field");
  const key = `manual:${draftId}`;
  return buildJournalEvent({
    eventId: key,
    idempotencyKey: key,
    eventType: eventType as ManualEventType,
    occurredOn: input.occurredOn,
    accountId: input.accountId,
    currency: input.currency,
    instrumentId: input.instrumentId,
    quantity: input.quantity,
    cashAmount: input.cashAmount,
    unitPrice: input.unitPrice,
    splitNumerator: input.splitNumerator,
    splitDenominator: input.splitDenominator,
    rejectPriceMismatch: false,
  });
}

export function buildJournalEvent(input: {
  eventId: string;
  idempotencyKey: string;
  eventType: ManualEventType;
  occurredOn: string;
  accountId: string;
  currency: string;
  instrumentId: string;
  quantity: string;
  cashAmount: string;
  unitPrice: string;
  splitNumerator: string;
  splitDenominator: string;
  rejectPriceMismatch: boolean;
}): JournalEvent {
  const occurredOn = input.occurredOn.trim();
  if (!isIsoDate(occurredOn)) throw new Error("missing field");
  const accountId = requireLabel(input.accountId);
  const currency = input.currency.trim() === "" ? "" : assertJournalCurrency(input.currency);
  if (currency === "") throw new Error("missing field");
  const eventId = requireLabel(input.eventId);
  const idempotencyKey = requireLabel(input.idempotencyKey);
  const instrumentId = blankToNull(input.instrumentId);
  const quantityText = input.quantity.trim();
  const cashText = input.cashAmount.trim();
  const priceText = input.unitPrice.trim();
  const numeratorText = input.splitNumerator.trim();
  const denominatorText = input.splitDenominator.trim();

  if (input.eventType === "split") {
    if (cashText || quantityText || priceText) throw new Error("missing field");
    if (!instrumentId) throw new Error("missing field");
    return blankEvent({
      eventId,
      idempotencyKey,
      accountId,
      eventType: "split",
      occurredOn,
      instrumentId,
      currency,
      splitNumerator: strictPositiveInt(numeratorText),
      splitDenominator: strictPositiveInt(denominatorText),
    });
  }

  if (numeratorText || denominatorText) throw new Error("missing field");

  if (
    input.eventType === "deposit" ||
    input.eventType === "withdrawal" ||
    input.eventType === "fee" ||
    input.eventType === "distribution"
  ) {
    if (quantityText || priceText) throw new Error("missing field");
    if (input.eventType !== "distribution" && instrumentId) throw new Error("missing field");
    const cashAmountMinor = signedCash(input.eventType, cashText, currency);
    return blankEvent({
      eventId,
      idempotencyKey,
      accountId,
      eventType: input.eventType,
      occurredOn,
      instrumentId: input.eventType === "distribution" ? instrumentId : null,
      currency,
      cashAmountMinor,
    });
  }

  if (!instrumentId) throw new Error("missing field");
  const quantity = unsignedQuantity(quantityText);
  const cashAmountMinor = cashText ? signedCash(input.eventType, cashText, currency) : null;
  let unitPriceMinor = priceText ? parseMajorToMinor(priceText, currency) : null;
  if (cashAmountMinor === null && unitPriceMinor === null) throw new Error("missing field");
  if (cashAmountMinor !== null && unitPriceMinor !== null) {
    const magnitude = cashAmountMinor < 0n ? -cashAmountMinor : cashAmountMinor;
    if (notionalMinor(quantity, unitPriceMinor) !== magnitude) {
      if (input.rejectPriceMismatch) throw new Error("ambiguous amount");
      unitPriceMinor = null;
    }
  }
  return blankEvent({
    eventId,
    idempotencyKey,
    accountId,
    eventType: input.eventType,
    occurredOn,
    instrumentId,
    quantity: input.eventType === "sell" ? `-${quantity}` : quantity,
    unitPriceMinor,
    cashAmountMinor,
    currency,
  });
}

export function acceptJournalEvent(
  events: readonly JournalEvent[],
  event: JournalEvent,
  reportingCurrency: string,
): { events: JournalEvent[]; added: boolean } {
  const existing = events.find((item) => item.idempotencyKey === event.idempotencyKey);
  if (existing) {
    if (journalCanonical(existing) !== journalCanonical(event)) {
      throw new Error("idempotency key already identifies a different event");
    }
    return { events: [...events], added: false };
  }
  const next = [...events, event];
  replayJournal(next, reportingCurrency);
  return { events: next, added: true };
}

function blankEvent(partial: {
  eventId: string;
  idempotencyKey: string;
  accountId: string;
  eventType: ManualEventType;
  occurredOn: string;
  instrumentId?: string | null;
  quantity?: string | null;
  unitPriceMinor?: bigint | null;
  cashAmountMinor?: bigint | null;
  currency: string;
  splitNumerator?: number | null;
  splitDenominator?: number | null;
}): JournalEvent {
  return {
    eventId: partial.eventId,
    accountId: partial.accountId,
    eventType: partial.eventType,
    occurredOn: partial.occurredOn,
    instrumentId: partial.instrumentId ?? null,
    quantity: partial.quantity ?? null,
    unitPriceMinor: partial.unitPriceMinor ?? null,
    cashAmountMinor: partial.cashAmountMinor ?? null,
    currency: partial.currency,
    idempotencyKey: partial.idempotencyKey,
    correctionOf: null,
    transferGroupId: null,
    splitNumerator: partial.splitNumerator ?? null,
    splitDenominator: partial.splitDenominator ?? null,
  };
}

function signedCash(eventType: ManualEventType, cashText: string, currency: string): bigint {
  if (cashText === "") throw new Error("missing field");
  if (cashText.startsWith("-") || cashText.startsWith("+")) throw new Error("invalid amount");
  const magnitude = parseMajorToMinor(cashText, currency);
  if (magnitude === 0n) throw new Error("invalid amount");
  if (eventType === "fee" || eventType === "buy" || eventType === "withdrawal") return -magnitude;
  return magnitude;
}

function unsignedQuantity(value: string): string {
  if (!/^(?:[1-9]\d*|\d)(?:\.\d{1,8})?$/.test(value)) throw new Error("invalid quantity");
  const [whole, fraction = ""] = value.split(".");
  if (BigInt(whole) === 0n && /^0*$/.test(fraction)) throw new Error("invalid quantity");
  return value;
}

function strictPositiveInt(value: string): number {
  if (!/^[1-9]\d{0,8}$/.test(value)) throw new Error("missing field");
  return Number(value);
}

function requireLabel(value: string): string {
  const trimmed = value.trim();
  if (!LABEL.test(trimmed)) throw new Error("missing field");
  return trimmed;
}

function blankToNull(value: string): string | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  return requireLabel(trimmed);
}

function notionalMinor(quantity: string, unitPriceMinor: bigint): bigint {
  const [whole, fraction = ""] = quantity.split(".");
  const scaled = BigInt(whole) * QUANTITY_SCALE + BigInt(fraction.padEnd(8, "0"));
  return (scaled * unitPriceMinor + QUANTITY_SCALE / 2n) / QUANTITY_SCALE;
}
