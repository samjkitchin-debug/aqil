import { assertTargets, parseAssetClass, type InvestableClass, type Target } from "../wealth/allocation.ts";
import { parseMajorToMinor } from "../wealth/money.ts";
import type { ApprovedInstrument } from "./deploy.ts";

export const POLICY_VERSION = 1 as const;

export type StoredInstrument = {
  id: string;
  name: string;
  assetClass: InvestableClass;
  currency: string;
  minimumUnit: string;
  priceMajor: string;
  costMajorPerUnit?: string;
};

export type StoredInvestmentPolicy = {
  version: typeof POLICY_VERSION;
  targets: Target[];
  /** Null means the founder left the budget blank. */
  additionalCashMajor: string | null;
  instruments: StoredInstrument[];
  holdingClasses: Record<string, InvestableClass>;
};

export type InvestmentPolicy = {
  targets: Target[] | null;
  additionalCashMinor: bigint | null;
  instruments: ApprovedInstrument[] | null;
  holdingClasses: Readonly<Record<string, InvestableClass>>;
};

const INVESTABLE_FIELDS = [
  "global_equity",
  "thematic_technology",
  "investment_grade_bonds",
  "cash_investable",
] as const satisfies readonly InvestableClass[];

export function targetsFromPercentFields(
  fields: Readonly<Record<string, string>>,
): Target[] {
  return INVESTABLE_FIELDS.map((assetClass) => ({
    assetClass,
    targetWeightBps: Math.round(Number(fields[assetClass] ?? "0") * 100),
  }));
}

export function parseAdditionalCashMajor(value: string | null | undefined): string | null {
  const trimmed = String(value ?? "").trim();
  return trimmed.length === 0 ? null : trimmed;
}

export function additionalCashMinorFromMajor(
  additionalCashMajor: string | null,
  currency: string,
): bigint | null {
  if (additionalCashMajor === null) return null;
  try {
    return parseMajorToMinor(additionalCashMajor, currency);
  } catch {
    throw new Error("investment budget is not a valid amount");
  }
}

export function parseStoredInstrument(row: unknown): StoredInstrument | null {
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const source = row as Record<string, unknown>;
  const id = String(source.id ?? "").trim();
  const name = String(source.name ?? "").trim();
  const currency = String(source.currency ?? "").trim().toUpperCase();
  const minimumUnit = String(source.minimumUnit ?? "").trim();
  const priceMajor = String(source.priceMajor ?? "").trim();
  if (!id || !name || !currency || !minimumUnit || !priceMajor) return null;
  let assetClass: InvestableClass;
  try {
    assetClass = parseAssetClass(String(source.assetClass ?? "")) as InvestableClass;
    if (assetClass === "emergency_reserve") return null;
  } catch {
    return null;
  }
  const costMajorPerUnit = String(source.costMajorPerUnit ?? "").trim();
  return {
    id,
    name,
    assetClass,
    currency,
    minimumUnit,
    priceMajor,
    ...(costMajorPerUnit ? { costMajorPerUnit } : {}),
  };
}

export function approvedInstrumentFromStored(row: StoredInstrument): ApprovedInstrument {
  const minimumUnit = BigInt(row.minimumUnit);
  const priceMinor = parseMajorToMinor(row.priceMajor, row.currency);
  const costMinorPerUnit = row.costMajorPerUnit
    ? parseMajorToMinor(row.costMajorPerUnit, row.currency)
    : undefined;
  return {
    id: row.id,
    name: row.name,
    assetClass: row.assetClass,
    currency: row.currency,
    minimumUnit,
    priceMinor,
    ...(costMinorPerUnit !== undefined ? { costMinorPerUnit } : {}),
  };
}

export function parseStoredPolicy(raw: unknown): StoredInvestmentPolicy | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const source = raw as Record<string, unknown>;
  if (source.version !== POLICY_VERSION) return null;
  if (!Array.isArray(source.targets)) return null;
  const targets: Target[] = [];
  for (const row of source.targets) {
    if (!row || typeof row !== "object" || Array.isArray(row)) return null;
    const item = row as Record<string, unknown>;
    try {
      const assetClass = parseAssetClass(String(item.assetClass ?? "")) as InvestableClass;
      if (assetClass === "emergency_reserve") return null;
      const targetWeightBps = Number(item.targetWeightBps);
      if (!Number.isInteger(targetWeightBps)) return null;
      targets.push({ assetClass, targetWeightBps });
    } catch {
      return null;
    }
  }
  const additionalCashMajor =
    source.additionalCashMajor === null
      ? null
      : parseAdditionalCashMajor(String(source.additionalCashMajor ?? ""));
  if (source.additionalCashMajor !== null && additionalCashMajor === null && String(source.additionalCashMajor ?? "").trim() !== "") {
    return null;
  }
  if (!Array.isArray(source.instruments)) return null;
  const instruments: StoredInstrument[] = [];
  for (const row of source.instruments) {
    const parsed = parseStoredInstrument(row);
    if (!parsed) return null;
    instruments.push(parsed);
  }
  if (!source.holdingClasses || typeof source.holdingClasses !== "object" || Array.isArray(source.holdingClasses)) {
    return null;
  }
  const holdingClasses: Record<string, InvestableClass> = {};
  for (const [key, value] of Object.entries(source.holdingClasses as Record<string, unknown>)) {
    if (!key.trim()) continue;
    try {
      const assetClass = parseAssetClass(String(value ?? "")) as InvestableClass;
      if (assetClass === "emergency_reserve") return null;
      holdingClasses[key] = assetClass;
    } catch {
      return null;
    }
  }
  return {
    version: POLICY_VERSION,
    targets,
    additionalCashMajor,
    instruments,
    holdingClasses,
  };
}

export function assertPolicyTargets(targets: readonly Target[]): void {
  assertTargets(targets);
}

export function policyFromStored(stored: StoredInvestmentPolicy, reportingCurrency: string): InvestmentPolicy {
  let additionalCashMinor: bigint | null = null;
  if (stored.additionalCashMajor !== null) {
    additionalCashMinor = additionalCashMinorFromMajor(stored.additionalCashMajor, reportingCurrency);
  }
  const instruments =
    stored.instruments.length === 0
      ? null
      : stored.instruments.map((row) => approvedInstrumentFromStored(row));
  return {
    targets: stored.targets.length > 0 ? stored.targets : null,
    additionalCashMinor,
    instruments,
    holdingClasses: stored.holdingClasses,
  };
}

export function emptyInvestmentPolicy(): InvestmentPolicy {
  return {
    targets: null,
    additionalCashMinor: null,
    instruments: null,
    holdingClasses: {},
  };
}

export type InvestmentPolicyFormDefaults = {
  global_equity: string;
  thematic_technology: string;
  investment_grade_bonds: string;
  cash_investable: string;
  additionalCashMajor: string;
  instruments: StoredInstrument[];
  holdingClasses: Readonly<Record<string, InvestableClass>>;
};

export function formDefaultsFromStored(stored: StoredInvestmentPolicy | null): InvestmentPolicyFormDefaults {
  const targets = new Map(stored?.targets.map((row) => [row.assetClass, row.targetWeightBps]) ?? []);
  const percent = (assetClass: InvestableClass) => {
    const bps = targets.get(assetClass) ?? 0;
    return (bps / 100).toFixed(2).replace(/\.?0+$/, "") || "0";
  };
  return {
    global_equity: percent("global_equity"),
    thematic_technology: percent("thematic_technology"),
    investment_grade_bonds: percent("investment_grade_bonds"),
    cash_investable: percent("cash_investable"),
    additionalCashMajor: stored?.additionalCashMajor ?? "",
    instruments: stored?.instruments ?? [],
    holdingClasses: stored?.holdingClasses ?? {},
  };
}

export function toStoredPolicy(input: {
  targets: Target[];
  additionalCashMajor: string | null;
  instruments: StoredInstrument[];
  holdingClasses: Record<string, InvestableClass>;
}): StoredInvestmentPolicy {
  return {
    version: POLICY_VERSION,
    targets: input.targets,
    additionalCashMajor: input.additionalCashMajor,
    instruments: input.instruments,
    holdingClasses: input.holdingClasses,
  };
}
