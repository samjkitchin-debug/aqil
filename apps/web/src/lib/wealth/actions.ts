"use server";

import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/server";

import { assertTargets, parseAssetClass } from "./allocation";
import { parseMajorToMinor } from "./money";

async function requireUserId(): Promise<string> {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/login?error=signed_out&next=%2Fmy-wealth");
  return data.user.id;
}

export async function createAccount(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const supabase = await createSupabaseServerClient();
  const name = String(formData.get("name") ?? "").trim();
  const provider = String(formData.get("provider") ?? "manual");
  const environment = String(formData.get("environment") ?? "live");
  const currency = String(formData.get("currency") ?? "SGD").toUpperCase();
  const { error } = await supabase.from("wealth_accounts").insert({
    user_id: userId,
    name,
    provider,
    environment,
    currency,
    source_status: "manual",
  });
  if (error) redirect("/my-wealth?error=save_failed");
  redirect("/my-wealth");
}

export async function recordHolding(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const supabase = await createSupabaseServerClient();
  const accountId = String(formData.get("account_id") ?? "");
  const name = String(formData.get("name") ?? "").trim();
  const isin = String(formData.get("isin") ?? "").trim() || null;
  const currency = String(formData.get("currency") ?? "SGD").toUpperCase();
  const quantity = String(formData.get("quantity") ?? "").trim();
  const asOf = String(formData.get("as_of") ?? "");
  let assetClass;
  let amountMinor;
  try {
    assetClass = parseAssetClass(String(formData.get("asset_class") ?? ""));
    amountMinor = parseMajorToMinor(String(formData.get("amount") ?? ""), currency);
  } catch {
    redirect("/my-wealth?error=save_failed");
  }

  let instrumentId: string | null = null;
  if (isin) {
    const existing = await supabase
      .from("wealth_instruments")
      .select("id")
      .eq("user_id", userId)
      .eq("isin", isin)
      .maybeSingle();
    instrumentId = existing.data?.id ?? null;
  }
  if (!instrumentId) {
    const created = await supabase
      .from("wealth_instruments")
      .insert({ user_id: userId, name, isin, asset_class: assetClass, currency })
      .select("id")
      .single();
    if (created.error || !created.data) redirect("/my-wealth?error=save_failed");
    instrumentId = created.data.id;
  }

  const saved = await supabase.from("wealth_valuations").insert({
    user_id: userId,
    account_id: accountId,
    instrument_id: instrumentId,
    quantity,
    currency,
    amount_minor: amountMinor.toString(),
    as_of: asOf,
    provenance: "manual",
  });
  if (saved.error) redirect("/my-wealth?error=save_failed");
  redirect("/my-wealth");
}

export async function saveTargets(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const supabase = await createSupabaseServerClient();
  const rows = [
    ["global_equity", "global_equity"],
    ["thematic_technology", "thematic_technology"],
    ["investment_grade_bonds", "investment_grade_bonds"],
    ["cash_investable", "cash_investable"],
  ].map(([field, assetClass]) => ({
    assetClass: parseAssetClass(assetClass) as "global_equity" | "thematic_technology" | "investment_grade_bonds" | "cash_investable",
    targetWeightBps: Math.round(Number(formData.get(field) ?? "0") * 100),
  }));
  try {
    assertTargets(rows);
  } catch {
    redirect("/my-wealth?error=save_failed");
  }
  const removed = await supabase.from("wealth_allocation_targets").delete().eq("user_id", userId);
  if (removed.error) redirect("/my-wealth?error=save_failed");
  const inserted = await supabase.from("wealth_allocation_targets").insert(
    rows.map((row) => ({
      user_id: userId,
      asset_class: row.assetClass,
      target_weight_bps: row.targetWeightBps,
    })),
  );
  if (inserted.error) redirect("/my-wealth?error=save_failed");
  redirect("/my-wealth");
}
