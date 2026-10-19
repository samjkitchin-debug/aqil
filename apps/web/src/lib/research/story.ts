/** Synthetic layered research story — G1 comprehension prototype (AQ-015, AQ-016). */

export const SYNTHETIC_STORY_BANNER =
  "Synthetic demonstration — not live market intelligence";

export type ResearchStoryPublicationStatus =
  | "synthetic_demonstration"
  | "internal_preview"
  | "published";

export type ResearchSourceCitation = {
  source_id: string;
  title: string;
  primary_url: string;
  /** When the cited material was observed or released (ISO 8601). */
  observed_at: string;
  evidence_kind: "synthetic_fixture";
};

export type ResearchStoryCorrection = {
  correction_id: string;
  corrected_at: string;
  summary: string;
  supersedes_research_version_id: string;
};

export type QuickReadDepth = {
  headline: string;
  summary: string;
  material_uncertainty: string;
  source_ids: string[];
};

export type ConnectedAnalysisDepth = {
  body: string;
  causal_links: string[];
  source_ids: string[];
};

export type ResearchDetailDepth = {
  method_summary: string;
  audit_notes: string;
  source_ids: string[];
  insufficient_evidence: boolean;
};

export type SyntheticResearchStoryV1 = {
  schema_version: "1.0";
  fixture_kind: "synthetic_research_story";
  label: string;
  research_version_id: string;
  story_id: string;
  status: ResearchStoryPublicationStatus;
  updated_at: string;
  sources: ResearchSourceCitation[];
  correction: ResearchStoryCorrection;
  quick_read: QuickReadDepth;
  connected_analysis: ConnectedAnalysisDepth;
  research_detail: ResearchDetailDepth;
};

export type ResearchStoryDepthKey = "quick_read" | "connected_analysis" | "research_detail";

const DEMO_SOURCES: ResearchSourceCitation[] = [
  {
    source_id: "src:synthetic:demo-policy-release-001",
    title: "Illustrative policy release excerpt (fixture)",
    primary_url: "https://example.invalid/aqil/synthetic/demo-policy-release-001",
    observed_at: "2026-09-15T14:00:00Z",
    evidence_kind: "synthetic_fixture",
  },
  {
    source_id: "src:synthetic:demo-indicator-vintage-001",
    title: "Illustrative labour-market indicator vintage (fixture)",
    primary_url: "https://example.invalid/aqil/synthetic/demo-indicator-vintage-001",
    observed_at: "2026-09-05T12:30:00Z",
    evidence_kind: "synthetic_fixture",
  },
];

const SHARED_SOURCE_IDS = DEMO_SOURCES.map((row) => row.source_id);

/** Deterministic synthetic story for UI comprehension tests — not ingested research output. */
export function getSyntheticResearchStory(): SyntheticResearchStoryV1 {
  return {
    schema_version: "1.0",
    fixture_kind: "synthetic_research_story",
    label: SYNTHETIC_STORY_BANNER,
    research_version_id: "rv-synthetic-g0-001",
    story_id: "story-synthetic-g0-001",
    status: "synthetic_demonstration",
    updated_at: "2026-10-16T00:00:00Z",
    sources: DEMO_SOURCES,
    correction: {
      correction_id: "corr-synthetic-g0-001",
      corrected_at: "2026-10-14T09:00:00Z",
      summary:
        "An earlier draft of this demonstration used the wrong illustrative release date for the policy excerpt. The citation list and connected analysis now reference the corrected vintage.",
      supersedes_research_version_id: "rv-synthetic-g0-000",
    },
    quick_read: {
      headline: "Illustrative briefing: policy wording shifted before a labour print",
      summary:
        "This quick read walks through how a synthetic policy excerpt and a synthetic indicator vintage might be read together. No recession call, market forecast or product implication is asserted.",
      material_uncertainty:
        "Both inputs are fixtures. Real publication would require verified primary sources and an approved method card.",
      source_ids: [...SHARED_SOURCE_IDS],
    },
    connected_analysis: {
      body:
        "The connected layer links the illustrative policy wording to the illustrative unemployment-rate vintage without claiming causality is settled. It highlights where corroboration would be required before any investable narrative.",
      causal_links: [
        "Illustrative policy wording → possible labour-market interpretation (contested in this fixture)",
        "Indicator vintage timing → limits what a historical replay may claim",
      ],
      source_ids: [...SHARED_SOURCE_IDS],
    },
    research_detail: {
      method_summary:
        "Full research depth shows the method placeholder: rules-only comparator, explicit vintage handling and dependency on the same source identifiers as the shorter layers.",
      audit_notes:
        "Status is synthetic_demonstration. Evidence is insufficient for publication. Citations resolve to labelled fixture URLs only.",
      source_ids: [...SHARED_SOURCE_IDS],
      insufficient_evidence: true,
    },
  };
}

export function sourceIdsForDepth(
  story: SyntheticResearchStoryV1,
  depth: ResearchStoryDepthKey,
): string[] {
  switch (depth) {
    case "quick_read":
      return story.quick_read.source_ids;
    case "connected_analysis":
      return story.connected_analysis.source_ids;
    case "research_detail":
      return story.research_detail.source_ids;
  }
}

/** Every depth must cite only registered source_id values on the story record. */
export function depthsShareCanonicalSourceIds(story: SyntheticResearchStoryV1): boolean {
  const canonical = new Set(story.sources.map((row) => row.source_id));
  const depthKeys: ResearchStoryDepthKey[] = [
    "quick_read",
    "connected_analysis",
    "research_detail",
  ];

  for (const depth of depthKeys) {
    const ids = sourceIdsForDepth(story, depth);
    if (ids.length === 0) return false;
    if (!ids.every((id) => canonical.has(id))) return false;
  }

  const first = [...sourceIdsForDepth(story, "quick_read")].sort().join(",");
  for (const depth of depthKeys.slice(1)) {
    const next = [...sourceIdsForDepth(story, depth)].sort().join(",");
    if (next !== first) return false;
  }

  return true;
}

export function lookupSources(
  story: SyntheticResearchStoryV1,
  sourceIds: string[],
): ResearchSourceCitation[] {
  const byId = new Map(story.sources.map((row) => [row.source_id, row]));
  return sourceIds.map((id) => byId.get(id)).filter((row): row is ResearchSourceCitation => !!row);
}
