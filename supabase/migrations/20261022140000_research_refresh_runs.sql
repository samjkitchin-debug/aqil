-- Local refresh history. One row per source attempt. Does not replace retrieval provenance.

create table research.refresh_runs (
  refresh_id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null,
  finished_at timestamptz not null,
  source_id text not null,
  outcome text not null,
  detail text not null default '',
  inserted_count integer not null default 0,
  unchanged_count integer not null default 0,
  constraint refresh_runs_time_order check (finished_at >= started_at),
  constraint refresh_runs_counts_nonnegative check (
    inserted_count >= 0 and unchanged_count >= 0
  )
);

comment on table research.refresh_runs is
  'Operator refresh outcomes by source. A failed source is its own row.';

revoke all on table research.refresh_runs from public, anon, authenticated;
grant select, insert on table research.refresh_runs to research_writer;
