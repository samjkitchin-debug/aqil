export type SourceEvent = {
  kind: "booking" | "trade" | "transaction" | "lot" | "order-event" | "historical-position" | "series-point" | "aggregated-amount";
  id: string;
  corrects: string | null;
  corporateActionId: string | null;
};

const CORRECTION_FIELDS = ["CorrectionOf", "CorrectsBookingId", "CorrectsTradeId", "OriginalBookingId", "OriginalTradeId"] as const;

/**
 * Indexes Saxo ids without dropping nested bookings or trades.
 * A new booking or trade id is its own event. A correction link is set only from an explicit Saxo field.
 */
export function indexSourceEvents(body: unknown): SourceEvent[] {
  const events: SourceEvent[] = [];
  const rows = arrayData(body);
  const records = rows.length > 0 ? rows : [body];
  for (const row of records) {
    const record = asRecord(row);
    if (!record) continue;
    const corporateActionId = text(record.CorporateActionId);
    const tradeId = text(record.TradeId);
    const bookingId = text(record.BookingId);
    const positionId = text(record.PositionId);
    const logId = text(record.LogId);
    if (tradeId || corporateActionId || bookingId) {
      const transactionId = tradeId
        ? `transaction:${tradeId}`
        : corporateActionId
          ? `transaction:${corporateActionId}:${text(record.Date) ?? ""}`
          : `transaction:${bookingId}`;
      events.push({
        kind: "transaction",
        id: transactionId,
        corrects: correctionTarget(record, "transaction"),
        corporateActionId,
      });
    }
    if (positionId && record.PositionBase) {
      events.push({
        kind: "lot",
        id: `position:${positionId}`,
        corrects: null,
        corporateActionId: null,
      });
    } else if (record.ExecutionTimeClose || record.ClosingTradeDate) {
      const account = text(record.AccountId) ?? "";
      const instrument = text(record.InstrumentSymbol) ?? text(record.Uic) ?? "";
      const open = text(record.ExecutionTimeOpen) ?? "";
      const close = text(record.ExecutionTimeClose) ?? text(record.ClosingTradeDate) ?? "";
      events.push({
        kind: "historical-position",
        id: `historical:${account}:${instrument}:${open}:${close}`,
        corrects: null,
        corporateActionId: null,
      });
    }
    if (logId) {
      events.push({ kind: "order-event", id: `order-event:${logId}`, corrects: null, corporateActionId: null });
    }
    if (record.AmountTypeId != null && record.Date && record.Amount != null && !bookingId) {
      const account = text(record.BookingAccountId) ?? text(record.AccountId) ?? "";
      const uic = record.Uic == null ? "" : String(record.Uic);
      const currency = text(record.AccountCurrency) ?? text(record.Currency) ?? "";
      events.push({
        kind: "aggregated-amount",
        id: `aggregated:${account}:${text(record.Date)}:${String(record.AmountTypeId)}:${uic}:${currency}`,
        corrects: null,
        corporateActionId: null,
      });
    }
    if (record.Date && record.Value != null && text(record.Field)) {
      events.push({
        kind: "series-point",
        id: `series:${text(record.Field)}:${text(record.Scope) ?? ""}:${text(record.Date)}`,
        corrects: null,
        corporateActionId: null,
      });
    }
    for (const booking of nestedArray(record.Bookings)) {
      const item = asRecord(booking);
      const id = text(item?.BookingId);
      if (!item || !id) continue;
      events.push({
        kind: "booking",
        id: `booking:${id}`,
        corrects: correctionTarget(item, "booking"),
        corporateActionId,
      });
    }
    for (const trade of nestedArray(record.Trades)) {
      const item = asRecord(trade);
      const id = text(item?.TradeId);
      if (!item || !id) continue;
      events.push({
        kind: "trade",
        id: `trade:${id}`,
        corrects: correctionTarget(item, "trade"),
        corporateActionId,
      });
    }
  }
  return events;
}

function correctionTarget(record: Record<string, unknown>, kind: "booking" | "trade" | "transaction"): string | null {
  for (const field of CORRECTION_FIELDS) {
    const value = text(record[field]);
    if (!value) continue;
    if (field === "CorrectsTradeId" || field === "OriginalTradeId") return `trade:${value}`;
    if (field === "CorrectsBookingId" || field === "OriginalBookingId") return `booking:${value}`;
    return `${kind}:${value}`;
  }
  return null;
}

function nestedArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function arrayData(body: unknown): unknown[] {
  if (Array.isArray(body)) return body;
  const data = asRecord(body)?.Data;
  return Array.isArray(data) ? data : [];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function text(value: unknown): string | null {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return typeof value === "string" && value.length > 0 ? value : null;
}
