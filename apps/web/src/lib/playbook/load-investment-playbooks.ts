import "server-only";

import { existsSync, readFileSync } from "node:fs";

import {
  loadInvestmentPlaybooksFromDisk,
  type InvestmentPlaybook,
} from "./investment-playbooks";

export function loadInvestmentPlaybooks(): InvestmentPlaybook[] {
  return loadInvestmentPlaybooksFromDisk(
    (filePath) => readFileSync(filePath, "utf8"),
    existsSync,
  );
}
