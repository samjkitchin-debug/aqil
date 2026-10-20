"use server";

import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/server";

import { isIsoDate } from "./journal-entry.ts";
import { assertJournalUserId, readJournalFile, writeJournalFile } from "./journal-store.ts";
import {
  appendManualEntry,
  clearJournalPreview,
  commitJournalCsv,
  recordSuppliedPrice,
  recordSuppliedRate,
  stageJournalCsv,
} from "./journal-workflow.ts";

const NEXT = "/my-wealth/journal";

function rethrowRedirect(error: unknown): void {
  if (
    typeof error === "object" &&
    error !== null &&
    "digest" in error &&
    String((error as { digest?: unknown }).digest).startsWith("NEXT_REDIRECT")
  ) {
    throw error;
  }
}

function go(error?: string, asOf?: string): never {
  const params = new URLSearchParams();
  if (error) params.set("error", error);
  if (asOf && isIsoDate(asOf)) params.set("asOf", asOf);
  const query = params.toString();
  redirect(query ? `${NEXT}?${query}` : NEXT);
}

function viewedAsOf(formData: FormData): string | undefined {
  const value = String(formData.get("as_of_view") ?? "");
  return isIsoDate(value) ? value : undefined;
}

async function requireUserId(): Promise<string> {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect(`/login?error=signed_out&next=${encodeURIComponent(NEXT)}`);
  try {
    return assertJournalUserId(data.user.id);
  } catch (error) {
    rethrowRedirect(error);
    go("unreadable");
  }
}

function entryError(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (message === "invalid currency" || message === "position currency does not match") return "currency";
  if (message.includes("idempotency")) return "conflict";
  if (message === "invalid amount" || message === "too many decimal places" || message === "invalid quantity") {
    return "amount";
  }
  if (message === "missing field") return "missing";
  if (message === "unreadable") return "unreadable";
  return "rejected";
}

function priceError(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (message === "invalid currency") return "currency";
  if (message === "conflict") return "price_conflict";
  return "price";
}

function rateError(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (message === "conflict") return "rate_conflict";
  return "rate";
}

export async function saveJournalEntry(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const asOf = viewedAsOf(formData);
  try {
    const file = await readJournalFile(userId);
    const next = appendManualEntry(file, {
      eventType: String(formData.get("event_type") ?? ""),
      occurredOn: String(formData.get("occurred_on") ?? ""),
      accountId: String(formData.get("account_id") ?? ""),
      currency: String(formData.get("currency") ?? ""),
      cashAmount: String(formData.get("cash_amount") ?? ""),
      instrumentId: String(formData.get("instrument_id") ?? ""),
      quantity: String(formData.get("quantity") ?? ""),
      unitPrice: String(formData.get("unit_price") ?? ""),
      splitNumerator: String(formData.get("split_numerator") ?? ""),
      splitDenominator: String(formData.get("split_denominator") ?? ""),
      draftId: String(formData.get("draft_id") ?? ""),
    });
    await writeJournalFile(userId, next);
  } catch (error) {
    rethrowRedirect(error);
    const message = error instanceof Error ? error.message : "";
    go(message === "unreadable" ? "unreadable" : entryError(error), asOf);
  }
  go(undefined, asOf);
}

export async function saveSuppliedPrice(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const asOf = viewedAsOf(formData);
  try {
    const file = await readJournalFile(userId);
    const next = recordSuppliedPrice(file, {
      instrumentId: String(formData.get("instrument_id") ?? ""),
      currency: String(formData.get("currency") ?? ""),
      unitPrice: String(formData.get("unit_price") ?? ""),
      asOf: String(formData.get("as_of") ?? ""),
    });
    await writeJournalFile(userId, next);
  } catch (error) {
    rethrowRedirect(error);
    const message = error instanceof Error ? error.message : "";
    go(message === "unreadable" ? "unreadable" : priceError(error), asOf);
  }
  go(undefined, asOf);
}

export async function saveSuppliedRate(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const asOf = viewedAsOf(formData);
  try {
    const file = await readJournalFile(userId);
    const next = recordSuppliedRate(file, {
      baseCurrency: String(formData.get("base_currency") ?? ""),
      quoteCurrency: String(formData.get("quote_currency") ?? ""),
      rate: String(formData.get("rate") ?? ""),
      asOf: String(formData.get("as_of") ?? ""),
    });
    await writeJournalFile(userId, next);
  } catch (error) {
    rethrowRedirect(error);
    const message = error instanceof Error ? error.message : "";
    go(message === "unreadable" ? "unreadable" : rateError(error), asOf);
  }
  go(undefined, asOf);
}

export async function saveJournalPreview(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const asOf = viewedAsOf(formData);
  try {
    const file = await readJournalFile(userId);
    const next = stageJournalCsv(file, String(formData.get("csv") ?? ""));
    await writeJournalFile(userId, next);
  } catch (error) {
    rethrowRedirect(error);
    go("preview", asOf);
  }
  go(undefined, asOf);
}

export async function applyJournalPreview(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const asOf = viewedAsOf(formData);
  try {
    const file = await readJournalFile(userId);
    const next = commitJournalCsv(file);
    await writeJournalFile(userId, next);
  } catch (error) {
    rethrowRedirect(error);
    go("unreadable", asOf);
  }
  go(undefined, asOf);
}

export async function discardJournalPreview(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const asOf = viewedAsOf(formData);
  try {
    const file = await readJournalFile(userId);
    await writeJournalFile(userId, clearJournalPreview(file));
  } catch (error) {
    rethrowRedirect(error);
    go("unreadable", asOf);
  }
  go(undefined, asOf);
}
