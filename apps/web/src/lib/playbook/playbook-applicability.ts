import { assertTargets, type Target } from "../wealth/allocation.ts";
import type { InvestmentPlaybook, PlaybookApprovalStatus } from "./investment-playbooks.ts";

/**
 * Read-only check of register inputs against the saved development policy.
 * It does not score a playbook, name a fund, or produce an order.
 * An input that the policy does not store stays missing.
 */

export const PLAYBOOK_APPLICABILITY_INTRO =
  "This check reads the saved development policy only. It does not name a fund, score a method, or send an order. Missing inputs stay missing.";

const WRITTEN_TARGETS_OR_UNSET =
  "Written target weights, or an explicit record that targets are not set";

/** Register sentences that ask for no stored series. They are not a forecast. */
const NOT_REQUIRED = new Set([
  "None. A return forecast is not required.",
  "A forecast of future correlations is not an input",
  "A benchmark total return is not invented to fill a gap",
  "Prices are used only to state current weights",
]);

export type PolicyTargetRecord = {
  /** Null, or an empty list, means the development policy has no written targets. */
  targets: readonly Target[] | null;
};

export type PlaybookInputPresence = "present" | "missing" | "not_required";

export type PlaybookInputCheck = {
  label: string;
  presence: PlaybookInputPresence;
  note: string | null;
};

export type PlaybookApplicability = {
  id: string;
  title: string;
  kind: InvestmentPlaybook["kind"];
  approvalStatus: PlaybookApprovalStatus;
  summary: string;
  inputs: PlaybookInputCheck[];
  constraints: readonly string[];
  requiredInputsPresent: boolean;
};

export function assessPlaybookApplicability(
  playbooks: readonly InvestmentPlaybook[],
  policy: PolicyTargetRecord,
): PlaybookApplicability[] {
  return playbooks.map((playbook) => assessOne(playbook, policy));
}

export function classifyRequiredInput(label: string, policy: PolicyTargetRecord): PlaybookInputCheck {
  if (label === WRITTEN_TARGETS_OR_UNSET) return targetInput(policy);
  if (NOT_REQUIRED.has(label)) return { label, presence: "not_required", note: null };
  return { label, presence: "missing", note: null };
}

export function applicabilitySummary(
  approvalStatus: PlaybookApprovalStatus,
  requiredInputsPresent: boolean,
): string {
  if (approvalStatus === "not_approved") {
    const inputs = requiredInputsPresent
      ? "The required inputs are present. That does not approve this entry."
      : "Required inputs are missing.";
    return `Not approved. This entry is not applied. ${inputs}`;
  }
  if (requiredInputsPresent) {
    return "Required inputs are present. This is not an instruction to trade.";
  }
  return "Required inputs are missing.";
}

function assessOne(playbook: InvestmentPlaybook, policy: PolicyTargetRecord): PlaybookApplicability {
  const labels = [...playbook.requiredPortfolioData, ...playbook.requiredMarketOrEconomicData];
  const inputs = labels.map((label) => classifyRequiredInput(label, policy));
  const requiredInputsPresent =
    inputs.length > 0 && inputs.every((input) => input.presence !== "missing");
  return {
    id: playbook.id,
    title: playbook.title,
    kind: playbook.kind,
    approvalStatus: playbook.approvalStatus,
    summary: applicabilitySummary(playbook.approvalStatus, requiredInputsPresent),
    inputs,
    constraints: playbook.investorPolicyConstraints,
    requiredInputsPresent,
  };
}

function targetInput(policy: PolicyTargetRecord): PlaybookInputCheck {
  const label = WRITTEN_TARGETS_OR_UNSET;
  const targets = policy.targets;
  if (!targets || targets.length === 0) {
    return { label, presence: "present", note: "Targets are not set." };
  }
  try {
    assertTargets(targets);
  } catch {
    return {
      label,
      presence: "missing",
      note: "Saved targets are not usable. They are not replaced with a default mix.",
    };
  }
  return { label, presence: "present", note: "Written target weights are saved." };
}
