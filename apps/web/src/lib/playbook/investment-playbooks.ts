/**
 * Investment playbook register.
 * A read-only contract for a later policy review. It does not score methods,
 * rank efficacy, or produce orders.
 */

import path from "node:path";
import { fileURLToPath } from "node:url";

export const PLAYBOOK_COLUMNS = [
  "playbook_id",
  "title",
  "kind",
  "decision_question",
  "required_portfolio_data",
  "required_market_or_economic_data",
  "investor_policy_constraints",
  "evidence",
  "evidence_limitations",
  "applicable_conditions",
  "contradictory_conditions",
  "implementation_alternatives",
  "expected_trade_offs",
  "outcome_evaluation_criteria",
  "version",
  "approval_status",
] as const;

export const PLAYBOOK_KINDS = ["structural", "disputed_market_timing"] as const;
export const PLAYBOOK_APPROVAL_STATUSES = ["proposed", "not_approved"] as const;

export const NO_ACTION_OUTCOME = "No action.";
export const CONTINUE_CONTRIBUTION_OUTCOME = "Continue the existing contribution policy.";
export const INSTITUTIONAL_USE_LIMIT = "Institutional use is not proof of outperformance.";

export const PLAYBOOK_TRADE_NOTICE =
  "These entries are research. They are not an instruction to trade.";

export const PLAYBOOK_REGISTER_NOTE =
  "They do not score methods, they do not rank efficacy, and they do not create an order. No action, and continuing the existing contribution policy, are valid outcomes. Institutional use of a method is not proof that it outperforms. A proposed entry is proposed for later review only. Structural principles are listed separately from disputed market-timing.";

const LIST_SEPARATOR = ";;";
const CITATION_SEPARATOR = "||";
const REGISTER_FILE = "08_INVESTMENT_PLAYBOOKS.csv";

export type PlaybookKind = (typeof PLAYBOOK_KINDS)[number];
export type PlaybookApprovalStatus = (typeof PLAYBOOK_APPROVAL_STATUSES)[number];

export type PlaybookCitation = {
  authors: string;
  year: number;
  title: string;
  locator: string;
};

export type InvestmentPlaybook = {
  id: string;
  title: string;
  kind: PlaybookKind;
  decisionQuestion: string;
  requiredPortfolioData: readonly string[];
  requiredMarketOrEconomicData: readonly string[];
  investorPolicyConstraints: readonly string[];
  evidence: readonly PlaybookCitation[];
  evidenceLimitations: readonly string[];
  applicableConditions: readonly string[];
  contradictoryConditions: readonly string[];
  implementationAlternatives: readonly string[];
  expectedTradeOffs: readonly string[];
  outcomeEvaluationCriteria: readonly string[];
  version: string;
  approvalStatus: PlaybookApprovalStatus;
};

export function playbookKindLabel(kind: PlaybookKind): string {
  switch (kind) {
    case "structural":
      return "Structural principle";
    case "disputed_market_timing":
      return "Disputed market-timing";
    default: {
      const unexpected: never = kind;
      throw new Error(`unexpected playbook kind: ${String(unexpected)}`);
    }
  }
}

export function playbookApprovalLabel(status: PlaybookApprovalStatus): string {
  switch (status) {
    case "proposed":
      return "Proposed for later review";
    case "not_approved":
      return "Not approved";
    default: {
      const unexpected: never = status;
      throw new Error(`unexpected playbook approval status: ${String(unexpected)}`);
    }
  }
}

export function investmentPlaybookRegisterCandidates(
  moduleUrl: string = import.meta.url,
  cwd: string = process.cwd(),
): string[] {
  return [
    fileURLToPath(new URL(`../../../../../docs/${REGISTER_FILE}`, moduleUrl)),
    path.resolve(cwd, "docs", REGISTER_FILE),
    path.resolve(cwd, "..", "..", "docs", REGISTER_FILE),
  ];
}

export function loadInvestmentPlaybooksFromDisk(
  readFile: (filePath: string) => string,
  exists: (filePath: string) => boolean,
): InvestmentPlaybook[] {
  const found = investmentPlaybookRegisterCandidates().find((candidate) => exists(candidate));
  if (!found) {
    throw new Error("investment playbook register was not found");
  }
  return parseInvestmentPlaybooks(readFile(found));
}

export function parseInvestmentPlaybooks(csv: string): InvestmentPlaybook[] {
  const rows = parseCsv(csv.replace(/^\uFEFF/, "")).filter(
    (row) => !row.every((cell) => cell.trim() === ""),
  );
  if (rows.length < 2) {
    throw new Error("investment playbook register has no entries");
  }

  const header = rows[0]?.map((cell) => cell.trim()) ?? [];
  if (
    header.length !== PLAYBOOK_COLUMNS.length ||
    header.some((name, index) => name !== PLAYBOOK_COLUMNS[index])
  ) {
    throw new Error("investment playbook register header does not match the contract");
  }

  const seen = new Set<string>();
  return rows.slice(1).map((row) => {
    if (row.length !== PLAYBOOK_COLUMNS.length) {
      throw new Error(`investment playbook row has ${row.length} columns`);
    }
    const playbook = playbookFromRow(row);
    if (seen.has(playbook.id)) {
      throw new Error(`${playbook.id}: duplicate playbook id`);
    }
    seen.add(playbook.id);
    return playbook;
  });
}

function playbookFromRow(row: string[]): InvestmentPlaybook {
  const value = (index: number) => row[index]?.trim() ?? "";
  const id = value(0);
  if (!/^[a-z0-9_]+$/.test(id)) {
    throw new Error("playbook id must use lowercase letters, digits and underscores");
  }

  const title = requiredText(id, "title", value(1));
  const kind = parseKind(id, value(2));
  const approvalStatus = parseApprovalStatus(id, value(15));
  if (kind === "disputed_market_timing" && approvalStatus !== "not_approved") {
    throw new Error(`${id}: disputed market-timing is not approved`);
  }

  const playbook: InvestmentPlaybook = {
    id,
    title,
    kind,
    decisionQuestion: requiredText(id, "decision question", value(3)),
    requiredPortfolioData: requiredList(id, "required portfolio data", value(4)),
    requiredMarketOrEconomicData: requiredList(id, "required market or economic data", value(5)),
    investorPolicyConstraints: requiredList(id, "investor-policy constraints", value(6)),
    evidence: parseCitations(id, value(7)),
    evidenceLimitations: requiredList(id, "evidence limitations", value(8)),
    applicableConditions: requiredList(id, "applicable conditions", value(9)),
    contradictoryConditions: requiredList(id, "contradictory conditions", value(10)),
    implementationAlternatives: requiredList(id, "implementation alternatives", value(11)),
    expectedTradeOffs: requiredList(id, "expected trade-offs", value(12)),
    outcomeEvaluationCriteria: requiredList(id, "outcome evaluation criteria", value(13)),
    version: parseVersion(id, value(14)),
    approvalStatus,
  };

  if (!playbook.implementationAlternatives.includes(NO_ACTION_OUTCOME)) {
    throw new Error(`${id}: no action must remain a valid outcome`);
  }
  if (!playbook.implementationAlternatives.includes(CONTINUE_CONTRIBUTION_OUTCOME)) {
    throw new Error(`${id}: continuing the existing contribution policy must remain a valid outcome`);
  }
  if (!playbook.evidenceLimitations.includes(INSTITUTIONAL_USE_LIMIT)) {
    throw new Error(`${id}: institutional use must not be recorded as outperformance`);
  }
  return playbook;
}

function parseKind(id: string, value: string): PlaybookKind {
  if (PLAYBOOK_KINDS.includes(value as PlaybookKind)) return value as PlaybookKind;
  throw new Error(`${id}: kind must be structural or disputed_market_timing`);
}

function parseApprovalStatus(id: string, value: string): PlaybookApprovalStatus {
  if (PLAYBOOK_APPROVAL_STATUSES.includes(value as PlaybookApprovalStatus)) {
    return value as PlaybookApprovalStatus;
  }
  throw new Error(`${id}: approval status must be proposed or not_approved`);
}

function parseVersion(id: string, value: string): string {
  if (!/^\d+\.\d+\.\d+$/.test(value)) {
    throw new Error(`${id}: version must be a major.minor.patch number`);
  }
  return value;
}

function requiredText(id: string, label: string, value: string): string {
  if (!value) throw new Error(`${id}: ${label} is required`);
  return value;
}

function requiredList(id: string, label: string, value: string): string[] {
  const items = splitPacked(value, LIST_SEPARATOR);
  if (items.length === 0) throw new Error(`${id}: ${label} is required`);
  return items;
}

function parseCitations(id: string, value: string): PlaybookCitation[] {
  const citations = splitPacked(value, CITATION_SEPARATOR).map((citation) =>
    parseCitation(id, citation),
  );
  if (citations.length === 0) throw new Error(`${id}: evidence is required`);
  return citations;
}

function parseCitation(id: string, value: string): PlaybookCitation {
  const parts = value.split(";").map((part) => part.trim());
  if (parts.length !== 4) {
    throw new Error(`${id}: citation must be authors; year; title; locator`);
  }
  const [authors, yearText, title, locator] = parts;
  if (!authors || !title || !locator) {
    throw new Error(`${id}: citation is incomplete`);
  }
  if (!/^\d{4}$/.test(yearText ?? "")) {
    throw new Error(`${id}: citation year is not a four-digit year`);
  }
  const year = Number(yearText);
  if (year < 1900 || year > 2100) {
    throw new Error(`${id}: citation year is outside 1900 to 2100`);
  }
  assertLocator(id, locator ?? "");
  return { authors: authors ?? "", year, title: title ?? "", locator: locator ?? "" };
}

function assertLocator(id: string, locator: string): void {
  if (locator.startsWith("https://doi.org/")) {
    if (!/^https:\/\/doi\.org\/10\.\S+$/.test(locator)) {
      throw new Error(`${id}: DOI locator is not well formed`);
    }
    return;
  }
  if (locator.includes("://")) {
    throw new Error(`${id}: only a DOI URL is accepted as a web locator`);
  }
  if (locator.length < 8) {
    throw new Error(`${id}: citation locator is missing`);
  }
}

function splitPacked(value: string, separator: string): string[] {
  const trimmed = value.trim();
  if (!trimmed) return [];
  return trimmed
    .split(separator)
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"') {
        if (text[index + 1] === '"') {
          field += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        field += char ?? "";
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (char !== "\r") {
      field += char ?? "";
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}
