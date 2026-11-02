/**
 * Sentences for the research health page.
 * This module does not query a database and does not import a method.
 */

import {
  RESEARCH_READ_CONTRACT_VERSION,
  type OperationalStateRead,
} from "./read-contract-types.ts";

export type HealthCopy = {
  version: typeof RESEARCH_READ_CONTRACT_VERSION;
  headline: string;
  lines: readonly string[];
};

export function describeOperationalState(
  state: OperationalStateRead | null,
  todayUtc: string,
): HealthCopy {
  if (!state || !state.startedAt) {
    return {
      version: RESEARCH_READ_CONTRACT_VERSION,
      headline: "Today's cycle has not run.",
      lines: ["No cycle is stored. The last valid result is unchanged."],
    };
  }
  const startedDay = state.startedAt.slice(0, 10);
  const ranToday = startedDay === todayUtc;
  const lines = [
    ranToday
      ? `Today's cycle status is ${state.status ?? "unknown"}.`
      : `The latest cycle started on ${startedDay}, which is before today.`,
  ];
  if (state.status === "partial") {
    lines.push("This cycle is a partial success.");
  }
  lines.push(`Successful updates: ${named(state.events, "source", ["success", "inserted", "revised"])}.`);
  lines.push(`Unchanged sources: ${named(state.events, "source", ["unchanged"])}.`);
  lines.push(`Failed sources: ${named(state.events, "source", ["failed"])}.`);
  lines.push(
    `Blocked sources: ${named(state.events, "source", ["rights_blocked", "invalid", "blocked"])}.`,
  );
  lines.push(`Skipped methodologies: ${named(state.events, "method", ["skipped"])}.`);
  lines.push(`Completed methodology runs: ${named(state.events, "method", ["success"])}.`);
  lines.push(`Stale results: ${named(state.events, "source", ["stale"])}.`);
  lines.push("The latest valid result is the last completed run that this cycle did not replace.");
  return {
    version: RESEARCH_READ_CONTRACT_VERSION,
    headline: ranToday ? "Today's cycle has a record." : "Today's cycle has not run.",
    lines,
  };
}

function named(
  events: OperationalStateRead["events"],
  phase: string,
  outcomes: readonly string[],
): string {
  const subjects = events
    .filter((event) => event.phase === phase && outcomes.includes(event.outcome))
    .map((event) => event.subjectId);
  return subjects.length === 0 ? "none" : subjects.join(", ");
}
