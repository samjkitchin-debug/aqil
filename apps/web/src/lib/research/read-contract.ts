import "server-only";

import type { Client } from "pg";

import {
  RESEARCH_READ_CONTRACT_VERSION,
  type CycleEventRead,
  type MethodologyRunRead,
  type ObservationRead,
  type OperationalStateRead,
} from "@/lib/research/read-contract-types";

export { RESEARCH_READ_CONTRACT_VERSION };
export type { CycleEventRead, MethodologyRunRead, ObservationRead, OperationalStateRead };

type SqlClient = Pick<Client, "query">;

type RunMetaRow = {
  method_id: string;
  method_version: string;
  executed_at: Date | string;
  execution_status: string;
  publication_allowed: boolean;
  data_sufficiency: string;
  calculation_stored: boolean;
};

type RunCalculationRow = {
  run_id: string;
  method_id: string;
  method_version: string;
  executed_at: Date | string;
  execution_status: string;
  publication_allowed: boolean;
  data_sufficiency: string;
  analysis_mode: string;
  primary_dataset_id: string;
  missing_data_reason: string | null;
  statistical_interpretation: string;
  limitations: unknown;
  calculation: unknown;
};

type ObservationRow = {
  observation_id: string;
  dataset_id: string;
  period_start: Date | string;
  raw_value: string;
  unit: string;
  frequency: string;
};

type CycleRow = {
  started_at: Date | string | null;
  status: string | null;
};

type EventRow = {
  phase: string;
  subject_id: string;
  outcome: string;
  detail: string;
};

export async function readMethodologyRunMetadata(
  client: SqlClient,
  methodIds: readonly string[],
  includeStoredFlag: boolean,
): Promise<MethodologyRunRead[]> {
  const result = await client.query<RunMetaRow>(
    `select method_id, method_version, executed_at, execution_status,
            publication_allowed, data_sufficiency,
            ${includeStoredFlag ? "(calculation is not null)" : "false"} as calculation_stored
     from research.research_runs
     where method_id = any($1::text[])
     order by executed_at desc`,
    [methodIds],
  );
  return result.rows.map((row) => ({
    runId: "",
    methodId: row.method_id,
    methodVersion: row.method_version,
    executedAt: stamp(row.executed_at),
    executionStatus: row.execution_status,
    publicationAllowed: row.publication_allowed === true,
    dataSufficiency: row.data_sufficiency,
    analysisMode: "",
    primaryDatasetId: "",
    missingDataReason: null,
    statisticalInterpretation: "",
    limitations: [],
    calculation: null,
    calculationStored: row.calculation_stored === true,
  }));
}

export async function readMethodologyCalculations(
  client: SqlClient,
  methodIds: readonly string[],
): Promise<MethodologyRunRead[]> {
  const result = await client.query<RunCalculationRow>(
    `select run_id, method_id, method_version, executed_at, execution_status,
            publication_allowed, data_sufficiency, analysis_mode,
            primary_dataset_id, missing_data_reason, statistical_interpretation,
            limitations, calculation
     from research.research_runs
     where method_id = any($1::text[])
     order by executed_at desc`,
    [methodIds],
  );
  return result.rows.map((row) => ({
    runId: row.run_id,
    methodId: row.method_id,
    methodVersion: row.method_version,
    executedAt: stamp(row.executed_at),
    executionStatus: row.execution_status,
    publicationAllowed: row.publication_allowed === true,
    dataSufficiency: row.data_sufficiency,
    analysisMode: row.analysis_mode,
    primaryDatasetId: row.primary_dataset_id,
    missingDataReason: row.missing_data_reason,
    statisticalInterpretation: row.statistical_interpretation,
    limitations: limitationLines(row.limitations),
    calculation: isRecord(row.calculation) ? row.calculation : null,
  }));
}

export async function readObservations(
  client: SqlClient,
  datasetId: string,
): Promise<ObservationRead[]> {
  const result = await client.query<ObservationRow>(
    `select observation_id, dataset_id, period_start, raw_value, unit, frequency
     from research.economic_observations
     where dataset_id = $1
     order by period_start, observation_id`,
    [datasetId],
  );
  return result.rows.map((row) => ({
    observationId: row.observation_id,
    datasetId: row.dataset_id,
    periodStart: stamp(row.period_start).slice(0, 10),
    rawValue: row.raw_value,
    unit: row.unit,
    frequency: row.frequency,
  }));
}

export async function readOperationalState(client: SqlClient): Promise<OperationalStateRead> {
  const cycle = await client.query<CycleRow>(
    `select started_at, status
     from research.research_cycles
     where status <> 'overlapped'
     order by started_at desc
     limit 1`,
  );
  const latest = cycle.rows[0];
  if (!latest) {
    return { version: RESEARCH_READ_CONTRACT_VERSION, startedAt: null, status: null, events: [] };
  }
  const events = await client.query<EventRow>(
    `select phase, subject_id, outcome, detail
     from research.research_cycle_events
     where cycle_id = (
       select cycle_id from research.research_cycles
       where status <> 'overlapped'
       order by started_at desc
       limit 1
     )
     order by recorded_at, subject_id`,
  );
  return {
    version: RESEARCH_READ_CONTRACT_VERSION,
    startedAt: latest.started_at ? stamp(latest.started_at) : null,
    status: latest.status,
    events: events.rows.map(
      (row): CycleEventRead => ({
        phase: row.phase,
        subjectId: row.subject_id,
        outcome: row.outcome,
        detail: row.detail,
      }),
    ),
  };
}

function stamp(value: Date | string): string {
  if (value instanceof Date) return value.toISOString();
  return value;
}

function limitationLines(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
