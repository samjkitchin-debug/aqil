import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

import {
  CONTINUE_CONTRIBUTION_OUTCOME,
  INSTITUTIONAL_USE_LIMIT,
  NO_ACTION_OUTCOME,
  PLAYBOOK_COLUMNS,
  PLAYBOOK_REGISTER_NOTE,
  PLAYBOOK_TRADE_NOTICE,
  investmentPlaybookRegisterCandidates,
  loadInvestmentPlaybooksFromDisk,
  parseInvestmentPlaybooks,
  playbookApprovalLabel,
  playbookKindLabel,
  type InvestmentPlaybook,
} from "./investment-playbooks.ts";

const EXPECTED = [
  {
    id: "strategic_asset_allocation",
    title: "Strategic asset allocation",
    kind: "structural",
    approvalStatus: "proposed",
  },
  {
    id: "diversification_regions_sectors",
    title: "Diversification across regions and sectors",
    kind: "structural",
    approvalStatus: "proposed",
  },
  {
    id: "contribution_rebalancing",
    title: "Contribution-based rebalancing",
    kind: "structural",
    approvalStatus: "proposed",
  },
  {
    id: "cost_tracking_efficiency",
    title: "Cost and tracking efficiency",
    kind: "structural",
    approvalStatus: "proposed",
  },
  {
    id: "tactical_regional_sector_allocation",
    title: "Tactical regional or sector allocation",
    kind: "disputed_market_timing",
    approvalStatus: "not_approved",
  },
] as const;

const EXPECTED_CITATIONS: Record<string, readonly (readonly [string, number, string, string])[]> = {
  strategic_asset_allocation: [
    ["Harry Markowitz", 1952, "Portfolio Selection", "https://doi.org/10.1111/j.1540-6261.1952.tb01525.x"],
    [
      "Gary P. Brinson, L. Randolph Hood and Gilbert L. Beebower",
      1986,
      "Determinants of Portfolio Performance",
      "https://doi.org/10.2469/faj.v42.n4.39",
    ],
    [
      "Roger G. Ibbotson and Paul D. Kaplan",
      2000,
      "Does Asset Allocation Policy Explain 40, 90, or 100 Percent of Performance?",
      "https://doi.org/10.2469/faj.v56.n1.2327",
    ],
  ],
  diversification_regions_sectors: [
    ["Harry Markowitz", 1952, "Portfolio Selection", "https://doi.org/10.1111/j.1540-6261.1952.tb01525.x"],
    [
      "Bruno H. Solnik",
      1974,
      "Why Not Diversify Internationally Rather Than Domestically?",
      "https://doi.org/10.2469/faj.v30.n4.48",
    ],
    [
      "François Longin and Bruno Solnik",
      2001,
      "Extreme Correlation of International Equity Markets",
      "https://doi.org/10.1111/0022-1082.00340",
    ],
  ],
  contribution_rebalancing: [
    [
      "André F. Perold and William F. Sharpe",
      1988,
      "Dynamic Strategies for Asset Allocation",
      "https://doi.org/10.2469/faj.v44.n1.16",
    ],
    [
      "Colleen M. Jaconetti, Francis M. Kinniry Jr. and Yan Zilbering",
      2010,
      "Best practices for portfolio rebalancing",
      "Vanguard research, July 2010",
    ],
  ],
  cost_tracking_efficiency: [
    ["William F. Sharpe", 1991, "The Arithmetic of Active Management", "https://doi.org/10.2469/faj.v47.n1.7"],
    ["William F. Sharpe", 2013, "The Arithmetic of Investment Expenses", "https://doi.org/10.2469/faj.v69.n2.2"],
    [
      "Mark M. Carhart",
      1997,
      "On Persistence in Mutual Fund Performance",
      "https://doi.org/10.1111/j.1540-6261.1997.tb03808.x",
    ],
    [
      "Kenneth R. French",
      2008,
      "Presidential Address: The Cost of Active Investing",
      "https://doi.org/10.1111/j.1540-6261.2008.01368.x",
    ],
  ],
  tactical_regional_sector_allocation: [
    [
      "Robert C. Merton",
      1981,
      "On Market Timing and Investment Performance. I. An Equilibrium Theory of Value for Market Forecasts",
      "https://doi.org/10.1086/296137",
    ],
    [
      "Ivo Welch and Amit Goyal",
      2008,
      "A Comprehensive Look at The Empirical Performance of Equity Premium Prediction",
      "https://doi.org/10.1093/rfs/hhm014",
    ],
  ],
};

function loadRegister(): InvestmentPlaybook[] {
  return loadInvestmentPlaybooksFromDisk(
    (filePath) => readFileSync(filePath, "utf8"),
    existsSync,
  );
}

test("the register has five playbooks in contract order", () => {
  const playbooks = loadRegister();
  assert.deepEqual(
    playbooks.map((playbook) => ({
      id: playbook.id,
      title: playbook.title,
      kind: playbook.kind,
      approvalStatus: playbook.approvalStatus,
    })),
    EXPECTED,
  );
  assert.equal(playbooks.filter((playbook) => playbook.kind === "structural").length, 4);
  assert.equal(playbooks.filter((playbook) => playbook.kind === "disputed_market_timing").length, 1);
});

test("citations stay traceable and the register does not rank efficacy", () => {
  const playbooks = loadRegister();
  for (const playbook of playbooks) {
    assert.deepEqual(
      playbook.evidence.map((citation) => [
        citation.authors,
        citation.year,
        citation.title,
        citation.locator,
      ]),
      EXPECTED_CITATIONS[playbook.id],
    );
    assert.equal(playbook.version, "1.0.0");
    assert.ok(playbook.implementationAlternatives.includes(NO_ACTION_OUTCOME));
    assert.ok(playbook.implementationAlternatives.includes(CONTINUE_CONTRIBUTION_OUTCOME));
    assert.ok(playbook.evidenceLimitations.includes(INSTITUTIONAL_USE_LIMIT));
    assert.ok(playbook.outcomeEvaluationCriteria.some((item) => item.includes("No numerical efficacy rank")));
    assert.deepEqual(Object.keys(playbook).sort(), [
      "applicableConditions",
      "approvalStatus",
      "contradictoryConditions",
      "decisionQuestion",
      "evidence",
      "evidenceLimitations",
      "expectedTradeOffs",
      "id",
      "implementationAlternatives",
      "investorPolicyConstraints",
      "kind",
      "outcomeEvaluationCriteria",
      "requiredMarketOrEconomicData",
      "requiredPortfolioData",
      "title",
      "version",
    ]);
  }

  const allocation = playbooks.find((playbook) => playbook.id === "strategic_asset_allocation");
  assert.ok(allocation);
  assert.match(
    allocation.evidenceLimitations.join(" "),
    /often misread as proof that policy explains performance/,
  );

  for (const playbook of playbooks.filter((item) => item.kind === "structural")) {
    assert.match(playbook.requiredMarketOrEconomicData.join(" "), /A return forecast is not required/);
  }

  const timing = playbooks.find((playbook) => playbook.id === "tactical_regional_sector_allocation");
  assert.ok(timing);
  assert.equal(timing.kind, "disputed_market_timing");
  assert.notEqual(timing.kind, "structural");
  assert.match(timing.decisionQuestion, /not approved/);
  assert.match(timing.decisionQuestion, /leave the strategic mix unchanged/);
  assert.equal(playbookKindLabel(timing.kind), "Disputed market-timing");
  assert.equal(playbookApprovalLabel(timing.approvalStatus), "Not approved");
  assert.equal(playbookApprovalLabel("proposed"), "Proposed for later review");
});

test("the register file stays in UK English and does not instruct a trade", () => {
  const csv = readFileSync(investmentPlaybookRegisterCandidates().find((candidate) => existsSync(candidate))!, "utf8");
  assert.doesNotMatch(csv, /\btoward\b/);
  assert.doesNotMatch(csv, /\bmaximize/);
  assert.doesNotMatch(csv, /\bauthorized\b/);
  assert.doesNotMatch(csv, /\bbehavior\b/);
  assert.doesNotMatch(csv, /place an order/i);
  assert.match(PLAYBOOK_TRADE_NOTICE, /not an instruction to trade/);
  assert.match(PLAYBOOK_REGISTER_NOTE, /do not rank efficacy/);
  assert.match(PLAYBOOK_REGISTER_NOTE, /do not create an order/);
});

test("learn lists the register as research without a new navigation item", () => {
  const page = readFileSync(new URL("../../app/learn/page.tsx", import.meta.url), "utf8");
  const component = readFileSync(new URL("../../components/learn/investment-playbooks.tsx", import.meta.url), "utf8");
  const navigation = readFileSync(new URL("../navigation.ts", import.meta.url), "utf8");
  const loader = readFileSync(new URL("./load-investment-playbooks.ts", import.meta.url), "utf8");

  assert.match(page, /InvestmentPlaybooks/);
  assert.match(component, /PLAYBOOK_TRADE_NOTICE/);
  assert.match(component, /\/my-wealth\/deploy/);
  assert.match(component, /Missing inputs stay missing/);
  assert.match(component, /Structural principles/);
  assert.match(component, /Disputed market-timing/);
  assert.doesNotMatch(component, /#[0-9a-fA-F]{3,8}\b/);
  assert.doesNotMatch(component, /\b(rgb|rgba|hsl|hsla)\s*\(/);
  assert.doesNotMatch(navigation, /playbook/i);
  assert.match(loader, /import "server-only"/);
  assert.match(loader, /loadInvestmentPlaybooksFromDisk/);
});

test("the contract rejects approval, timing promotion, duplicates and thin citations", () => {
  const brokenApproval = registerCsv([validRow({ approval_status: "approved" })]);
  assert.throws(() => parseInvestmentPlaybooks(brokenApproval), /approval status/);

  const promotedTiming = registerCsv([
    validRow({
      playbook_id: "timing_example",
      kind: "disputed_market_timing",
      approval_status: "proposed",
    }),
  ]);
  assert.throws(() => parseInvestmentPlaybooks(promotedTiming), /not approved/);

  const vagueKind = registerCsv([validRow({ kind: "tactical" })]);
  assert.throws(() => parseInvestmentPlaybooks(vagueKind), /disputed_market_timing/);

  const missingOutcome = registerCsv([
    validRow({ implementation_alternatives: "No action." }),
  ]);
  assert.throws(() => parseInvestmentPlaybooks(missingOutcome), /contribution policy/);

  const duplicate = registerCsv([validRow(), validRow()]);
  assert.throws(() => parseInvestmentPlaybooks(duplicate), /duplicate/);

  const thinCitation = registerCsv([
    validRow({ evidence: "Harry Markowitz; Portfolio Selection; https://doi.org/10.1111/j.1540-6261.1952.tb01525.x" }),
  ]);
  assert.throws(() => parseInvestmentPlaybooks(thinCitation), /citation must be authors/);

  const webLocator = registerCsv([
    validRow({
      evidence: "Harry Markowitz; 1952; Portfolio Selection; https://example.com/not-a-doi",
    }),
  ]);
  assert.throws(() => parseInvestmentPlaybooks(webLocator), /DOI URL/);

  assert.throws(
    () => parseInvestmentPlaybooks("playbook_id,title\nexample,Example\n"),
    /header/,
  );
  assert.throws(
    () => loadInvestmentPlaybooksFromDisk(() => "", () => false),
    /was not found/,
  );
});

function validRow(overrides: Partial<Record<(typeof PLAYBOOK_COLUMNS)[number], string>> = {}): string[] {
  const base: Record<(typeof PLAYBOOK_COLUMNS)[number], string> = {
    playbook_id: "example_playbook",
    title: "Example playbook",
    kind: "structural",
    decision_question: "Does the written policy still match the horizon?",
    required_portfolio_data: "Current weights",
    required_market_or_economic_data: "None. A return forecast is not required.",
    investor_policy_constraints: "The written policy is the anchor",
    evidence:
      "Harry Markowitz; 1952; Portfolio Selection; https://doi.org/10.1111/j.1540-6261.1952.tb01525.x",
    evidence_limitations: INSTITUTIONAL_USE_LIMIT,
    applicable_conditions: "A written policy is in force.",
    contradictory_conditions: "The decision is being used to time a market.",
    implementation_alternatives: `${NO_ACTION_OUTCOME} ;; ${CONTINUE_CONTRIBUTION_OUTCOME}`,
    expected_trade_offs: "Leaving the mix unchanged avoids turnover.",
    outcome_evaluation_criteria: "No numerical efficacy rank is recorded.",
    version: "1.0.0",
    approval_status: "proposed",
  };
  return PLAYBOOK_COLUMNS.map((column) => overrides[column] ?? base[column]);
}

function registerCsv(dataRows: string[][]): string {
  const quote = (value: string) => `"${value.replaceAll('"', '""')}"`;
  return [PLAYBOOK_COLUMNS.join(","), ...dataRows.map((row) => row.map(quote).join(","))].join("\n");
}
