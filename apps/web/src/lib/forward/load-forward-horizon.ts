import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";
import { connection } from "next/server";

import { isFounderResearchAuthorised, researchFixtureFallbackAllowed } from "@/lib/research/founder-access";
import type { ForwardHorizonV1 } from "@/lib/forward/types";

const FIXTURE_PATH = path.join(process.cwd(), "fixtures", "forward-horizon.v1.json");
const LOCAL_PATH = path.join(process.cwd(), ".local", "forward-horizon.v1.json");

function candidates(): string[] {
  const configured = process.env.FORWARD_HORIZON_PATH?.trim();
  const paths: string[] = [];
  if (configured) {
    paths.push(
      path.isAbsolute(configured)
        ? configured
        : path.join(/* turbopackIgnore: true */ process.cwd(), configured),
    );
  } else {
    paths.push(LOCAL_PATH);
  }
  if (researchFixtureFallbackAllowed() && !paths.includes(FIXTURE_PATH)) {
    paths.push(FIXTURE_PATH);
  }
  return paths;
}

function isValid(data: unknown): data is ForwardHorizonV1 {
  if (!data || typeof data !== "object") return false;
  const o = data as Record<string, unknown>;
  return o.schema_version === "1.0" && Array.isArray(o.events) && Array.isArray(o.etfs);
}

export type ForwardHorizonLoadResult =
  | { status: "ok"; bundle: ForwardHorizonV1; source: "local" | "fixture" }
  | { status: "missing" }
  | { status: "invalid" }
  | { status: "unauthorized" };

export async function loadForwardHorizonBundle(): Promise<ForwardHorizonLoadResult> {
  await connection();
  if (!(await isFounderResearchAuthorised())) {
    return { status: "unauthorized" };
  }
  for (const filePath of candidates()) {
    try {
      const raw = await readFile(filePath, "utf8");
      const parsed: unknown = JSON.parse(raw);
      if (!isValid(parsed)) {
        return { status: "invalid" };
      }
      const isFixture = filePath.includes(`${path.sep}fixtures${path.sep}`);
      return { status: "ok", bundle: parsed, source: isFixture ? "fixture" : "local" };
    } catch (err) {
      const code = (err as NodeJS.ErrnoException).code;
      if (code === "ENOENT") continue;
      throw err;
    }
  }
  return { status: "missing" };
}
