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
  const failures = state.events.filter((event) => event.outcome === "failed" || event.outcome === "invalid" || event.outcome === "rights_blocked");
  const lines = [
    ranToday
      ? `Today's cycle status is ${state.status ?? "unknown"}.`
      : `The latest cycle started on ${startedDay}, which is before today.`,
  ];
  if (failures.length === 0) {
    lines.push("Nothing in that cycle is marked failed.");
  } else {
    for (const failure of failures) {
      lines.push(`${failure.subjectId} ${failure.outcome.replaceAll("_", " ")}.`);
    }
  }
  lines.push("The latest valid result is the last completed run that this cycle did not replace.");
  return {
    version: RESEARCH_READ_CONTRACT_VERSION,
    headline: ranToday ? "Today's cycle has a record." : "Today's cycle has not run.",
    lines,
  };
}
