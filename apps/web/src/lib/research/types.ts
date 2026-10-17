/** Research insight v1 — mirrors packages/contracts/schemas/research_insight.v1.json */

export type ResearchInsightPublicationStatus =
  | "internal_preview"
  | "not_eligible"
  | "blocked";

export type ResearchInsightProvenance =
  | "latest_revised"
  | "provider_vintage"
  | "first_seen_by_aqil";

export type ChartPoint = {
  period: string;
  value: number;
};

export type ResearchInsightV1 = {
  schema_version: "1.0";
  insight_id: string;
  run_id: string;
  generated_at: string;
  headline: string;
  what_changed: string;
  why_it_matters: string;
  historical_context: string;
  investor_implications: string;
  confidence_and_limitations: string;
  what_comes_next: string;
  method_id: string;
  method_version: string;
  dataset_id: string;
  analysis_mode: string;
  data_provenance: ResearchInsightProvenance;
  publication_status: ResearchInsightPublicationStatus;
  verification_status: string;
  calculation_summary: Record<string, unknown>;
  source_attribution: string;
  observation_ids: string[];
  analytical_payload_hash?: string;
  evidence_reasons?: string[];
  chart_points?: ChartPoint[];
};
