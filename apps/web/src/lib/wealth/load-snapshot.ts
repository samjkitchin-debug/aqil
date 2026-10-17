import "server-only";

import { connection } from "next/server";

import { isFounderResearchAuthorised } from "@/lib/research/founder-access";
import type { SupabaseClient } from "@supabase/supabase-js";

import { createSupabaseServerClient } from "@/lib/supabase/server";
import { syntheticTechConcentrationFixture } from "@/lib/wealth/fixture-synthetic-tech-concentration";
import type {
  AllocationTarget,
  AssetClass,
  ContributionEvent,
  ContributionPlan,
  WealthPosition,
  WealthSnapshot,
} from "@/lib/wealth/types";

export type WealthLoadResult =
  | { status: "ok"; snapshot: WealthSnapshot }
  | { status: "unauthorized" }
  | { status: "empty" };

const ASSET_CLASSES: AssetClass[] = [
  "global_equity",
  "thematic_technology",
  "investment_grade_bonds",
  "cash_investable",
];

function isAssetClass(value: string): value is AssetClass {
  return (ASSET_CLASSES as string[]).includes(value);
}

export async function loadWealthSnapshot(): Promise<WealthLoadResult> {
  await connection();
  if (!(await isFounderResearchAuthorised())) {
    return { status: "unauthorized" };
  }

  const supabase = (await createSupabaseServerClient()) as SupabaseClient;
  const { data: auth } = await supabase.auth.getUser();
  if (!auth.user) {
    return { status: "ok", snapshot: syntheticTechConcentrationFixture() };
  }

  const userId = auth.user.id;

  const [profileRes, positionsRes, targetsRes, planRes, eventsRes] = await Promise.all([
    supabase.from("wealth_profiles").select("*").eq("user_id", userId).maybeSingle(),
    supabase.from("wealth_positions").select("*").eq("user_id", userId),
    supabase.from("wealth_allocation_targets").select("*").eq("user_id", userId),
    supabase.from("wealth_contribution_plans").select("*").eq("user_id", userId).maybeSingle(),
    supabase
      .from("wealth_contribution_events")
      .select("*")
      .eq("user_id", userId)
      .order("occurred_at", { ascending: false })
      .limit(24),
  ]);

  if (profileRes.error || positionsRes.error || targetsRes.error || planRes.error || eventsRes.error) {
    return { status: "empty" };
  }

  if (!profileRes.data && (positionsRes.data?.length ?? 0) === 0) {
    return { status: "empty" };
  }

  const profile = profileRes.data ?? {
    base_currency: "SGD",
    emergency_reserve_minor: 0,
  };

  const positions: WealthPosition[] = (positionsRes.data ?? []).map((row) => ({
    id: row.id,
    isin: row.isin,
    symbol: row.symbol,
    name: row.name,
    assetClass: isAssetClass(row.asset_class) ? row.asset_class : "global_equity",
    thematicLabel: row.thematic_label,
    currency: row.currency,
    marketValueMinor: BigInt(row.market_value_minor),
    valuationDate: row.valuation_date,
  }));

  const targets: AllocationTarget[] = (targetsRes.data ?? [])
    .filter((row) => isAssetClass(row.asset_class))
    .map((row) => ({
      assetClass: row.asset_class as AssetClass,
      targetWeightBps: row.target_weight_bps,
    }));

  let contributionPlan: ContributionPlan | null = null;
  if (planRes.data) {
    contributionPlan = {
      amountMinor: BigInt(planRes.data.amount_minor),
      currency: planRes.data.currency,
      cadence: "monthly",
      dayOfMonth: planRes.data.day_of_month,
    };
  }

  const contributionHistory: ContributionEvent[] = (eventsRes.data ?? []).map((row) => ({
    id: row.id,
    occurredAt: row.occurred_at,
    amountMinor: BigInt(row.amount_minor),
    currency: row.currency,
    note: row.note,
  }));

  const dates = positions.map((p) => p.valuationDate).filter(Boolean);
  const oldestValuationDate = dates.length ? dates.sort()[0] : null;

  return {
    status: "ok",
    snapshot: {
      source: "database",
      profile: {
        baseCurrency: profile.base_currency,
        emergencyReserveMinor: BigInt(profile.emergency_reserve_minor),
      },
      positions,
      targets,
      contributionPlan,
      contributionHistory,
      dataFreshness: {
        oldestValuationDate,
        missingValuationCount: positions.filter((p) => !p.valuationDate).length,
      },
    },
  };
}
