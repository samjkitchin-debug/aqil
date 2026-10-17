import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  allocateContributionToTargets,
  applyResearchInsightToTargets,
  computePortfolioAnalytics,
} from "./analytics.ts";
import { allocateByWeightsBps, minorFromDecimal, sumMinor } from "./minor-units.ts";
import { syntheticTechConcentrationFixture } from "./fixture-synthetic-tech-concentration.ts";

describe("minor units", () => {
  it("reconciles allocation to exact total", () => {
    const map = allocateByWeightsBps(minorFromDecimal("100.00"), [
      { key: "a", bps: 3333 },
      { key: "b", bps: 3333 },
      { key: "c", bps: 3334 },
    ]);
    assert.equal(sumMinor([...map.values()]), minorFromDecimal("100.00"));
  });
});

describe("portfolio analytics", () => {
  it("excludes emergency reserve from investable total", () => {
    const fixture = syntheticTechConcentrationFixture();
    const analytics = computePortfolioAnalytics(
      fixture.positions,
      fixture.targets,
      fixture.profile.emergencyReserveMinor,
    );
    assert.equal(analytics.investableTotalMinor, 900_000_00n);
    assert.equal(analytics.emergencyReserveMinor, 150_000n);
  });

  it("reports technology concentration", () => {
    const fixture = syntheticTechConcentrationFixture();
    const analytics = computePortfolioAnalytics(
      fixture.positions,
      fixture.targets,
      fixture.profile.emergencyReserveMinor,
    );
    assert.ok(analytics.largestFund);
    assert.equal(analytics.largestFund.name, fixture.positions[0].name);
    const thematic = analytics.thematicExposure.find((t) => t.label === "Semiconductors");
    assert.ok(thematic);
    assert.ok(thematic.bps > 3000);
  });
});

describe("contribution engine", () => {
  it("allocates contribution with cent-level reconciliation", () => {
    const fixture = syntheticTechConcentrationFixture();
    const analytics = computePortfolioAnalytics(
      fixture.positions,
      fixture.targets,
      fixture.profile.emergencyReserveMinor,
    );
    const result = allocateContributionToTargets(minorFromDecimal("5000.00"), analytics);
    assert.equal(result.totalMinor, minorFromDecimal("5000.00"));
    assert.equal(sumMinor([...result.perClassMinor.values()]), result.totalMinor);
  });
});

describe("research isolation — semiconductor scenario", () => {
  it("does not increase technology target after positive semiconductor research", () => {
    const fixture = syntheticTechConcentrationFixture();
    const before = fixture.targets;
    const after = applyResearchInsightToTargets(before, {
      thematic: "Semiconductors",
      sentiment: "positive_cycle",
    });
    assert.deepEqual(after, before);
    const techTarget = after.find((t) => t.assetClass === "thematic_technology");
    assert.equal(techTarget?.targetWeightBps, 0);
  });
});
