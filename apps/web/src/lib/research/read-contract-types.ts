/**
 * Research read contract, version 1.
 *
 * Observations, methodology results, and the daily cycle. No economic
 * interpretation is added here.
 */

export const RESEARCH_READ_CONTRACT_VERSION = "2" as const;

export type ResearchConsumerUse =
  | "descriptive_measurement"
  | "retrospective_diagnostic"
  | "historical_association"
  | "probability_estimate"
  | "qualified_forecast"
  | "experimental_only"
  | "blocked";

export type ObservationRead = {
  observationId: string;
  datasetId: string;
  periodStart: string;
  rawValue: string;
  unit: string;
  frequency: string;
};

export type MethodologyRunRead = {
  runId: string;
  methodId: string;
  methodVersion: string;
  executedAt: string;
  executionStatus: string;
  publicationAllowed: boolean;
  dataSufficiency: string;
  analysisMode: string;
  primaryDatasetId: string;
  missingDataReason: string | null;
  statisticalInterpretation: string;
  limitations: readonly string[];
  calculation: Record<string, unknown> | null;
  calculationStored?: boolean;
};

export type CycleEventRead = {
  phase: string;
  subjectId: string;
  outcome: string;
  detail: string;
};

export type OperationalStateRead = {
  version: typeof RESEARCH_READ_CONTRACT_VERSION;
  startedAt: string | null;
  status: string | null;
  events: readonly CycleEventRead[];
};
