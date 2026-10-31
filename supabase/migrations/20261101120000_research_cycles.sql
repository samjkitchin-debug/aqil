-- One daily research cycle and its drill-down events.
-- Apply on a host only after a tested logical restore. This file does not do that.

create table research.research_cycles (
  cycle_id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null,
  finished_at timestamptz,
  status text not null,
  expected_on date not null,
  detail text not null default '',
  constraint research_cycles_status check (
    status in ('running', 'completed', 'partial', 'overlapped', 'missed')
  ),
  constraint research_cycles_time_order check (
    finished_at is null or finished_at >= started_at
  )
);

create table research.research_cycle_events (
  event_id uuid primary key default gen_random_uuid(),
  cycle_id uuid not null references research.research_cycles (cycle_id),
  phase text not null,
  subject_id text not null,
  outcome text not null,
  detail text not null default '',
  recorded_at timestamptz not null,
  constraint research_cycle_events_phase check (phase in ('source', 'method', 'schedule'))
);

comment on table research.research_cycles is
  'One daily research cycle. A missed UTC day is the last start, not a GitHub receipt.';

revoke all on table research.research_cycles from public, anon, authenticated;
revoke all on table research.research_cycle_events from public, anon, authenticated;

grant select, insert on table research.research_cycles to research_writer;
grant select, insert on table research.research_cycle_events to research_writer;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'research_reader') then
    execute 'grant select on table research.research_cycles to research_reader';
    execute 'grant select on table research.research_cycle_events to research_reader';
  end if;
end $$;
