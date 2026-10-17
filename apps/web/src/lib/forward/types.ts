export type ForwardHorizonV1 = {
  schema_version: "1.0";
  generated_at: string;
  data_mode: "fixture_demonstration" | "verified_source" | "mixed";
  etfs: EtfSummary[];
  events: HorizonEvent[];
  exposures: ExposureLink[];
  scenarios?: ScenarioSummary[];
  outcomes?: OutcomeSummary[];
};

export type EtfSummary = {
  etf_id: string;
  legal_name: string;
  ticker: string;
  exchange: string;
  isin?: string;
  holdings_as_of: string;
  completeness: string;
  top_holdings: { name: string; issuer_id?: string; weight_percentage: string }[];
};

export type HorizonEvent = {
  event_id: string;
  title: string;
  category: string;
  subject_label?: string;
  scheduled_date: string;
  scheduled_time?: string | null;
  timezone?: string | null;
  date_precision: "confirmed" | "estimated" | "unknown";
  materiality: "high" | "medium" | "low" | "insufficient_evidence";
  source_confidence: string;
  why_it_matters: string;
  etf_ids: string[];
  is_fixture?: boolean;
};

export type ExposureLink = {
  event_id: string;
  etf_id: string;
  issuer_id: string;
  weight_percentage: string;
  materiality: string;
  snapshot_as_of: string;
};

export type ScenarioSummary = {
  scenario_id: string;
  event_id: string;
  frozen_at: string;
  headline: string;
  upside_case?: string;
  downside_case?: string;
  evidence_gaps?: string[];
};

export type OutcomeSummary = {
  outcome_id: string;
  event_id: string;
  scenario_id: string;
  headline: string;
  expectation_met?: string;
  surprise_assessment?: string;
};
