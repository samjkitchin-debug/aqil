-- RLS tests for public.user_settings (synthetic users; exercises anon/authenticated roles).
begin;

select plan(24);

-- Anonymous: no access
select tests.clear_authentication();
select throws_ok(
  $$ select * from public.user_settings $$,
  '42501',
  null,
  'anon cannot select user_settings'
);

select tests.clear_authentication();
select throws_ok(
  $$ insert into public.user_settings (user_id) values (gen_random_uuid()) $$,
  '42501',
  null,
  'anon cannot insert user_settings'
);

-- Synthetic identities
select tests.create_supabase_user('user_a', 'user_a@aqil.test');
select tests.create_supabase_user('user_b', 'user_b@aqil.test');

-- User A: own row
select tests.authenticate_as('user_a');
insert into public.user_settings (user_id, locale, timezone)
values (tests.get_supabase_uid('user_a'), 'en-GB', 'UTC');

select results_eq(
  $$ select locale from public.user_settings where user_id = tests.get_supabase_uid('user_a') $$,
  $$ values ('en-GB'::text) $$,
  'user_a can read own settings'
);

-- User B: cannot see A
select tests.authenticate_as('user_b');
select is(
  current_user,
  'authenticated',
  'cross-user assertions run as authenticated'
);
select results_eq(
  $$ select count(*)::int from public.user_settings $$,
  $$ values (0) $$,
  'user_b cannot read user_a settings'
);

select throws_ok(
  $$ insert into public.user_settings (user_id) values (tests.get_supabase_uid('user_a')) $$,
  '42501',
  null,
  'user_b cannot insert user_settings for user_a'
);

-- User B: cannot update A
select results_eq(
  $$
    with updated as (
      update public.user_settings
      set locale = 'fr-FR'
      where user_id = tests.get_supabase_uid('user_a')
      returning 1
    )
    select count(*)::int from updated
  $$,
  $$ values (0) $$,
  'user_b cannot update user_a settings'
);

-- User B: cannot delete A
select results_eq(
  $$
    with deleted as (
      delete from public.user_settings
      where user_id = tests.get_supabase_uid('user_a')
      returning 1
    )
    select count(*)::int from deleted
  $$,
  $$ values (0) $$,
  'user_b cannot delete user_a settings'
);

select throws_ok(
  $$ truncate table public.user_settings $$,
  '42501',
  null,
  'authenticated cannot truncate user_settings'
);

select throws_ok(
  $$
    create trigger user_settings_not_allowed
    before update on public.user_settings
    for each row
    execute function public.set_updated_at()
  $$,
  '42501',
  null,
  'authenticated cannot create triggers on user_settings'
);

insert into public.user_settings (user_id)
values (tests.get_supabase_uid('user_b'));

select throws_ok(
  $$
    update public.user_settings
    set user_id = tests.get_supabase_uid('user_a')
    where user_id = tests.get_supabase_uid('user_b')
  $$,
  '42501',
  null,
  'user_b cannot reassign ownership of their row'
);

-- User A: still has the original row after B attempts
select tests.authenticate_as('user_a');
select results_eq(
  $$ select locale from public.user_settings where user_id = tests.get_supabase_uid('user_a') $$,
  $$ values ('en-GB'::text) $$,
  'user_a locale unchanged after cross-user attacks'
);
select results_eq(
  $$ select count(*)::int from public.user_settings where user_id = tests.get_supabase_uid('user_a') $$,
  $$ values (1) $$,
  'user_a row remains after cross-user attacks'
);

select is(
  current_user,
  'authenticated',
  'owner update runs as authenticated'
);
update public.user_settings
set locale = 'cy-GB',
    updated_at = timestamptz '2000-01-01'
where user_id = tests.get_supabase_uid('user_a');
select results_eq(
  $$
    select locale, updated_at > timestamptz '2000-01-01'
    from public.user_settings
    where user_id = tests.get_supabase_uid('user_a')
  $$,
  $$ values ('cy-GB'::text, true) $$,
  'owner update persists and set_updated_at overwrites updated_at'
);

-- Missing auth fails closed
select tests.clear_authentication();
select is(current_user, 'anon', 'cleared auth is anon');
select throws_ok(
  $$ select * from public.user_settings $$,
  '42501',
  null,
  'cleared auth cannot select user_settings'
);

select set_config('role', 'authenticated', true);
select set_config('request.jwt.claims', '', true);
select results_eq(
  $$ select count(*)::int from public.user_settings $$,
  $$ values (0) $$,
  'authenticated with no jwt sub sees no rows'
);
select throws_ok(
  $$ insert into public.user_settings (user_id) values (gen_random_uuid()) $$,
  '42501',
  null,
  'authenticated with no jwt sub cannot insert'
);

-- set_updated_at(): least privilege (trigger still works for authenticated updates)
select ok(
  not pg_catalog.has_function_privilege(
    'anon',
    'public.set_updated_at()'::regprocedure,
    'EXECUTE'
  ),
  'anon cannot execute set_updated_at'
);
select ok(
  pg_catalog.has_function_privilege(
    'authenticated',
    'public.set_updated_at()'::regprocedure,
    'EXECUTE'
  ),
  'authenticated can execute set_updated_at'
);
select ok(
  not has_table_privilege('authenticated', 'public.user_settings', 'TRUNCATE'),
  'authenticated lacks truncate on user_settings'
);
select ok(
  not has_table_privilege('authenticated', 'public.user_settings', 'TRIGGER'),
  'authenticated lacks trigger on user_settings'
);
select ok(
  not has_table_privilege('anon', 'public.user_settings', 'SELECT'),
  'anon lacks select on user_settings'
);

select * from finish();
rollback;
