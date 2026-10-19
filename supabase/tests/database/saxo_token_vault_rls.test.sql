-- Token ciphertext stays off the authenticated and anon roles. Synthetic users only.
begin;

select plan(8);

select tests.create_supabase_user('vault_a', 'vault_a@aqil.test');
select tests.create_supabase_user('vault_b', 'vault_b@aqil.test');

select ok(
  not has_table_privilege('anon', 'public.saxo_token_vault', 'SELECT'),
  'anon cannot select token ciphertext'
);
select ok(
  not has_table_privilege('authenticated', 'public.saxo_token_vault', 'SELECT'),
  'authenticated cannot select token ciphertext'
);
select ok(
  has_table_privilege('service_role', 'public.saxo_token_vault', 'SELECT'),
  'service role can select token ciphertext'
);
select ok(
  not has_table_privilege('authenticated', 'public.saxo_source_units', 'UPDATE'),
  'authenticated cannot update a source unit'
);
select ok(
  not has_table_privilege('authenticated', 'public.saxo_source_units', 'DELETE'),
  'authenticated cannot delete a source unit'
);

select tests.authenticate_as('vault_a');
select throws_ok(
  $$
    insert into public.saxo_token_vault (user_id, environment, ciphertext)
    values (tests.get_supabase_uid('vault_a'), 'live', 'v1.bm9uY2U.Y2lwaGVy')
  $$,
  '42501',
  null,
  'authenticated cannot insert a token row'
);

select lives_ok(
  $$
    insert into public.saxo_source_units (
      user_id, environment, kind, content_hash, ciphertext, retrieved_at
    )
    values (
      tests.get_supabase_uid('vault_a'),
      'live',
      'balances',
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      'v1.bm9uY2U.Y2lwaGVy',
      '2026-10-20T00:00:00Z'
    )
  $$,
  'owner can append an encrypted source unit'
);

select tests.authenticate_as('vault_b');
select results_eq(
  $$ select count(*)::int from public.saxo_source_units $$,
  $$ values (0) $$,
  'another user cannot read the source unit'
);

select * from finish();
rollback;
