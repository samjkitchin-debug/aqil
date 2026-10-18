import "server-only";

import { connection } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

import { parseAssetClass, type AssetClass, type Environment } from "./allocation";

export type WealthAccount = {
  id: string;
  name: string;
  provider: string;
  environment: Environment;
  currency: string;
  sourceStatus: string;
};

export type WealthHolding = {
  id: string;
  accountId: string;
  accountName: string;
  environment: Environment;
  name: string;
  isin: string | null;
  assetClass: AssetClass;
  quantity: string;
  currency: string;
  amountMinor: bigint;
  asOf: string;
};

export type WealthSnapshot = {
  reportingCurrency: string;
  accounts: WealthAccount[];
  holdings: WealthHolding[];
  quarantined: string[];
  targets: { assetClass: AssetClass; targetWeightBps: number }[];
  fx: { baseCurrency: string; quoteCurrency: string; rate: string; observationDate: string }[];
};

export type WealthLoad =
  | { status: "unauthorized" }
  | { status: "storage_pending" }
  | { status: "empty" }
  | { status: "ok"; snapshot: WealthSnapshot };

function relationMissing(error: { code?: string; message?: string } | null): boolean {
  if (!error) return false;
  const message = (error.message ?? "").toLowerCase();
  return error.code === "42P01" || error.code === "PGRST205" || message.includes("wealth_");
}

export async function loadWealthSnapshot(): Promise<WealthLoad> {
  await connection();
  const supabase = await createSupabaseServerClient();
  const { data: auth } = await supabase.auth.getUser();
  if (!auth.user) return { status: "unauthorized" };

  const [accountsRes, instrumentsRes, valuationsRes, targetsRes, fxRes, profileRes] = await Promise.all([
    supabase.from("wealth_accounts").select("*").eq("user_id", auth.user.id),
    supabase.from("wealth_instruments").select("*").eq("user_id", auth.user.id),
    supabase.from("wealth_valuations").select("*").eq("user_id", auth.user.id).order("created_at", { ascending: false }),
    supabase.from("wealth_allocation_targets").select("*").eq("user_id", auth.user.id),
    supabase.from("wealth_fx_rates").select("*").eq("user_id", auth.user.id),
    supabase.from("wealth_profiles").select("*").eq("user_id", auth.user.id).maybeSingle(),
  ]);

  const errors = [accountsRes.error, instrumentsRes.error, valuationsRes.error, targetsRes.error, fxRes.error, profileRes.error];
  if (errors.some(relationMissing)) return { status: "storage_pending" };
  if (errors.some(Boolean)) return { status: "empty" };

  const accounts: WealthAccount[] = (accountsRes.data ?? []).map((row) => ({
    id: row.id,
    name: row.name,
    provider: row.provider,
    environment: row.environment === "simulation" ? "simulation" : "live",
    currency: row.currency,
    sourceStatus: row.source_status,
  }));
  if (accounts.length === 0 && (valuationsRes.data ?? []).length === 0) {
    return { status: "empty" };
  }

  const accountById = new Map(accounts.map((account) => [account.id, account]));
  const instruments = new Map((instrumentsRes.data ?? []).map((row) => [row.id, row]));
  const seen = new Set<string>();
  const holdings: WealthHolding[] = [];
  const quarantined: string[] = [];

  for (const row of valuationsRes.data ?? []) {
    const key = `${row.account_id}:${row.instrument_id}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const instrument = instruments.get(row.instrument_id);
    const account = accountById.get(row.account_id);
    if (!instrument || !account) continue;
    try {
      holdings.push({
        id: row.id,
        accountId: account.id,
        accountName: account.name,
        environment: account.environment,
        name: instrument.name,
        isin: instrument.isin,
        assetClass: parseAssetClass(instrument.asset_class),
        quantity: String(row.quantity),
        currency: row.currency,
        amountMinor: BigInt(row.amount_minor),
        asOf: row.as_of,
      });
    } catch {
      quarantined.push(instrument.name);
    }
  }

  return {
    status: "ok",
    snapshot: {
      reportingCurrency: profileRes.data?.reporting_currency ?? "SGD",
      accounts,
      holdings,
      quarantined,
      targets: (targetsRes.data ?? []).flatMap((row) => {
        try {
          return [{ assetClass: parseAssetClass(row.asset_class), targetWeightBps: row.target_weight_bps }];
        } catch {
          return [];
        }
      }),
      fx: (fxRes.data ?? []).map((row) => ({
        baseCurrency: row.base_currency,
        quoteCurrency: row.quote_currency,
        rate: String(row.rate),
        observationDate: row.observation_date,
      })),
    },
  };
}
