import "server-only";

import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  emptyInvestmentPolicy,
  formDefaultsFromStored,
  parseStoredPolicy,
  policyFromStored,
  type InvestmentPolicy,
  type InvestmentPolicyFormDefaults,
  type StoredInvestmentPolicy,
} from "./policy.ts";

function webRoot(): string {
  const cwd = process.cwd();
  return cwd.replace(/\\/g, "/").endsWith("/apps/web") ? cwd : path.join(cwd, "apps", "web");
}

function policyPath(userId: string): string {
  return path.join(webRoot(), ".local", "investment-policy", `${userId}.json`);
}

export type LoadedInvestmentPolicy = {
  runtime: InvestmentPolicy;
  form: InvestmentPolicyFormDefaults;
};

async function readStoredPolicyFile(userId: string): Promise<StoredInvestmentPolicy | null> {
  try {
    const raw = JSON.parse(await readFile(policyPath(userId), "utf8")) as unknown;
    return parseStoredPolicy(raw);
  } catch {
    return null;
  }
}

export async function readInvestmentPolicy(
  userId: string,
  reportingCurrency: string,
): Promise<LoadedInvestmentPolicy> {
  const stored = await readStoredPolicyFile(userId);
  return {
    runtime: stored ? policyFromStored(stored, reportingCurrency) : emptyInvestmentPolicy(),
    form: formDefaultsFromStored(stored),
  };
}

export async function writeInvestmentPolicyFile(
  userId: string,
  stored: StoredInvestmentPolicy,
): Promise<void> {
  const file = policyPath(userId);
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, `${JSON.stringify(stored, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
}
