import assert from "node:assert/strict";
import test from "node:test";

import {
  SYNTHETIC_STORY_BANNER,
  depthsShareCanonicalSourceIds,
  getSyntheticResearchStory,
  lookupSources,
  sourceIdsForDepth,
} from "./story.ts";

test("synthetic story exposes three depths with the same source ids", () => {
  const story = getSyntheticResearchStory();
  assert.equal(story.fixture_kind, "synthetic_research_story");
  assert.match(story.label, /synthetic/i);
  assert.equal(story.label, SYNTHETIC_STORY_BANNER);
  assert.equal(story.status, "synthetic_demonstration");
  assert.equal(depthsShareCanonicalSourceIds(story), true);

  const quickIds = sourceIdsForDepth(story, "quick_read");
  const connectedIds = sourceIdsForDepth(story, "connected_analysis");
  const fullIds = sourceIdsForDepth(story, "research_detail");
  assert.deepEqual(connectedIds, quickIds);
  assert.deepEqual(fullIds, quickIds);
});

test("citations include source time and resolve for each depth", () => {
  const story = getSyntheticResearchStory();
  for (const depth of ["quick_read", "connected_analysis", "research_detail"] as const) {
    const citations = lookupSources(story, sourceIdsForDepth(story, depth));
    assert.equal(citations.length, story.sources.length);
    for (const row of citations) {
      assert.equal(row.evidence_kind, "synthetic_fixture");
      assert.match(row.observed_at, /^\d{4}-\d{2}-\d{2}T/);
      assert.match(row.primary_url, /^https:\/\//);
    }
  }
});

test("correction line references a superseded research version", () => {
  const story = getSyntheticResearchStory();
  assert.match(story.correction.summary, /corrected/i);
  assert.notEqual(story.correction.supersedes_research_version_id, story.research_version_id);
});

test("full depth marks insufficient evidence and does not imply live intelligence", () => {
  const story = getSyntheticResearchStory();
  assert.equal(story.research_detail.insufficient_evidence, true);
  assert.doesNotMatch(story.quick_read.summary, /live market/i);
  assert.match(story.research_detail.audit_notes, /synthetic_demonstration/i);
});
