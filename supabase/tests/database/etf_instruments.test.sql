-- pgTAP: instruments revoke, ISIN uniqueness, listing uniqueness, append-only assessments.
begin;

select plan(16);

select has_schema('instruments');

select ok(
  not has_schema_privilege('anon', 'instruments', 'USAGE'),
  'anon has no usage on the instruments schema'
);

select ok(
  not has_schema_privilege('authenticated', 'instruments', 'USAGE'),
  'authenticated has no usage on the instruments schema'
);

select ok(
  not has_schema_privilege('service_role', 'instruments', 'USAGE'),
  'service_role has no usage on the instruments schema'
);

select ok(
  not has_table_privilege('service_role', 'instruments.share_classes', 'SELECT'),
  'service_role is not granted select on share classes'
);

select ok(
  has_table_privilege('research_writer', 'instruments.share_classes', 'INSERT'),
  'research_writer can insert share classes'
);

select ok(
  not exists (
    select 1
    from information_schema.columns
    where table_schema = 'instruments'
      and table_name = 'benchmark_returns'
      and column_name = 'share_class_id'
  ),
  'benchmark returns are a different series from fund returns'
);

insert into instruments.umbrellas (umbrella_id, legal_name)
values ('11111111-1111-4111-8111-111111111111', 'PgTAP umbrella');

insert into instruments.sub_funds (sub_fund_id, umbrella_id, legal_name, base_currency)
values (
  '22222222-2222-4222-8222-222222222222',
  '11111111-1111-4111-8111-111111111111',
  'PgTAP sub-fund',
  'USD'
);

insert into instruments.share_classes (
  share_class_id, sub_fund_id, isin, distribution_policy, hedge_status, inception_date
) values (
  '33333333-3333-4333-8333-333333333333',
  '22222222-2222-4222-8222-222222222222',
  'IE00B0000009',
  'accumulating',
  'unhedged',
  date '2020-06-01'
);

select throws_ok(
  $$
    insert into instruments.share_classes (
      sub_fund_id, isin, distribution_policy, hedge_status
    ) values (
      '22222222-2222-4222-8222-222222222222',
      'IE00B0000009',
      'distributing',
      'hedged'
    )
  $$,
  '23505',
  null,
  'share class ISIN is unique'
);

insert into instruments.listings (
  listing_id, share_class_id, mic, trading_currency, ticker
) values (
  '44444444-4444-4444-8444-444444444444',
  '33333333-3333-4333-8333-333333333333',
  'XLON',
  'USD',
  'TEST'
);

select throws_ok(
  $$
    insert into instruments.listings (share_class_id, mic, trading_currency, ticker)
    values (
      '33333333-3333-4333-8333-333333333333',
      'XLON',
      'USD',
      'TEST'
    )
  $$,
  '23505',
  null,
  'listing is unique by share class, MIC, trading currency, and ticker'
);

insert into instruments.assessments (
  assessment_id, share_class_id, eligibility, evidence_status, statement
) values (
  '55555555-5555-4555-8555-555555555555',
  '33333333-3333-4333-8333-333333333333',
  'UNKNOWN',
  'insufficient',
  'PgTAP assessment with missing hard evidence'
);

select throws_ok(
  $$
    update instruments.assessments
    set statement = 'rewritten'
    where assessment_id = '55555555-5555-4555-8555-555555555555'
  $$,
  'P0001',
  null,
  'assessments reject updates'
);

select throws_ok(
  $$
    delete from instruments.assessments
    where assessment_id = '55555555-5555-4555-8555-555555555555'
  $$,
  'P0001',
  null,
  'assessments reject deletes'
);

insert into instruments.identifier_history (
  identifier_history_id,
  share_class_id,
  listing_id,
  identifier_kind,
  identifier_value,
  effective_on,
  source_id,
  source_locator
) values (
  '66666666-6666-4666-8666-666666666666',
  '33333333-3333-4333-8333-333333333333',
  '44444444-4444-4444-8444-444444444444',
  'ticker',
  'TEST',
  date '2020-06-01',
  'pgtap',
  'synthetic://aqil/pgtap/identifier'
);

select throws_ok(
  $$
    update instruments.identifier_history
    set identifier_value = 'NEW'
    where identifier_history_id = '66666666-6666-4666-8666-666666666666'
  $$,
  'P0001',
  null,
  'identifier history appends and does not rewrite a ticker'
);

select throws_ok(
  $$
    insert into instruments.fund_returns (
      share_class_id, period_start, period_end, currency, return_type,
      reinvestment, value_text, source_id, source_locator
    ) values (
      '33333333-3333-4333-8333-333333333333',
      date '2019-01-01',
      date '2019-12-31',
      'USD',
      'total_return',
      'reinvested',
      '1.0',
      'pgtap',
      'synthetic://aqil/pgtap/fund-return'
    )
  $$,
  'P0001',
  null,
  'fund returns cannot start before share-class inception'
);

insert into instruments.share_classes (
  share_class_id, sub_fund_id, isin, distribution_policy, hedge_status
) values (
  '77777777-7777-4777-8777-777777777777',
  '22222222-2222-4222-8222-222222222222',
  'IE00B0000017',
  'accumulating',
  'unknown'
);

select throws_ok(
  $$
    insert into instruments.fund_returns (
      share_class_id, period_start, period_end, currency, return_type,
      reinvestment, value_text, source_id, source_locator
    ) values (
      '77777777-7777-4777-8777-777777777777',
      date '2024-01-01',
      date '2024-12-31',
      'USD',
      'total_return',
      'unknown',
      '1.0',
      'pgtap',
      'synthetic://aqil/pgtap/unknown-inception'
    )
  $$,
  'P0001',
  null,
  'fund returns cannot be stored when inception is unknown'
);

set local role anon;
select throws_ok(
  $$ select 1 from instruments.share_classes limit 1 $$,
  '42501',
  null,
  'anon cannot read share classes'
);
reset role;

set local role authenticated;
select throws_ok(
  $$ select 1 from instruments.share_classes limit 1 $$,
  '42501',
  null,
  'authenticated cannot read share classes'
);
reset role;

select * from finish();
rollback;
