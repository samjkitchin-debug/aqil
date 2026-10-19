-- Journal identity, idempotency, corrections and transfer balance.
-- Synthetic users only. Unapplied until supabase test db passes for this file.
begin;

select plan(28);

select tests.clear_authentication();
select throws_ok(
  $$ select * from public.wealth_journal_events $$,
  '42501',
  null,
  'anon cannot select journal events'
);

select tests.create_supabase_user('journal_a', 'journal_a@aqil.test');
select tests.create_supabase_user('journal_b', 'journal_b@aqil.test');

create temp table journal_ids (
  account_a uuid,
  account_b uuid,
  instrument_id uuid,
  account_other uuid
);
grant select, insert, update on journal_ids to authenticated;

select tests.authenticate_as('journal_a');
select is(current_user, 'authenticated', 'journal owner runs as authenticated');

insert into public.wealth_accounts (user_id, name, provider, environment, currency)
values
  (tests.get_supabase_uid('journal_a'), 'Journal primary', 'manual', 'live', 'SGD'),
  (tests.get_supabase_uid('journal_a'), 'Journal second', 'manual', 'live', 'SGD');

insert into public.wealth_instruments (user_id, name, asset_class, currency)
values (tests.get_supabase_uid('journal_a'), 'Fixture equity', 'global_equity', 'SGD');

insert into journal_ids (account_a, account_b, instrument_id)
select
  (select id from public.wealth_accounts where name = 'Journal primary'),
  (select id from public.wealth_accounts where name = 'Journal second'),
  (select id from public.wealth_instruments where name = 'Fixture equity');

insert into public.wealth_journal_events (
  id, user_id, account_id, event_type, occurred_on, instrument_id,
  quantity, cash_amount_minor, currency, source_type, idempotency_key
)
select
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1',
  tests.get_supabase_uid('journal_a'),
  account_a,
  'buy',
  '2024-01-02',
  instrument_id,
  10,
  -100000,
  'SGD',
  'manual',
  'buy-original'
from journal_ids;

select results_eq(
  $$
    select cash_amount_minor
    from public.wealth_journal_events
    where id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1'
  $$,
  $$ values (-100000::bigint) $$,
  'the booked buy keeps its event identity and minor-unit amount'
);

select throws_ok(
  $$
    insert into public.wealth_journal_events (
      user_id, account_id, event_type, occurred_on, instrument_id,
      quantity, cash_amount_minor, currency, source_type, idempotency_key
    )
    select
      tests.get_supabase_uid('journal_a'),
      account_a,
      'buy',
      '2024-01-02',
      instrument_id,
      10,
      -100000,
      'SGD',
      'manual',
      'buy-original'
    from journal_ids
  $$,
  '23505',
  null,
  'a repeated idempotency key is rejected'
);

select throws_ok(
  $$
    insert into public.wealth_journal_events (
      user_id, account_id, event_type, occurred_on, quantity, cash_amount_minor,
      currency, source_type, idempotency_key
    )
    select
      tests.get_supabase_uid('journal_a'),
      account_a,
      'buy',
      '2024-01-02',
      1,
      -100,
      'SGD',
      'manual',
      'buy-without-instrument'
    from journal_ids
  $$,
  '23514',
  null,
  'a buy without an instrument is rejected'
);

insert into public.wealth_journal_events (
  id, user_id, account_id, event_type, occurred_on, instrument_id,
  quantity, cash_amount_minor, currency, source_type, idempotency_key, correction_of
)
select
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2',
  tests.get_supabase_uid('journal_a'),
  account_a,
  'buy',
  '2024-01-03',
  instrument_id,
  10,
  -80000,
  'SGD',
  'correction',
  'buy-corrected',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1'
from journal_ids;

select results_eq(
  $$
    select cash_amount_minor
    from public.wealth_journal_events
    where id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1'
  $$,
  $$ values (-100000::bigint) $$,
  'a correction leaves the original event unchanged'
);

select throws_ok(
  $$
    insert into public.wealth_journal_events (
      id, user_id, account_id, event_type, occurred_on, instrument_id,
      quantity, cash_amount_minor, currency, source_type, idempotency_key, correction_of
    )
    select
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3',
      tests.get_supabase_uid('journal_a'),
      account_a,
      'buy',
      '2024-01-04',
      instrument_id,
      10,
      -70000,
      'SGD',
      'correction',
      'buy-corrected-again',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1'
    from journal_ids
  $$,
  '23505',
  null,
  'an event can have only one correction'
);

select throws_ok(
  $$
    insert into public.wealth_journal_events (
      id, user_id, account_id, event_type, occurred_on, currency, source_type,
      idempotency_key, correction_of
    )
    select
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa9',
      tests.get_supabase_uid('journal_a'),
      account_a,
      'correction',
      '2024-01-04',
      'SGD',
      'correction',
      'self-correction',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa9'
    from journal_ids
  $$,
  '23514',
  null,
  'an event cannot correct itself'
);

select lives_ok(
  $$
    insert into public.wealth_journal_events (
      user_id, account_id, event_type, occurred_on, instrument_id, currency,
      source_type, idempotency_key, split_numerator, split_denominator
    )
    select
      tests.get_supabase_uid('journal_a'),
      account_a,
      'split',
      '2024-01-05',
      instrument_id,
      'SGD',
      'system_corporate_action',
      'split-2-for-1',
      2,
      1
    from journal_ids
  $$,
  'a split records a ratio and no cash amount'
);

select tests.authenticate_as('journal_b');
select is(current_user, 'authenticated', 'cross-user assertions run as authenticated');
select results_eq(
  $$ select count(*)::int from public.wealth_journal_events $$,
  $$ values (0) $$,
  'user b cannot read user a journal events'
);

select throws_ok(
  $$
    insert into public.wealth_journal_events (
      user_id, account_id, event_type, occurred_on, cash_amount_minor, currency,
      source_type, idempotency_key
    )
    select
      tests.get_supabase_uid('journal_a'),
      account_a,
      'fee',
      '2024-01-06',
      -100,
      'SGD',
      'manual',
      'stolen-fee'
    from journal_ids
  $$,
  '42501',
  null,
  'user b cannot insert a journal event for user a'
);

select throws_ok(
  $$ update public.wealth_journal_events set cash_amount_minor = -1 $$,
  '42501',
  null,
  'authenticated cannot update journal events'
);

select throws_ok(
  $$ delete from public.wealth_journal_events $$,
  '42501',
  null,
  'authenticated cannot delete journal events'
);

select throws_ok(
  $$ truncate table public.wealth_journal_events $$,
  '42501',
  null,
  'authenticated cannot truncate journal events'
);

select throws_ok(
  $$
    create trigger wealth_journal_events_not_allowed
    before update on public.wealth_journal_events
    for each row
    execute function public.set_updated_at()
  $$,
  '42501',
  null,
  'authenticated cannot create triggers on journal events'
);

insert into public.wealth_accounts (user_id, name, provider, environment, currency)
values (tests.get_supabase_uid('journal_b'), 'Other journal', 'manual', 'live', 'SGD');

update journal_ids
set account_other = (
  select id from public.wealth_accounts where name = 'Other journal'
);

insert into public.wealth_journal_events (
  id, user_id, account_id, event_type, occurred_on, cash_amount_minor, currency,
  source_type, idempotency_key
)
select
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1',
  tests.get_supabase_uid('journal_b'),
  account_other,
  'fee',
  '2024-01-06',
  -100,
  'SGD',
  'manual',
  'other-fee'
from journal_ids;

select tests.authenticate_as('journal_a');
select throws_ok(
  $$
    insert into public.wealth_journal_events (
      id, user_id, account_id, event_type, occurred_on, currency, source_type,
      idempotency_key, correction_of
    )
    select
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa8',
      tests.get_supabase_uid('journal_a'),
      account_a,
      'correction',
      '2024-01-07',
      'SGD',
      'correction',
      'cross-owner-correction',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1'
    from journal_ids
  $$,
  '23514',
  null,
  'a correction cannot reference another owner'
);

select lives_ok(
  $$
    insert into public.wealth_journal_events (
      id, user_id, account_id, event_type, occurred_on, cash_amount_minor,
      currency, source_type, idempotency_key, transfer_group_id
    )
    select
      legs.id,
      tests.get_supabase_uid('journal_a'),
      legs.account_id,
      'transfer',
      '2024-02-01',
      legs.cash_amount_minor,
      'SGD',
      'manual',
      legs.idempotency_key,
      'cccccccc-cccc-4ccc-8ccc-ccccccccccc1'
    from (
      values
        (
          'cccccccc-cccc-4ccc-8ccc-cccccccccc01'::uuid,
          (select account_a from journal_ids),
          -10000::bigint,
          'transfer-out'
        ),
        (
          'cccccccc-cccc-4ccc-8ccc-cccccccccc02'::uuid,
          (select account_b from journal_ids),
          10000::bigint,
          'transfer-in'
        )
    ) as legs(id, account_id, cash_amount_minor, idempotency_key)
  $$,
  'a balanced cash transfer is accepted'
);

select lives_ok(
  $$
    insert into public.wealth_journal_events (
      id, user_id, account_id, event_type, occurred_on, instrument_id, quantity,
      currency, source_type, idempotency_key, transfer_group_id
    )
    select
      legs.id,
      tests.get_supabase_uid('journal_a'),
      legs.account_id,
      'transfer',
      '2024-02-02',
      (select instrument_id from journal_ids),
      legs.quantity,
      'SGD',
      'manual',
      legs.idempotency_key,
      'cccccccc-cccc-4ccc-8ccc-ccccccccccc2'
    from (
      values
        (
          'cccccccc-cccc-4ccc-8ccc-cccccccccc03'::uuid,
          (select account_a from journal_ids),
          -4::numeric,
          'security-out'
        ),
        (
          'cccccccc-cccc-4ccc-8ccc-cccccccccc04'::uuid,
          (select account_b from journal_ids),
          4::numeric,
          'security-in'
        )
    ) as legs(id, account_id, quantity, idempotency_key)
  $$,
  'a balanced security transfer is accepted'
);

select lives_ok(
  $$ set constraints wealth_journal_transfer_zero_sum immediate $$,
  'balanced transfer groups satisfy zero-sum'
);

select throws_ok(
  $$
    insert into public.wealth_journal_events (
      user_id, account_id, event_type, occurred_on, cash_amount_minor, currency,
      source_type, idempotency_key, transfer_group_id
    )
    select
      tests.get_supabase_uid('journal_a'),
      account_a,
      'transfer',
      '2024-02-03',
      -1000,
      'SGD',
      'manual',
      'orphan-transfer',
      'dddddddd-dddd-4ddd-8ddd-ddddddddddd1'
    from journal_ids
  $$,
  '23514',
  null,
  'a one-sided transfer is rejected'
);

select ok(
  not has_table_privilege('authenticated', 'public.wealth_journal_events', 'TRUNCATE'),
  'authenticated lacks truncate on journal events'
);
select ok(
  not has_table_privilege('authenticated', 'public.wealth_journal_events', 'TRIGGER'),
  'authenticated lacks trigger on journal events'
);
select ok(
  not has_table_privilege('anon', 'public.wealth_journal_events', 'SELECT'),
  'anon lacks select on journal events'
);
select ok(
  not has_table_privilege('authenticated', 'public.wealth_journal_events', 'UPDATE'),
  'authenticated lacks update on journal events'
);
select ok(
  not has_table_privilege('authenticated', 'public.wealth_journal_events', 'DELETE'),
  'authenticated lacks delete on journal events'
);

select tests.clear_authentication();
select is(current_user, 'anon', 'cleared auth is anon');
select throws_ok(
  $$ select * from public.wealth_journal_events $$,
  '42501',
  null,
  'cleared auth cannot select journal events'
);

select * from finish();
rollback;
