"use server";

import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/server";

import { parseAssetClass, type InvestableClass } from "../wealth/allocation.ts";
import {
  assertPolicyTargets,
  parseAdditionalCashMajor,
  parseStoredInstrument,
  targetsFromPercentFields,
  toStoredPolicy,
} from "./policy.ts";
import { writeInvestmentPolicyFile } from "./policy-file.ts";

async function requireUserId(): Promise<string> {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/login?error=signed_out&next=%2Fmy-wealth%2Fdeploy");
  return data.user.id;
}

function parseHoldingClasses(formData: FormData): Record<string, InvestableClass> {
  const holdingClasses: Record<string, InvestableClass> = {};
  for (const [name, value] of formData.entries()) {
    if (!name.startsWith("holding_class__")) continue;
    const key = decodeURIComponent(name.slice("holding_class__".length));
    const selected = String(value ?? "").trim();
    if (!key || !selected) continue;
    try {
      const assetClass = parseAssetClass(selected) as InvestableClass;
      if (assetClass === "emergency_reserve") continue;
      holdingClasses[key] = assetClass;
    } catch {
      continue;
    }
  }
  return holdingClasses;
}

function parseInstruments(formData: FormData): ReturnType<typeof parseStoredInstrument>[] {
  const count = Number(formData.get("instrument_count") ?? "0");
  const rows: NonNullable<ReturnType<typeof parseStoredInstrument>>[] = [];
  for (let index = 0; index < count; index += 1) {
    const id = String(formData.get(`instrument_id_${index}`) ?? "").trim();
    const name = String(formData.get(`instrument_name_${index}`) ?? "").trim();
    const assetClass = String(formData.get(`instrument_asset_class_${index}`) ?? "").trim();
    const currency = String(formData.get(`instrument_currency_${index}`) ?? "").trim();
    const minimumUnit = String(formData.get(`instrument_minimum_unit_${index}`) ?? "").trim();
    const priceMajor = String(formData.get(`instrument_price_${index}`) ?? "").trim();
    const costMajorPerUnit = String(formData.get(`instrument_cost_${index}`) ?? "").trim();
    if (!id && !name && !priceMajor) continue;
    const parsed = parseStoredInstrument({
      id,
      name,
      assetClass,
      currency,
      minimumUnit: minimumUnit || "1",
      priceMajor,
      ...(costMajorPerUnit ? { costMajorPerUnit } : {}),
    });
    if (!parsed) redirect("/my-wealth/deploy?error=save_failed");
    rows.push(parsed);
  }
  return rows;
}

export async function saveInvestmentPolicy(formData: FormData): Promise<void> {
  const userId = await requireUserId();
  const fields = Object.fromEntries(
    ["global_equity", "thematic_technology", "investment_grade_bonds", "cash_investable"].map((field) => [
      field,
      String(formData.get(field) ?? "0"),
    ]),
  );
  const targets = targetsFromPercentFields(fields);
  try {
    assertPolicyTargets(targets);
  } catch {
    redirect("/my-wealth/deploy?error=save_failed");
  }
  const additionalCashMajor = parseAdditionalCashMajor(String(formData.get("additional_cash") ?? ""));
  const instruments = parseInstruments(formData).filter((row): row is NonNullable<typeof row> => row !== null);
  const holdingClasses = parseHoldingClasses(formData);
  await writeInvestmentPolicyFile(
    userId,
    toStoredPolicy({
      targets,
      additionalCashMajor,
      instruments,
      holdingClasses,
    }),
  );
  redirect("/my-wealth/deploy?saved=1");
}
