-- Explicit permission to use Aqil. Google sign-in does not grant this row.

create table public.access_grants (
  user_id uuid primary key references auth.users (id) on delete cascade,
  role text not null,
  created_at timestamptz not null default now(),
  constraint access_grants_role_check check (role in ('founder'))
);

comment on table public.access_grants is
  'Operator-provisioned access. Authenticated users may read only their own row and cannot insert grants.';

alter table public.access_grants enable row level security;

create policy access_grants_select_own
on public.access_grants
for select
to authenticated
using (user_id = (select auth.uid()));

revoke all on table public.access_grants from public;
revoke all on table public.access_grants from anon;
revoke all on table public.access_grants from authenticated;
grant select on table public.access_grants to authenticated;
grant all on table public.access_grants to service_role;
