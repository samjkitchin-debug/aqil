import type { WealthSnapshot } from "./types";

export type WealthSnapshotWire = {
  source: WealthSnapshot["source"];
  profile: { baseCurrency: string; emergencyReserveMinor: string };
  positions: {
    id: string;
    isin: string | null;
    symbol: string | null;
    name: string;
    assetClass: string;
    thematicLabel: string | null;
    currency: string;
    marketValueMinor: string;
    valuationDate: string;
  }[];
  targets: { assetClass: string; targetWeightBps: number }[];
  contributionPlan: {
    amountMinor: string;
    currency: string;
    cadence: "monthly";
    dayOfMonth: number | null;
  } | null;
  contributionHistory: {
    id: string;
    occurredAt: string;
    amountMinor: string;
    currency: string;
    note: string | null;
  }[];
  dataFreshness: WealthSnapshot["dataFreshness"];
};

export function toWire(snapshot: WealthSnapshot): WealthSnapshotWire {
  return {
    source: snapshot.source,
    profile: {
      baseCurrency: snapshot.profile.baseCurrency,
      emergencyReserveMinor: snapshot.profile.emergencyReserveMinor.toString(),
    },
    positions: snapshot.positions.map((p) => ({
      ...p,
      marketValueMinor: p.marketValueMinor.toString(),
    })),
    targets: snapshot.targets,
    contributionPlan: snapshot.contributionPlan
      ? {
          ...snapshot.contributionPlan,
          amountMinor: snapshot.contributionPlan.amountMinor.toString(),
        }
      : null,
    contributionHistory: snapshot.contributionHistory.map((e) => ({
      ...e,
      amountMinor: e.amountMinor.toString(),
    })),
    dataFreshness: snapshot.dataFreshness,
  };
}

export function fromWire(wire: WealthSnapshotWire): WealthSnapshot {
  return {
    source: wire.source,
    profile: {
      baseCurrency: wire.profile.baseCurrency,
      emergencyReserveMinor: BigInt(wire.profile.emergencyReserveMinor),
    },
    positions: wire.positions.map((p) => ({
      id: p.id,
      isin: p.isin,
      symbol: p.symbol,
      name: p.name,
      assetClass: p.assetClass as WealthSnapshot["positions"][0]["assetClass"],
      thematicLabel: p.thematicLabel,
      currency: p.currency,
      marketValueMinor: BigInt(p.marketValueMinor),
      valuationDate: p.valuationDate,
    })),
    targets: wire.targets.map((t) => ({
      assetClass: t.assetClass as WealthSnapshot["targets"][0]["assetClass"],
      targetWeightBps: t.targetWeightBps,
    })),
    contributionPlan: wire.contributionPlan
      ? {
          amountMinor: BigInt(wire.contributionPlan.amountMinor),
          currency: wire.contributionPlan.currency,
          cadence: "monthly",
          dayOfMonth: wire.contributionPlan.dayOfMonth,
        }
      : null,
    contributionHistory: wire.contributionHistory.map((e) => ({
      id: e.id,
      occurredAt: e.occurredAt,
      amountMinor: BigInt(e.amountMinor),
      currency: e.currency,
      note: e.note,
    })),
    dataFreshness: wire.dataFreshness,
  };
}
