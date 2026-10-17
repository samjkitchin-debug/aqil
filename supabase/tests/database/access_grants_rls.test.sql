-- access_grants: owner can read, nobody else can, authenticated cannot self-grant.
begin;

select plan(5);

select tests.create_supabase_user('grant_a', 'grant_a@aqil.test');
select tests.create_supabase_user('grant_b', 'grant_b@aqil.test');

insert into public.access_grants (user_id, role)
values (tests.get_supabase_uid('grant_a'), 'founder');

select tests.authenticate_as('grant_a');
select results_eq(
  $$ select role from public.access_grants $$,
  $$ values ('founder'::text) $$,
  'authorised user can read own grant'
);

select tests.authenticate_as('grant_b');
select results_eq(
  $$ select count(*)::int from public.access_grants $$,
  $$ values (0) $$,
  'another signed-in user cannot read the founder grant'
);

select throws_ok(
  $$
    insert into public.access_grants (user_id, role)
    values (tests.get_supabase_uid('grant_b'), 'founder')
  $$,
  '42501',
  null,
  'authenticated user cannot insert their own grant'
);

select tests.clear_authentication();
select throws_ok(
  $$ select * from public.access_grants $$,
  '42501',
  null,
  'anon cannot read access_grants'
);

select throws_ok(
  $$ update public.access_grants set role = 'founder' $$,
  '42501',
  null,
  'anon cannot update access_grants'
);

select * from finish();
rollback;
