import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

import type { ResearchInsightV1 } from "@/lib/research/types";

const FIXTURE_PATH = path.join(process.cwd(), "fixtures", "research-insight.v1.json");
const LOCAL_PATH = path.join(process.cwd(), ".local", "research-insight.v1.json");

function insightCandidates(): string[] {
  const configured = process.env.RESEARCH_INSIGHT_PATH?.trim();
  if (configured) {
    const resolved = path.isAbsolute(configured)
      ? configured
      : path.join(/* turbopackIgnore: true */ process.cwd(), configured);
    return [resolved, FIXTURE_PATH];
  }
  return [LOCAL_PATH, FIXTURE_PATH];
}

function isValidInsight(data: unknown): data is ResearchInsightV1 {
  if (!data || typeof data !== "object") return false;
  const o = data as Record<string, unknown>;
  return (
    o.schema_version === "1.0" &&
    typeof o.headline === "string" &&
    typeof o.run_id === "string"
  );
}

export type FounderInsightLoadResult =
  | { status: "ok"; insight: ResearchInsightV1; source: "local" | "fixture" }
  | { status: "missing" }
  | { status: "invalid" };

export async function loadFounderResearchInsight(): Promise<FounderInsightLoadResult> {
  const candidates = insightCandidates();
  for (const filePath of candidates) {
    try {
      const raw = await readFile(filePath, "utf8");
      const parsed: unknown = JSON.parse(raw);
      if (!isValidInsight(parsed)) {
        return { status: "invalid" };
      }
      const source = filePath.includes("fixtures") ? "fixture" : "local";
      return { status: "ok", insight: parsed, source };
    } catch (err) {
      const code = (err as NodeJS.ErrnoException).code;
      if (code === "ENOENT") continue;
      throw err;
    }
  }
  return { status: "missing" };
}
