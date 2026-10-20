import { applyAcceptedPreview, CSV_MAX_CHARS, previewJournalCsv, type CsvPreview } from "./journal-csv.ts";
import {
  acceptJournalEvent,
  assertJournalCurrency,
  isIsoDate,
  parseManualEntry,
  type ManualEntryInput,
} from "./journal-entry.ts";
import type { JournalFile } from "./journal-store.ts";
import { parseMajorToMinor } from "./money.ts";
import {
  addSuppliedPrice,
  addSuppliedRate,
  explainMarketValue,
  ratesOn,
  unrealisedGain,
  type MarketValueView,
} from "./journal-valuation.ts";
import {
  externalContributions,
  moneyWeightedReturn,
  portfolioTotal,
  timeWeightedReturn,
  TWR_UNAVAILABLE,
  valuedPoints,
  XIRR_UNAVAILABLE,
  type SolvedRate,
} from "./journal-returns.ts";
import type { JournalEvent, JournalReplay, MoneyStatus } from "./journal.ts";

export type JournalSummary = {
  asOf: string;
  reportingCurrency: "SGD";
  events: JournalEvent[];
  replay: JournalReplay;
  market: MarketValueView;
  total: MoneyStatus;
  realisedProfit: MoneyStatus;
  unrealisedGain: MoneyStatus;
  netContributions: MoneyStatus;
  xirr: SolvedRate;
  twr: SolvedRate;
  preview: CsvPreview | null;
};

export function resolveAsOf(requested: string | undefined, file: Pick<JournalFile, "events" | "prices" | "rates">): string {
  if (requested && isIsoDate(requested)) return requested;
  const dates = [
    ...file.events.map((event) => event.occurredOn),
    ...file.prices.map((price) => price.asOf),
    ...file.rates.map((rate) => rate.asOf),
  ].sort();
  return dates[dates.length - 1] ?? new Date().toISOString().slice(0, 10);
}

export function summariseJournal(file: JournalFile, requestedAsOf?: string): JournalSummary {
  const asOf = resolveAsOf(requestedAsOf, file);
  const explained = explainMarketValue(file.events, file.prices, file.rates, file.reportingCurrency, asOf);
  const contributions = externalContributions(file.events, file.rates, file.reportingCurrency, asOf);
  const totalMoney = portfolioTotal(explained.replay);
  const total: MoneyStatus = totalMoney
    ? { status: "available", currency: totalMoney.currency, amountMinor: totalMoney.amountMinor }
    : { status: "unavailable" };
  const netContributions: MoneyStatus = contributions.status === "available"
    ? {
        status: "available",
        currency: file.reportingCurrency,
        amountMinor: contributions.flows.reduce((sum, flow) => sum + flow.amountMinor, 0n),
      }
    : { status: "unavailable" };
  const terminal = totalMoney ? { asOf, amountMinor: totalMoney.amountMinor } : null;
  const xirr = contributions.status === "available"
    ? moneyWeightedReturn({ contributions: contributions.flows, terminal })
    : { status: "unavailable" as const, reason: XIRR_UNAVAILABLE };
  const points = contributions.status === "available"
    ? valuedPoints({
        events: file.events,
        prices: file.prices,
        rates: file.rates,
        reportingCurrency: file.reportingCurrency,
        asOf,
        contributions: contributions.flows,
      })
    : { status: "unavailable" as const };
  const twr = points.status === "available"
    ? timeWeightedReturn({ points: points.points, contributions: contributions.status === "available" ? contributions.flows : [], asOf })
    : { status: "unavailable" as const, reason: TWR_UNAVAILABLE };
  const preview = file.previewCsv
    ? previewJournalCsv(file.previewCsv, file.reportingCurrency, file.events)
    : null;
  return {
    asOf,
    reportingCurrency: file.reportingCurrency,
    events: [...file.events].sort(
      (left, right) => left.occurredOn.localeCompare(right.occurredOn) || left.eventId.localeCompare(right.eventId),
    ),
    replay: explained.replay,
    market: explained.market,
    total,
    realisedProfit: explained.replay.realisedProfit,
    unrealisedGain: unrealisedGain(
      explained.replay,
      ratesOn(file.rates, asOf, file.reportingCurrency),
      file.reportingCurrency,
    ),
    netContributions,
    xirr,
    twr,
    preview,
  };
}

export function safeQueryDate(value: string | undefined): string | undefined {
  return value && isIsoDate(value) ? value : undefined;
}

const LABEL = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/;

export function appendManualEntry(file: JournalFile, input: ManualEntryInput): JournalFile {
  const event = parseManualEntry(input);
  const accepted = acceptJournalEvent(file.events, event, file.reportingCurrency);
  if (!accepted.added) return file;
  return { ...file, events: accepted.events };
}

export function recordSuppliedPrice(
  file: JournalFile,
  input: { instrumentId: string; currency: string; unitPrice: string; asOf: string },
): JournalFile {
  const asOf = input.asOf.trim();
  if (!isIsoDate(asOf)) throw new Error("missing field");
  const instrumentId = input.instrumentId.trim();
  if (!LABEL.test(instrumentId)) throw new Error("missing field");
  const currency = input.currency.trim() === "" ? "" : assertJournalCurrency(input.currency);
  if (currency === "") throw new Error("missing field");
  const unitPriceMinor = parseMajorToMinor(input.unitPrice, currency);
  if (unitPriceMinor <= 0n) throw new Error("invalid amount");
  return {
    ...file,
    prices: addSuppliedPrice(file.prices, {
      instrumentId,
      currency,
      unitPriceMinor,
      asOf,
      source: "supplied",
    }),
  };
}

export function recordSuppliedRate(
  file: JournalFile,
  input: { baseCurrency: string; quoteCurrency: string; rate: string; asOf: string },
): JournalFile {
  const asOf = input.asOf.trim();
  if (!isIsoDate(asOf)) throw new Error("missing field");
  const quoteCurrency = assertJournalCurrency(input.quoteCurrency);
  if (quoteCurrency !== file.reportingCurrency) throw new Error("invalid rate");
  return {
    ...file,
    rates: addSuppliedRate(file.rates, {
      baseCurrency: assertJournalCurrency(input.baseCurrency),
      quoteCurrency,
      rate: input.rate.trim(),
      asOf,
      source: "supplied",
    }),
  };
}

export function stageJournalCsv(file: JournalFile, csv: string): JournalFile {
  if (csv.trim() === "") throw new Error("missing field");
  if (csv.length > CSV_MAX_CHARS) throw new Error("too large");
  previewJournalCsv(csv, file.reportingCurrency, file.events);
  return { ...file, previewCsv: csv };
}

export function commitJournalCsv(file: JournalFile): JournalFile {
  if (!file.previewCsv) return file;
  const preview = previewJournalCsv(file.previewCsv, file.reportingCurrency, file.events);
  if (!preview.recognised || preview.accepted.length === 0) return file;
  return {
    ...file,
    events: applyAcceptedPreview(file.events, preview, file.reportingCurrency),
  };
}

export function clearJournalPreview(file: JournalFile): JournalFile {
  if (file.previewCsv === null) return file;
  return { ...file, previewCsv: null };
}

