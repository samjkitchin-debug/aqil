/**
 * Completeness rules read from the research method-card registry:
 * workers/research/src/aqil_research/methods/card_registry.py
 * (`validate_method_card_for_registry`) and the MethodCard fields in
 * workers/research/src/aqil_research/contracts/method_card.py.
 * This module does not register a card in that Python registry.
 */

export const EVIDENCE_STAGES = [
  "documented",
  "implemented",
  "replicated",
  "historically_evaluated",
  "prospectively_testing",
  "prospectively_supported",
  "degraded",
  "retired",
] as const;

export const LICENCE_STATUSES = [
  "unknown",
  "permitted_private",
  "permitted_public",
  "restricted",
] as const;

export type EvidenceStage = (typeof EVIDENCE_STAGES)[number];
export type LicenceStatus = (typeof LICENCE_STATUSES)[number];

export type MethodCard = {
  schema_version: "1.0";
  method_id: string;
  method_version: string;
  name: string;
  research_question: string;
  primary_reference: string;
  original_universe: string;
  original_horizon: string | null;
  formula_specification: string | null;
  data_requirements: string[];
  assumptions: string[];
  limitations: string[];
  evidence_stage: EvidenceStage;
  implementation_hash: string | null;
  licence_status: LicenceStatus;
  reviewer_id: string | null;
};

export class MethodCardContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MethodCardContractError";
  }
}

function nonEmpty(text: string | null | undefined): boolean {
  return Boolean(text && text.trim());
}

/** Same rejection labels as the research registry: origin, universe, equation, limitations, rights. */
export function validateMethodCardForRegistry(card: MethodCard): void {
  if (card.schema_version !== "1.0") {
    throw new MethodCardContractError(`method card ${card.method_id} rejected; schema_version must be 1.0`);
  }
  if (!nonEmpty(card.method_id) || !nonEmpty(card.method_version) || !nonEmpty(card.name)) {
    throw new MethodCardContractError(`method card ${card.method_id} rejected; identity is empty`);
  }
  if (!nonEmpty(card.research_question)) {
    throw new MethodCardContractError(`method card ${card.method_id} rejected; research question is empty`);
  }
  if (!(EVIDENCE_STAGES as readonly string[]).includes(card.evidence_stage)) {
    throw new MethodCardContractError(`method card ${card.method_id} rejected; invalid evidence_stage`);
  }
  if (!(LICENCE_STATUSES as readonly string[]).includes(card.licence_status)) {
    throw new MethodCardContractError(`method card ${card.method_id} rejected; invalid licence_status`);
  }

  const missing: string[] = [];
  if (!nonEmpty(card.primary_reference)) missing.push("origin");
  if (!nonEmpty(card.original_universe)) missing.push("universe");
  if (!nonEmpty(card.formula_specification)) missing.push("equation");
  if (!card.limitations.length || !card.limitations.every((item) => nonEmpty(item))) {
    missing.push("limitations");
  }
  if (card.licence_status === "unknown") missing.push("rights");
  if (missing.length > 0) {
    throw new MethodCardContractError(
      `method card ${card.method_id} rejected; missing or empty: ${missing.join(", ")}`,
    );
  }
}
