import { connection } from "next/server";

import { resolveAccess } from "@/lib/auth/access";
import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import { describeOperationalState } from "@/lib/research/read-contract-consumer";
import { readOperationalState } from "@/lib/research/read-contract";

export async function ResearchHealthSection() {
  await connection();
  const access = await resolveAccess();
  if (access.status !== "authenticated_authorised" || access.researchAuthorisation !== "founder") {
    return (
      <section className="research-body" aria-labelledby="research-health-heading">
        <h2 id="research-health-heading">Research health</h2>
        <p>Unpublished research is limited to an authorised account.</p>
      </section>
    );
  }
  const database = resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
  const today = new Date().toISOString().slice(0, 10);
  if (database.status === "unavailable") {
    const copy = describeOperationalState(null, today);
    return (
      <section className="research-body" aria-labelledby="research-health-heading">
        <h2 id="research-health-heading">{copy.headline}</h2>
        <p>{database.reason}</p>
      </section>
    );
  }
  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      const state = await readOperationalState(client);
      const copy = describeOperationalState(state, today);
      return (
        <section className="research-body" aria-labelledby="research-health-heading">
          <h2 id="research-health-heading">{copy.headline}</h2>
          <ul>
            {copy.lines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <p>Publication stays closed. This page does not show a secret or a forecast.</p>
        </section>
      );
    } finally {
      await client.end();
    }
  } catch {
    return (
      <section className="research-body" aria-labelledby="research-health-heading">
        <h2 id="research-health-heading">Research health could not be read.</h2>
        <p>The cycle record is unavailable. No figure is invented.</p>
      </section>
    );
  }
}
