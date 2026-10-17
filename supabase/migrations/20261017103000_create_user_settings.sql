-- G0: minimal user-owned settings table (RLS pattern reference; no financial data).

create table public.user_settings (
  user_id uuid primary key references auth.users (id) on delete cascade,
  locale text not null default 'en-GB',
  timezone text not null default 'UTC',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint user_settings_locale_length check (char_length(locale) between 2 and 16),
  constraint user_settings_timezone_length check (char_length(timezone) between 1 and 64)
);

comment on table public.user_settings is
  'Per-user non-financial preferences. Owner-only via RLS.';

create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

revoke all on function public.set_updated_at() from public;
revoke all on function public.set_updated_at() from anon;
grant execute on function public.set_updated_at() to authenticated;
grant execute on function public.set_updated_at() to service_role;

create trigger user_settings_set_updated_at
before update on public.user_settings
for each row
execute function public.set_updated_at();

alter table public.user_settings enable row level security;

create policy user_settings_select_own
on public.user_settings
for select
to authenticated
using (user_id = (select auth.uid()));

create policy user_settings_insert_own
on public.user_settings
for insert
to authenticated
with check (user_id = (select auth.uid()));

create policy user_settings_update_own
on public.user_settings
for update
to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy user_settings_delete_own
on public.user_settings
for delete
to authenticated
using (user_id = (select auth.uid()));

-- Supabase default privileges grant ALL to anon/authenticated at CREATE TABLE.
-- Revoke first so TRUNCATE and TRIGGER (which RLS does not cover) do not remain.
revoke all on table public.user_settings from public;
revoke all on table public.user_settings from anon;
revoke all on table public.user_settings from authenticated;
grant select, insert, update, delete on table public.user_settings to authenticated;
grant all on table public.user_settings to service_role;
