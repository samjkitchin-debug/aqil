import { replayJournal, type JournalEvent, type JournalReplay } from "./journal.ts";
import {
  MANUAL_EVENT_TYPES,
  acceptJournalEvent,
  buildJournalEvent,
  journalCanonical,
  type ManualEventType,
} from "./journal-entry.ts";

export const JOURNAL_CSV_HEADER =
  "idempotency_key,event_type,occurred_on,account_id,currency,cash_amount,instrument_id,quantity,unit_price,split_numerator,split_denominator";

export const CSV_MAX_CHARS = 100_000;
export const CSV_MAX_ROWS = 500;

const COLUMNS = JOURNAL_CSV_HEADER.split(",");

export type HeldRow = { line: number; reason: string };
export type DuplicateRow = { line: number; idempotencyKey: string };

export type CsvPreview = {
  recognised: boolean;
  accepted: JournalEvent[];
  duplicates: DuplicateRow[];
  held: HeldRow[];
  replay: JournalReplay | null;
};

type Candidate = { line: number; event: JournalEvent };

export function previewJournalCsv(
  csv: string,
  reportingCurrency: string,
  existing: readonly JournalEvent[] = [],
): CsvPreview {
  if (csv.length > CSV_MAX_CHARS) {
    return emptyPreview([
      { line: 1, reason: "The file is too large to preview. Nothing was imported." },
    ]);
  }
  const rows = parseCsv(csv.replace(/^\uFEFF/, ""));
  const header = rows[0]?.map((cell) => cell.trim()).join(",");
  if (header !== JOURNAL_CSV_HEADER) {
    return {
      recognised: false,
      accepted: [],
      duplicates: [],
      held: [{ line: 1, reason: "The column headings were not recognised. Nothing was imported." }],
      replay: null,
    };
  }
  const dataRows = rows.slice(1).filter((row) => row.some((cell) => cell.trim() !== ""));
  if (dataRows.length > CSV_MAX_ROWS) {
    return emptyPreview([{ line: 2, reason: "The file has too many rows to preview. Nothing was imported." }]);
  }

  const known = new Map(existing.map((event) => [event.idempotencyKey, event]));
  const duplicates: DuplicateRow[] = [];
  const held: HeldRow[] = [];
  const candidates: Candidate[] = [];
  dataRows.forEach((row, index) => {
    const line = index + 2;
    if (row.length !== COLUMNS.length) {
      held.push({ line, reason: "This row does not match the column headings." });
      return;
    }
    const record = Object.fromEntries(COLUMNS.map((column, columnIndex) => [column, row[columnIndex] ?? ""]));
    try {
      const event = eventFromRow(record);
      const prior = known.get(event.idempotencyKey);
      if (prior) {
        if (journalCanonical(prior) === journalCanonical(event)) {
          duplicates.push({ line, idempotencyKey: event.idempotencyKey });
          return;
        }
        held.push({ line, reason: "This idempotency key already identifies a different entry." });
        return;
      }
      known.set(event.idempotencyKey, event);
      candidates.push({ line, event });
    } catch (error) {
      held.push({ line, reason: holdReason(error) });
    }
  });

  const accepted: JournalEvent[] = [];
  for (const candidate of candidates) {
    try {
      replayJournal([...existing, ...accepted, candidate.event], reportingCurrency);
      accepted.push(candidate.event);
    } catch {
      held.push({ line: candidate.line, reason: "This row was held because it does not fit the journal." });
    }
  }
  held.sort((left, right) => left.line - right.line);
  return {
    recognised: true,
    accepted,
    duplicates,
    held,
    replay: replayJournal([...existing, ...accepted], reportingCurrency),
  };
}

export function applyAcceptedPreview(
  events: readonly JournalEvent[],
  preview: CsvPreview,
  reportingCurrency: string,
): JournalEvent[] {
  let next = [...events];
  for (const event of preview.accepted) {
    next = acceptJournalEvent(next, event, reportingCurrency).events;
  }
  return next;
}

function eventFromRow(row: Record<string, string>): JournalEvent {
  const eventType = row.event_type?.trim() ?? "";
  if (!MANUAL_EVENT_TYPES.includes(eventType as ManualEventType)) {
    throw new Error("unrecognised type");
  }
  for (const value of Object.values(row)) {
    if (value.trim().startsWith("-") || value.trim().startsWith("+")) throw new Error("ambiguous sign");
  }
  return buildJournalEvent({
    eventId: row.idempotency_key ?? "",
    idempotencyKey: row.idempotency_key ?? "",
    eventType: eventType as ManualEventType,
    occurredOn: row.occurred_on ?? "",
    accountId: row.account_id ?? "",
    currency: row.currency ?? "",
    instrumentId: row.instrument_id ?? "",
    quantity: row.quantity ?? "",
    cashAmount: row.cash_amount ?? "",
    unitPrice: row.unit_price ?? "",
    splitNumerator: row.split_numerator ?? "",
    splitDenominator: row.split_denominator ?? "",
    rejectPriceMismatch: true,
  });
}

function holdReason(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (message === "ambiguous amount") return "The cash amount does not match the unit price and quantity.";
  if (message === "ambiguous sign") return "A signed amount is held for review.";
  if (message === "unrecognised type") return "The entry type is not recognised.";
  if (message === "invalid currency") return "The currency is invalid.";
  if (message === "invalid amount" || message === "too many decimal places" || message === "invalid quantity") {
    return "The amount or quantity is invalid.";
  }
  return "This row is missing a required field.";
}

function emptyPreview(held: HeldRow[]): CsvPreview {
  return { recognised: false, accepted: [], duplicates: [], held, replay: null };
}

function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"') {
        if (text[index + 1] === '"') {
          field += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        field += char ?? "";
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (char !== "\r") {
      field += char ?? "";
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}
