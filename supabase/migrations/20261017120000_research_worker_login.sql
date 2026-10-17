-- M2 Phase 2: LOGIN principal for the research worker (password rotated on hosted deploy).
-- Local default password is for CI/local Supabase only; never use in production without rotation.

do $$
begin
  create role research_worker
    login
    password 'research_worker'
    nosuperuser
    nocreatedb
    nocreaterole
    inherit;
exception
  when duplicate_object then null;
end $$;

comment on role research_worker is
  'Research worker DB login. Grant research_writer only. Set password via vault on hosted deploy.';

grant research_writer to research_worker;
grant connect on database postgres to research_worker;

alter role research_worker set search_path = research, pg_temp;
