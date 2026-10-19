import { convertMinor } from "./money.ts";

export const JOURNAL_EVENT_TYPES = [
  "deposit",
  "withdrawal",
  "transfer",
  "buy",
  "sell",
  "fee",
  "distribution",
  "reinvestment",
  "tax",
  "split",
  "correction",
] as const;

export type JournalEventType = (typeof JOURNAL_EVENT_TYPES)[number];

/** One append-only journal leg. Money is minor units. Quantity is a decimal string. */
export type JournalEvent = {
  eventId: string;
  accountId: string;
  eventType: JournalEventType;
  occurredOn: string;
  instrumentId: string | null;
  /** Signed units into the account. Null for cash-only events and splits. */
  quantity: string | null;
  /** Booked unit price in minor units. Null when no price was observed. */
  unitPriceMinor: bigint | null;
  /**
   * Signed minor units into the account. Already includes fees and tax.
   * Null when the cash leg was not observed.
   */
  cashAmountMinor: bigint | null;
  currency: string;
  idempotencyKey: string;
  correctionOf: string | null;
  transferGroupId: string | null;
  splitNumerator: number | null;
  splitDenominator: number | null;
};

export type FxRate = {
  baseCurrency: string;
  quoteCurrency: string;
  rate: string;
};

export type PriceQuote = {
  instrumentId: string;
  currency: string;
  unitPriceMinor: bigint;
};

export type MoneyStatus =
  | { status: "available"; currency: string; amountMinor: bigint }
  | { status: "unavailable" };

export type JournalReplay = {
  positions: Array<{
    accountId: string;
    instrumentId: string;
    quantity: string;
    costMinor: bigint | null;
    currency: string;
  }>;
  cash: Array<{
    accountId: string;
    currency: string;
    amountMinor: bigint | null;
  }>;
  realisedProfit: MoneyStatus;
  netContributionsMinor: bigint;
  marketValue: MoneyStatus;
  reportingCash: MoneyStatus;
  unbalancedTransferGroupIds: string[];
};

const QUANTITY_SCALE = 100_000_000n;

type Position = {
  accountId: string;
  instrumentId: string;
  currency: string;
  quantity: bigint;
  costMinor: bigint | null;
  unsettledIn: bigint;
};

type CashBucket = {
  accountId: string;
  currency: string;
  amountMinor: bigint | null;
};

type Pool = {
  quantity: bigint;
  costMinor: bigint | null;
};

type Waiter = {
  groupId: string;
  instrumentId: string;
  currency: string;
  accountId: string;
  quantity: bigint;
};

type State = {
  positions: Map<string, Position>;
  cash: Map<string, CashBucket>;
  pools: Map<string, Pool>;
  waiters: Waiter[];
  groupCash: Map<string, Map<string, bigint>>;
  realisedMinor: bigint | null;
  realisedCurrency: string | null;
  netContributionsMinor: bigint;
};

export function effectiveJournalEvents(events: readonly JournalEvent[]): JournalEvent[] {
  const unique = dedupe(events);
  const byId = new Map(unique.map((event) => [event.eventId, event]));
  const superseded = new Set<string>();
  for (const event of unique) {
    if (event.correctionOf === null) continue;
    if (event.correctionOf === event.eventId) {
      throw new Error("an event cannot correct itself");
    }
    if (!byId.has(event.correctionOf)) {
      throw new Error("correction target is not in the journal");
    }
    if (superseded.has(event.correctionOf)) {
      throw new Error("an event already has a correction");
    }
    const seen = new Set<string>([event.eventId]);
    let cursor: string | null = event.correctionOf;
    while (cursor) {
      if (seen.has(cursor)) throw new Error("correction cycle");
      seen.add(cursor);
      cursor = byId.get(cursor)?.correctionOf ?? null;
    }
    superseded.add(event.correctionOf);
  }
  return unique
    .filter((event) => !superseded.has(event.eventId))
    .sort((left, right) => left.occurredOn.localeCompare(right.occurredOn) || left.eventId.localeCompare(right.eventId));
}

export function replayJournal(
  events: readonly JournalEvent[],
  reportingCurrency: string,
  rates: readonly FxRate[] = [],
  prices: readonly PriceQuote[] = [],
): JournalReplay {
  if (!/^[A-Z]{3}$/.test(reportingCurrency)) throw new Error("invalid currency");
  const state = emptyState();
  for (const event of effectiveJournalEvents(events)) {
    applyEvent(state, event);
  }
  const unbalanced = unbalancedGroups(state);
  const open = [...state.positions.values()].filter((position) => position.quantity !== 0n);
  return {
    positions: open
      .map((position) => ({
        accountId: position.accountId,
        instrumentId: position.instrumentId,
        quantity: formatQuantity(position.quantity),
        costMinor: position.unsettledIn === 0n ? position.costMinor : null,
        currency: position.currency,
      }))
      .sort((left, right) => left.accountId.localeCompare(right.accountId) || left.instrumentId.localeCompare(right.instrumentId)),
    cash: [...state.cash.values()]
      .filter((bucket) => bucket.amountMinor !== 0n)
      .sort((left, right) => left.accountId.localeCompare(right.accountId) || left.currency.localeCompare(right.currency)),
    realisedProfit: realisedStatus(state, reportingCurrency),
    netContributionsMinor: state.netContributionsMinor,
    marketValue: marketValue(open, reportingCurrency, rates, prices),
    reportingCash: reportingCash([...state.cash.values()], reportingCurrency, rates),
    unbalancedTransferGroupIds: unbalanced,
  };
}

function emptyState(): State {
  return {
    positions: new Map(),
    cash: new Map(),
    pools: new Map(),
    waiters: [],
    groupCash: new Map(),
    realisedMinor: 0n,
    realisedCurrency: null,
    netContributionsMinor: 0n,
  };
}

function dedupe(events: readonly JournalEvent[]): JournalEvent[] {
  const byKey = new Map<string, JournalEvent>();
  const byId = new Map<string, JournalEvent>();
  for (const event of events) {
    validateEvent(event);
    const existing = byKey.get(event.idempotencyKey);
    if (existing) {
      if (existing.eventId !== event.eventId || canonical(existing) !== canonical(event)) {
        throw new Error("idempotency key already identifies a different event");
      }
      continue;
    }
    if (byId.has(event.eventId)) {
      throw new Error("event identity is already in the journal");
    }
    byKey.set(event.idempotencyKey, event);
    byId.set(event.eventId, event);
  }
  return [...byKey.values()];
}

function validateEvent(event: JournalEvent): void {
  if (!JOURNAL_EVENT_TYPES.includes(event.eventType)) throw new Error("unknown event type");
  if (event.eventId.trim().length === 0) throw new Error("event identity is required");
  if (event.idempotencyKey.trim().length === 0) throw new Error("idempotency key is required");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(event.occurredOn)) throw new Error("invalid date");
  if (!/^[A-Z]{3}$/.test(event.currency)) throw new Error("invalid currency");
  if (event.correctionOf === event.eventId) throw new Error("an event cannot correct itself");
  if (event.eventType === "split") {
    assertSplitRatio(event);
    if (event.instrumentId === null || event.quantity !== null || event.cashAmountMinor !== null) {
      throw new Error("invalid split");
    }
    return;
  }
  if (event.splitNumerator !== null || event.splitDenominator !== null) {
    throw new Error("invalid split");
  }
  if (event.eventType === "transfer") {
    if (event.transferGroupId === null) throw new Error("invalid transfer");
    const security = event.quantity !== null;
    const cash = event.cashAmountMinor !== null;
    if (security === cash) throw new Error("invalid transfer");
    if (security && event.instrumentId === null) throw new Error("invalid transfer");
    if (cash && (event.instrumentId !== null || event.cashAmountMinor === 0n)) {
      throw new Error("invalid transfer");
    }
    return;
  }
  if (event.transferGroupId !== null) throw new Error("invalid transfer");
  if (event.eventType === "correction") {
    if (event.correctionOf === null || event.quantity !== null || event.cashAmountMinor !== null) {
      throw new Error("invalid correction");
    }
    return;
  }
  if (event.eventType === "buy" || event.eventType === "reinvestment") {
    if (event.instrumentId === null || event.quantity === null) throw new Error("invalid quantity");
    if (parseQuantity(event.quantity) <= 0n) throw new Error("invalid quantity");
    if (event.cashAmountMinor !== null && event.cashAmountMinor > 0n) throw new Error("invalid amount");
    return;
  }
  if (event.eventType === "sell") {
    if (event.instrumentId === null || event.quantity === null) throw new Error("invalid quantity");
    if (parseQuantity(event.quantity) >= 0n) throw new Error("invalid quantity");
    if (event.cashAmountMinor !== null && event.cashAmountMinor < 0n) throw new Error("invalid amount");
    return;
  }
  if (event.quantity !== null || event.instrumentId !== null) {
    if (event.eventType !== "distribution") throw new Error("invalid quantity");
  }
  if (event.eventType === "distribution" && event.quantity !== null) throw new Error("invalid quantity");
  requireSignedCash(event);
}

function requireSignedCash(event: JournalEvent): void {
  const amount = event.cashAmountMinor;
  if (amount === null || amount === 0n) throw new Error("invalid amount");
  if (event.eventType === "deposit" || event.eventType === "distribution") {
    if (amount < 0n) throw new Error("invalid amount");
    if (event.eventType === "deposit" && event.instrumentId !== null) throw new Error("invalid amount");
    return;
  }
  if (event.eventType === "withdrawal" || event.eventType === "fee" || event.eventType === "tax") {
    if (amount > 0n) throw new Error("invalid amount");
    if (event.instrumentId !== null || event.quantity !== null) throw new Error("invalid amount");
  }
}

function assertSplitRatio(event: JournalEvent): void {
  const numerator = event.splitNumerator;
  const denominator = event.splitDenominator;
  if (
    numerator === null ||
    denominator === null ||
    !Number.isInteger(numerator) ||
    !Number.isInteger(denominator) ||
    numerator <= 0 ||
    denominator <= 0
  ) {
    throw new Error("split requires a ratio");
  }
}

function applyEvent(state: State, event: JournalEvent): void {
  switch (event.eventType) {
    case "buy":
    case "reinvestment":
      applyAcquisition(state, event);
      return;
    case "sell":
      applySell(state, event);
      return;
    case "fee":
    case "tax":
    case "distribution":
      applyCash(state, event.accountId, event.currency, event.cashAmountMinor);
      return;
    case "deposit":
      applyCash(state, event.accountId, event.currency, event.cashAmountMinor);
      state.netContributionsMinor += event.cashAmountMinor ?? 0n;
      return;
    case "withdrawal":
      applyCash(state, event.accountId, event.currency, event.cashAmountMinor);
      state.netContributionsMinor += event.cashAmountMinor ?? 0n;
      return;
    case "transfer":
      applyTransfer(state, event);
      return;
    case "split":
      applySplit(state, event);
      return;
    case "correction":
      return;
    default:
      throw new Error("unknown event type");
  }
}

function applyAcquisition(state: State, event: JournalEvent): void {
  const quantity = parseQuantity(event.quantity ?? "");
  const cash = bookedCash(event, quantity, "out");
  const position = positionFor(state, event.accountId, event.instrumentId ?? "", event.currency);
  position.quantity += quantity;
  if (cash === null || position.costMinor === null) position.costMinor = null;
  else position.costMinor += -cash;
  applyCash(state, event.accountId, event.currency, cash);
}

function applySell(state: State, event: JournalEvent): void {
  const quantity = parseQuantity(event.quantity ?? "");
  const sold = -quantity;
  const position = requirePosition(state, event.accountId, event.instrumentId ?? "");
  if (position.currency !== event.currency) throw new Error("position currency does not match");
  if (position.unsettledIn !== 0n) throw new Error("position cost is not settled");
  if (position.quantity < sold) throw new Error("position would become short");
  const cash = bookedCash(event, sold, "in");
  let allocated: bigint | null = null;
  if (position.costMinor !== null) {
    allocated = (position.costMinor * sold) / position.quantity;
    position.costMinor -= allocated;
  }
  position.quantity -= sold;
  if (position.quantity === 0n) position.costMinor = 0n;
  applyCash(state, event.accountId, event.currency, cash);
  if (allocated === null || cash === null) {
    state.realisedMinor = null;
    return;
  }
  if (state.realisedMinor === null) return;
  if (state.realisedCurrency !== null && state.realisedCurrency !== event.currency) {
    state.realisedMinor = null;
    return;
  }
  state.realisedCurrency = event.currency;
  state.realisedMinor += cash - allocated;
}

function applyTransfer(state: State, event: JournalEvent): void {
  const groupId = event.transferGroupId ?? "";
  if (event.cashAmountMinor !== null) {
    applyCash(state, event.accountId, event.currency, event.cashAmountMinor);
    const byCurrency = state.groupCash.get(groupId) ?? new Map<string, bigint>();
    byCurrency.set(event.currency, (byCurrency.get(event.currency) ?? 0n) + event.cashAmountMinor);
    state.groupCash.set(groupId, byCurrency);
    return;
  }
  const quantity = parseQuantity(event.quantity ?? "");
  const instrumentId = event.instrumentId ?? "";
  if (quantity < 0n) {
    const moved = -quantity;
    const source = requirePosition(state, event.accountId, instrumentId);
    if (source.currency !== event.currency) throw new Error("position currency does not match");
    if (source.unsettledIn !== 0n) throw new Error("position cost is not settled");
    if (source.quantity < moved) throw new Error("position would become short");
    let allocated: bigint | null = null;
    if (source.costMinor !== null) {
      allocated = (source.costMinor * moved) / source.quantity;
      source.costMinor -= allocated;
    }
    source.quantity -= moved;
    if (source.quantity === 0n) source.costMinor = 0n;
    const pool = poolFor(state, groupId, instrumentId, event.currency);
    pool.quantity += moved;
    pool.costMinor = pool.costMinor === null || allocated === null ? null : pool.costMinor + allocated;
    satisfyWaiters(state, pool, groupId, instrumentId, event.currency);
    return;
  }
  const destination = positionFor(state, event.accountId, instrumentId, event.currency);
  const pool = poolFor(state, groupId, instrumentId, event.currency);
  if (pool.quantity >= quantity) {
    receive(destination, quantity, takePool(pool, quantity));
    return;
  }
  destination.quantity += quantity;
  destination.unsettledIn += quantity;
  state.waiters.push({
    groupId,
    instrumentId,
    currency: event.currency,
    accountId: event.accountId,
    quantity,
  });
}

function applySplit(state: State, event: JournalEvent): void {
  const numerator = BigInt(event.splitNumerator ?? 0);
  const denominator = BigInt(event.splitDenominator ?? 0);
  const position = requirePosition(state, event.accountId, event.instrumentId ?? "");
  if (position.unsettledIn !== 0n) throw new Error("position cost is not settled");
  if (position.quantity === 0n) throw new Error("split requires a position");
  if ((position.quantity * numerator) % denominator !== 0n) {
    throw new Error("split does not divide the position");
  }
  position.quantity = (position.quantity * numerator) / denominator;
}

function applyCash(state: State, accountId: string, currency: string, amount: bigint | null): void {
  const key = `${accountId}\u0000${currency}`;
  const current = state.cash.get(key);
  if (amount === null || current?.amountMinor === null) {
    state.cash.set(key, { accountId, currency, amountMinor: null });
    return;
  }
  state.cash.set(key, {
    accountId,
    currency,
    amountMinor: (current?.amountMinor ?? 0n) + amount,
  });
}

function bookedCash(event: JournalEvent, quantity: bigint, direction: "in" | "out"): bigint | null {
  if (event.cashAmountMinor !== null) return event.cashAmountMinor;
  if (event.unitPriceMinor === null) return null;
  const gross = notionalMinor(quantity, event.unitPriceMinor);
  return direction === "out" ? -gross : gross;
}

function positionFor(state: State, accountId: string, instrumentId: string, currency: string): Position {
  const key = positionKey(accountId, instrumentId);
  const existing = state.positions.get(key);
  if (existing) {
    if (existing.currency !== currency) throw new Error("position currency does not match");
    return existing;
  }
  const created: Position = {
    accountId,
    instrumentId,
    currency,
    quantity: 0n,
    costMinor: 0n,
    unsettledIn: 0n,
  };
  state.positions.set(key, created);
  return created;
}

function requirePosition(state: State, accountId: string, instrumentId: string): Position {
  const position = state.positions.get(positionKey(accountId, instrumentId));
  if (!position || position.quantity === 0n) throw new Error("position would become short");
  return position;
}

function poolFor(state: State, groupId: string, instrumentId: string, currency: string): Pool {
  const key = `${groupId}\u0000${instrumentId}\u0000${currency}`;
  const existing = state.pools.get(key);
  if (existing) return existing;
  const created: Pool = { quantity: 0n, costMinor: 0n };
  state.pools.set(key, created);
  return created;
}

function takePool(pool: Pool, quantity: bigint): bigint | null {
  if (pool.quantity < quantity) throw new Error("invalid transfer");
  if (pool.costMinor === null) {
    pool.quantity -= quantity;
    return null;
  }
  const moved = (pool.costMinor * quantity) / pool.quantity;
  pool.costMinor -= moved;
  pool.quantity -= quantity;
  return moved;
}

function receive(position: Position, quantity: bigint, cost: bigint | null): void {
  position.quantity += quantity;
  if (cost === null || position.costMinor === null) position.costMinor = null;
  else position.costMinor += cost;
}

function satisfyWaiters(state: State, pool: Pool, groupId: string, instrumentId: string, currency: string): void {
  const remaining: Waiter[] = [];
  for (const waiter of state.waiters) {
    if (
      waiter.groupId !== groupId ||
      waiter.instrumentId !== instrumentId ||
      waiter.currency !== currency ||
      pool.quantity < waiter.quantity
    ) {
      remaining.push(waiter);
      continue;
    }
    const position = positionFor(state, waiter.accountId, waiter.instrumentId, waiter.currency);
    position.unsettledIn -= waiter.quantity;
    const cost = takePool(pool, waiter.quantity);
    if (cost === null || position.costMinor === null) position.costMinor = null;
    else position.costMinor += cost;
  }
  state.waiters = remaining;
}

function unbalancedGroups(state: State): string[] {
  const groups = new Set<string>();
  for (const waiter of state.waiters) groups.add(waiter.groupId);
  for (const [key, pool] of state.pools) {
    if (pool.quantity !== 0n) groups.add(key.split("\u0000")[0] ?? key);
  }
  for (const [groupId, byCurrency] of state.groupCash) {
    for (const total of byCurrency.values()) {
      if (total !== 0n) groups.add(groupId);
    }
  }
  return [...groups].sort();
}

function realisedStatus(state: State, reportingCurrency: string): MoneyStatus {
  if (state.realisedMinor === null) return { status: "unavailable" };
  return {
    status: "available",
    currency: state.realisedCurrency ?? reportingCurrency,
    amountMinor: state.realisedMinor,
  };
}

function marketValue(
  positions: readonly Position[],
  reportingCurrency: string,
  rates: readonly FxRate[],
  prices: readonly PriceQuote[],
): MoneyStatus {
  if (positions.length === 0) {
    return { status: "available", currency: reportingCurrency, amountMinor: 0n };
  }
  let total = 0n;
  for (const position of positions) {
    if (position.unsettledIn !== 0n) return { status: "unavailable" };
    const quote = prices.find(
      (price) => price.instrumentId === position.instrumentId && price.currency === position.currency,
    );
    if (!quote) return { status: "unavailable" };
    const native = notionalMinor(position.quantity < 0n ? -position.quantity : position.quantity, quote.unitPriceMinor);
    const signed = position.quantity < 0n ? -native : native;
    const converted = toReporting(signed, position.currency, reportingCurrency, rates);
    if (converted === null) return { status: "unavailable" };
    total += converted;
  }
  return { status: "available", currency: reportingCurrency, amountMinor: total };
}

function reportingCash(buckets: readonly CashBucket[], reportingCurrency: string, rates: readonly FxRate[]): MoneyStatus {
  let total = 0n;
  for (const bucket of buckets) {
    if (bucket.amountMinor === null) return { status: "unavailable" };
    const converted = toReporting(bucket.amountMinor, bucket.currency, reportingCurrency, rates);
    if (converted === null) return { status: "unavailable" };
    total += converted;
  }
  return { status: "available", currency: reportingCurrency, amountMinor: total };
}

function toReporting(amount: bigint, currency: string, reportingCurrency: string, rates: readonly FxRate[]): bigint | null {
  if (currency === reportingCurrency) return amount;
  const rate = rates.find((item) => item.baseCurrency === currency && item.quoteCurrency === reportingCurrency);
  if (!rate) return null;
  return convertMinor(amount, rate.rate);
}

function notionalMinor(quantityScaled: bigint, unitPriceMinor: bigint): bigint {
  const product = quantityScaled * unitPriceMinor;
  const half = QUANTITY_SCALE / 2n;
  return (product + half) / QUANTITY_SCALE;
}

function parseQuantity(value: string): bigint {
  const match = /^(-?)(\d+)(?:\.(\d{1,8}))?$/.exec(value.trim());
  if (!match) throw new Error("invalid quantity");
  const sign = match[1] ?? "";
  const whole = match[2] ?? "0";
  const fraction = (match[3] ?? "").padEnd(8, "0");
  const scaled = BigInt(whole) * QUANTITY_SCALE + BigInt(fraction);
  if (scaled === 0n) throw new Error("invalid quantity");
  return sign === "-" ? -scaled : scaled;
}

function formatQuantity(scaled: bigint): string {
  const negative = scaled < 0n;
  const absolute = negative ? -scaled : scaled;
  const whole = absolute / QUANTITY_SCALE;
  const fraction = (absolute % QUANTITY_SCALE).toString().padStart(8, "0").replace(/0+$/, "");
  const body = fraction.length > 0 ? `${whole.toString()}.${fraction}` : whole.toString();
  return negative ? `-${body}` : body;
}

function positionKey(accountId: string, instrumentId: string): string {
  return `${accountId}\u0000${instrumentId}`;
}

function canonical(event: JournalEvent): string {
  return JSON.stringify({
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
