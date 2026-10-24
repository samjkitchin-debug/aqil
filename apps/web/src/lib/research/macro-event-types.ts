export type EvidenceRole =
  | "primary"
  | "secondary"
  | "supporting"
  | "conflicting"
  | "subsequent_development";

export type DimensionStatus =
  | "available"
  | "stale"
  | "insufficient"
  | "contradictory"
  | "not_yet_monitored";

export type MeasureKind =
  | "actual_capital_expenditure"
  | "forecast_spending"
  | "actual_spending"
  | "infrastructure_demand"
  | "commercial_adoption"
  | "revenue"
  | "earnings"
  | "equity_price"
  | "none";

export type MacroEvidenceInput = {
  role: EvidenceRole;
  clusterKey: string;
  title: string;
  canonicalUrl: string;
  publishedAt: string | null;
  sourceId: string;
};

export type MacroEventInput = {
  eventId: string;
  eventKey: string;
  category: string;
  epistemicClass: "confirmed_event" | "reported_allegation" | "forecast" | "interpretation";
  claimScope: "policy_action_stated" | "publication_recorded";
  summary: string;
  eventOn: string;
  eventDatesStated: string;
  indicatorSourceIds: string[];
  channelNote: string | null;
  surfaceOnToday: boolean;
  surfaceReason: string | null;
  surfacedAt: string | null;
  recordClass: "recorded" | "synthetic_fixture";
  investmentImplication: "no_action" | "insufficient_evidence";
  evidence: MacroEvidenceInput[];
};

export type ThemeDimensionInput = {
  dimension: string;
  status: DimensionStatus;
  measureKind: MeasureKind;
  explanation: string;
  amount: string | null;
  unit: string | null;
  periodStart: string | null;
  periodEnd: string | null;
  reportingEntity: string | null;
  relationship: "supports" | "contradicts" | null;
  sourceUrl: string | null;
};

export type ThemeAssessmentInput = {
  assessmentId: string;
  recordedAt: string;
  supersedesAssessmentId: string | null;
  recordClass: "recorded" | "synthetic_fixture";
  realEconomyActivity: string;
  earnings: string;
  marketPrices: string;
  mediaAttention: string;
  dimensions: ThemeDimensionInput[];
};
