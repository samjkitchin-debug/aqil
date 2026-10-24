import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

import {
  applicabilitySummary,
  assessPlaybookApplicability,
  classifyRequiredInput,
  type PolicyTargetRecord,
} from "./playbook-applicability.ts";
import {
  loadInvestmentPlaybooksFromDisk,
  type InvestmentPlaybook,
} from "./investment-playbooks.ts";

const EMPTY: PolicyTargetRecord = { targets: null };

const SAVED: PolicyTargetRecord = {
  targets: [
    { assetClass: "global_equity", targetWeightBps: 6000 },
    { assetClass: "thematic_technology", targetWeightBps: 1000 },
    { assetClass: "investment_grade_bonds", targetWeightBps: 2000 },
    { assetClass: "cash_investable", targetWeightBps: 1000 },
  ],
};

function loadRegister(): InvestmentPlaybook[] {
  return loadInvestmentPlaybooksFromDisk(
    (filePath) => readFileSync(filePath, "utf8"),
    existsSync,
  );
}

function byId(rows: ReturnType<typeof assessPlaybookApplicability>, id: string) {
  const row = rows.find((item) => item.id === id);
  assert.ok(row);
  return row;
}

function input(row: ReturnType<typeof byId>, label: string) {
  const found = row.inputs.find((item) => item.label === label);
  assert.ok(found, label);
  return found;
}

test("an empty development policy records that targets are not set and leaves the other inputs missing", () => {
  const rows = assessPlaybookApplicability(loadRegister(), EMPTY);
  assert.deepEqual(
    rows.map((row) => row.id),
    [
      "strategic_asset_allocation",
      "diversification_regions_sectors",
      "contribution_rebalancing",
      "cost_tracking_efficiency",
      "tactical_regional_sector_allocation",
    ],
  );
  for (const row of rows) {
    assert.equal(row.requiredInputsPresent, false);
    assert.match(row.summary, /Required inputs are missing/);
    assert.ok(row.constraints.some((item) => item.includes("No order is produced")));
  }

  const strategic = byId(rows, "strategic_asset_allocation");
  const targets = input(strategic, "Written target weights, or an explicit record that targets are not set");
  assert.equal(targets.presence, "present");
  assert.equal(targets.note, "Targets are not set.");
  assert.equal(
    input(strategic, "Current weights for each class named in the written policy").presence,
    "missing",
  );
  assert.equal(
    input(strategic, "Standing contribution amount, currency and frequency").presence,
    "missing",
  );
  assert.equal(
    input(strategic, "Balances the policy treats as investable, and balances it keeps outside that mix")
      .presence,
    "missing",
  );
  assert.equal(input(strategic, "None. A return forecast is not required.").presence, "not_required");
});

test("saved written targets do not fill weights, contributions, holdings, or cited charges", () => {
  const rows = assessPlaybookApplicability(loadRegister(), SAVED);
  const strategic = byId(rows, "strategic_asset_allocation");
  const targets = input(strategic, "Written target weights, or an explicit record that targets are not set");
  assert.equal(targets.presence, "present");
  assert.equal(targets.note, "Written target weights are saved.");
  assert.equal(strategic.requiredInputsPresent, false);

  const contribution = byId(rows, "contribution_rebalancing");
  assert.equal(
    input(contribution, "Current weights and the written target weights").presence,
    "missing",
  );
  assert.equal(
    input(contribution, "Standing contribution amount, currency and frequency").presence,
    "missing",
  );
  assert.equal(input(contribution, "Whether a contribution is actually due").presence, "missing");
  assert.equal(
    input(contribution, "Dealing, tax and income constraints the policy has already recorded").presence,
    "missing",
  );
  assert.equal(input(contribution, "Prices are used only to state current weights").presence, "not_required");

  const diversification = byId(rows, "diversification_regions_sectors");
  assert.equal(
    input(
      diversification,
      "Regional weights of holdings in scope, where a holdings source supports them",
    ).presence,
    "missing",
  );
  assert.equal(
    input(diversification, "Sector weights of holdings in scope, where a holdings source supports them")
      .presence,
    "missing",
  );
  assert.equal(
    input(diversification, "An explicit gap where look-through holdings are not available from a cited source")
      .presence,
    "missing",
  );
  assert.equal(
    input(diversification, "A forecast of future correlations is not an input").presence,
    "not_required",
  );

  const cost = byId(rows, "cost_tracking_efficiency");
  assert.equal(
    input(cost, "Ongoing charge for each holding in scope, from a cited document").presence,
    "missing",
  );
  assert.equal(
    input(cost, "Tracking difference only where a cited document states it").presence,
    "missing",
  );
  assert.equal(input(cost, "Any maximum ongoing charge written in the policy").presence, "missing");
  assert.equal(
    input(
      cost,
      "Domicile, currency and accumulating or distributing treatment already recorded for the holding",
    ).presence,
    "missing",
  );
  assert.equal(
    input(cost, "A benchmark total return is not invented to fill a gap").presence,
    "not_required",
  );
});

test("unusable targets stay missing and are not replaced with a default mix", () => {
  const broken: PolicyTargetRecord = {
    targets: [{ assetClass: "global_equity", targetWeightBps: 5000 }],
  };
  const rows = assessPlaybookApplicability(loadRegister(), broken);
  const targets = input(
    byId(rows, "strategic_asset_allocation"),
    "Written target weights, or an explicit record that targets are not set",
  );
  assert.equal(targets.presence, "missing");
  assert.match(targets.note ?? "", /not usable/);
  assert.match(targets.note ?? "", /not replaced with a default mix/);
  const unset = assessPlaybookApplicability(loadRegister(), { targets: [] });
  assert.equal(
    input(byId(unset, "strategic_asset_allocation"), "Written target weights, or an explicit record that targets are not set")
      .note,
    "Targets are not set.",
  );
});

test("a timing forecast stays missing and the unapproved playbook is not applied", () => {
  const rows = assessPlaybookApplicability(loadRegister(), SAVED);
  const timing = byId(rows, "tactical_regional_sector_allocation");
  assert.equal(timing.kind, "disputed_market_timing");
  assert.equal(timing.approvalStatus, "not_approved");
  assert.equal(timing.requiredInputsPresent, false);
  assert.match(timing.summary, /Not approved/);
  assert.match(timing.summary, /not applied/);
  assert.equal(
    input(timing, "The written strategic weights that a tilt would leave").presence,
    "missing",
  );
  assert.equal(
    input(
      timing,
      "A timing rule would need a point-in-time forecast of regional or sector relative returns, with a source and a vintage",
    ).presence,
    "missing",
  );
  assert.equal(
    input(timing, "That forecast is not an authorised input while this entry is not approved").presence,
    "missing",
  );
});

test("unknown required text stays missing and a complete structural entry is still not a trade", () => {
  assert.equal(classifyRequiredInput("None. A new series is required.", EMPTY).presence, "missing");
  assert.equal(classifyRequiredInput("Standing contribution amount, currency and frequency", SAVED).presence, "missing");

  const complete = skeleton({
    id: "example_complete",
    kind: "structural",
    approvalStatus: "proposed",
    requiredPortfolioData: ["Written target weights, or an explicit record that targets are not set"],
    requiredMarketOrEconomicData: ["None. A return forecast is not required."],
  });
  const [row] = assessPlaybookApplicability([complete], SAVED);
  assert.equal(row?.requiredInputsPresent, true);
  assert.equal(
    row?.summary,
    "Required inputs are present. This is not an instruction to trade.",
  );

  const refused = skeleton({
    id: "example_refused",
    kind: "disputed_market_timing",
    approvalStatus: "not_approved",
    requiredPortfolioData: ["Written target weights, or an explicit record that targets are not set"],
    requiredMarketOrEconomicData: ["None. A return forecast is not required."],
  });
  const [blocked] = assessPlaybookApplicability([refused], SAVED);
  assert.equal(blocked?.requiredInputsPresent, true);
  assert.match(blocked?.summary ?? "", /does not approve this entry/);
  assert.match(applicabilitySummary("not_approved", false), /Required inputs are missing/);
});

test("the check does not name a fund, record a score, or place an order", () => {
  const rows = assessPlaybookApplicability(loadRegister(), SAVED);
  const rendered = JSON.stringify(rows);
  assert.doesNotMatch(rendered, /VWRA|IE00BK5BQT80|score|place an order|recommend a fund/i);
  assert.equal("score" in rows[0]!, false);

  const panel = readFileSync(new URL("../../components/capital/deploy-capital-panel.tsx", import.meta.url), "utf8");
  assert.match(panel, /PlaybookApplicabilitySection targets=\{policy\.runtime\.targets\}/);
  assert.doesNotMatch(panel, /PlaybookApplicabilitySection targets=\{example/);
  assert.doesNotMatch(panel, /#[0-9a-fA-F]{3,8}\b/);
});

function skeleton(overrides: Pick<
  InvestmentPlaybook,
  "id" | "kind" | "approvalStatus" | "requiredPortfolioData" | "requiredMarketOrEconomicData"
>): InvestmentPlaybook {
  return {
    id: overrides.id,
    title: "Example",
    kind: overrides.kind,
    decisionQuestion: "Is the written policy still the anchor?",
    requiredPortfolioData: overrides.requiredPortfolioData,
    requiredMarketOrEconomicData: overrides.requiredMarketOrEconomicData,
    investorPolicyConstraints: ["No order is produced"],
    evidence: [],
    evidenceLimitations: [],
    applicableConditions: [],
    contradictoryConditions: [],
    implementationAlternatives: [],
    expectedTradeOffs: [],
    outcomeEvaluationCriteria: [],
    version: "1.0.0",
    approvalStatus: overrides.approvalStatus,
  };
}
