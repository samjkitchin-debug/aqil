-- Accepted parameter versions are not historical calculations.
-- Ordinary authenticated users receive no privileges on this table.

create table research.parameter_versions (
  parameter_version_id text primary key,
  method_id text not null,
  method_version text not null,
  checksum text not null unique,
  parameter_values jsonb not null,
  estimation_configuration jsonb not null,
  provenance_run_id text,
  publication_allowed boolean not null default false,
  operationally_accepted boolean not null default false,
  recorded_at timestamptz not null default now(),
  constraint parameter_versions_unpublished check (publication_allowed = false),
  constraint parameter_versions_not_operational check (operationally_accepted = false),
  constraint parameter_versions_no_path check (
    not (parameter_values ? 'filtered_factor')
    and not (parameter_values ? 'smoothed_factor')
  )
);

comment on table research.parameter_versions is
  'Accepted parameter artifact. A research run remains a separate calculation.';

revoke all on table research.parameter_versions from public, anon, authenticated;

grant select, insert on table research.parameter_versions to research_writer;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'research_reader') then
    execute 'grant select on table research.parameter_versions to research_reader';
  end if;
end $$;
