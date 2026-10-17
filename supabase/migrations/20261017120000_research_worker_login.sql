-- M2: research worker principal (NOLOGIN in Git-tracked migrations).
-- Local/CI login password: scripts/provision-research-worker-local.sql (not applied on hosted push).

do $$
begin
  create role research_worker
    nologin
    nosuperuser
    nocreatedb
    nocreaterole
    inherit;
exception
  when duplicate_object then null;
end $$;

comment on role research_worker is
  'Research worker DB principal. Grant research_writer only. Enable LOGIN and set password via approved secrets on hosted deploy; use scripts/provision-research-worker-local.sql locally.';

grant research_writer to research_worker;
grant connect on database postgres to research_worker;

alter role research_worker set search_path = research, pg_temp;
