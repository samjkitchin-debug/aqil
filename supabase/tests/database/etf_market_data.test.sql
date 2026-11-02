-- pgTAP: additive market-data tables, quote units, append-only prices, and grants.
begin;

select plan(18);

select has_table('instruments', 'market_price_observations', 'market prices are a separate table');
select has_table('instruments', 'nav_observations', 'NAV observations are a separate table');
select has_table('instruments', 'approval_decisions', 'approval decisions are a separate table');
select has_table('instruments', 'eligibility_decisions', 'eligibility decisions are a separate table');

select ok(
  not has_table_privilege('service_role', 'instruments.market_price_observations', 'SELECT'),
  'service_role cannot select market prices'
);

select ok(
  has_table_privilege('etf_reader', 'instruments.market_price_observations', 'SELECT'),
  'etf_reader can select market prices'
);

select ok(
  not has_table_privilege('etf_reader', 'instruments.market_price_observations', 'INSERT'),
  'etf_reader cannot insert market prices'
);

select ok(
  has_table_privilege('research_writer', 'instruments.market_price_observations', 'INSERT'),
  'research_writer can insert market prices'
);

select ok(
  not has_table_privilege('research_writer', 'instruments.market_price_observations', 'UPDATE'),
  'research_writer cannot update market prices'
);

select ok(
  not has_table_privilege('research_writer', 'instruments.approval_decisions', 'UPDATE'),
  'research_writer cannot update approval decisions'
);

insert into instruments.umbrellas (umbrella_id, legal_name)
values ('aaaaaaa1-aaaa-4aaa-8aaa-aaaaaaaaaaa1', 'PgTAP market umbrella');

insert into instruments.sub_funds (sub_fund_id, umbrella_id, legal_name, base_currency)
values (
  'aaaaaaa2-aaaa-4aaa-8aaa-aaaaaaaaaaa2',
  'aaaaaaa1-aaaa-4aaa-8aaa-aaaaaaaaaaa1',
  'PgTAP market sub-fund',
  'USD'
);

insert into instruments.share_classes (
  share_class_id, sub_fund_id, isin, distribution_policy, hedge_status, inception_date
) values (
  'aaaaaaa3-aaaa-4aaa-8aaa-aaaaaaaaaaa3',
  'aaaaaaa2-aaaa-4aaa-8aaa-aaaaaaaaaaa2',
  'IE00B0000025',
  'accumulating',
  'unhedged',
  date '2020-06-01'
);

insert into instruments.listings (
  listing_id, share_class_id, mic, trading_currency, ticker
) values (
  'aaaaaaa4-aaaa-4aaa-8aaa-aaaaaaaaaaa4',
  'aaaaaaa3-aaaa-4aaa-8aaa-aaaaaaaaaaa3',
  'XLON',
  'GBP',
  'PENCE'
);

select lives_ok(
  $$
    insert into instruments.market_price_observations (
      market_price_observation_id, listing_id, session_date, value, currency,
      quote_unit, price_type, observation_time, retrieved_at, delay_class,
      adjustment_status, quality, source_id, source_locator, revision
    ) values (
      'aaaaaaa5-aaaa-4aaa-8aaa-aaaaaaaaaaa5',
      'aaaaaaa4-aaaa-4aaa-8aaa-aaaaaaaaaaa4',
      date '2026-10-30',
      12345,
      'GBP',
      'GBX',
      'close',
      timestamptz '2026-10-30 16:35:00+00',
      timestamptz '2026-10-30 18:00:00+00',
      'end_of_day',
      'raw',
      'accepted',
      'pgtap',
      'synthetic://aqil/pgtap/gbx-close',
      1
    )
  $$,
  'GBX is stored as GBX and is not rewritten to GBP'
);

select throws_ok(
  $$
    insert into instruments.market_price_observations (
      listing_id, session_date, value, currency, quote_unit, price_type,
      observation_time, retrieved_at, delay_class, adjustment_status, quality,
      source_id, source_locator, revision
    ) values (
      'aaaaaaa4-aaaa-4aaa-8aaa-aaaaaaaaaaa4',
      date '2026-10-30',
      -1,
      'GBP',
      'GBX',
      'close',
      timestamptz '2026-10-30 16:35:00+00',
      timestamptz '2026-10-30 18:00:00+00',
      'end_of_day',
      'raw',
      'accepted',
      'pgtap',
      'synthetic://aqil/pgtap/negative',
      2
    )
  $$,
  '23514',
  null,
  'a negative market price is rejected'
);

select throws_ok(
  $$
    insert into instruments.market_price_observations (
      listing_id, session_date, value, currency, quote_unit, price_type,
      observation_time, retrieved_at, delay_class, adjustment_status,
      adjustment_definition, quality, source_id, source_locator, revision
    ) values (
      'aaaaaaa4-aaaa-4aaa-8aaa-aaaaaaaaaaa4',
      date '2026-10-30',
      100,
      'USD',
      'USD',
      'close',
      timestamptz '2026-10-30 16:35:00+00',
      timestamptz '2026-10-30 18:00:00+00',
      'end_of_day',
      'adjusted',
      'provider total return',
      'accepted',
      'pgtap',
      'synthetic://aqil/pgtap/adjusted-close',
      3
    )
  $$,
  '23514',
  null,
  'an adjusted value cannot be stored as the raw close'
);

select lives_ok(
  $$
    insert into instruments.nav_observations (
      nav_observation_id, share_class_id, session_date, value, currency,
      quote_unit, price_type, observation_time, retrieved_at, delay_class,
      adjustment_status, quality, source_id, source_locator, revision
    ) values (
      'aaaaaaa6-aaaa-4aaa-8aaa-aaaaaaaaaaa6',
      'aaaaaaa3-aaaa-4aaa-8aaa-aaaaaaaaaaa3',
      date '2026-10-30',
      110,
      'USD',
      'USD',
      'nav',
      timestamptz '2026-10-30 21:00:00+00',
      timestamptz '2026-10-31 08:00:00+00',
      'end_of_day',
      'raw',
      'accepted',
      'pgtap',
      'synthetic://aqil/pgtap/nav',
      1
    )
  $$,
  'NAV is stored on the NAV table'
);

select throws_ok(
  $$
    update instruments.market_price_observations
    set value = 1
    where market_price_observation_id = 'aaaaaaa5-aaaa-4aaa-8aaa-aaaaaaaaaaa5'
  $$,
  'P0001',
  null,
  'market prices reject updates'
);

insert into instruments.eligibility_decisions (
  eligibility_decision_id, share_class_id, decision, conditions
) values (
  'aaaaaaa7-aaaa-4aaa-8aaa-aaaaaaaaaaa7',
  'aaaaaaa3-aaaa-4aaa-8aaa-aaaaaaaaaaa3',
  'insufficient',
  'No permitted issuer citation is stored.'
);

select throws_ok(
  $$
    update instruments.eligibility_decisions
    set decision = 'eligible'
    where eligibility_decision_id = 'aaaaaaa7-aaaa-4aaa-8aaa-aaaaaaaaaaa7'
  $$,
  'P0001',
  null,
  'eligibility decisions are append-only'
);

select throws_ok(
  $$
    insert into instruments.approval_decisions (share_class_id, decision, actor, rationale)
    values (
      'aaaaaaa3-aaaa-4aaa-8aaa-aaaaaaaaaaa3',
      'approved',
      '   ',
      'missing actor'
    )
  $$,
  '23514',
  null,
  'an approval requires an actor'
);

insert into instruments.etf_refresh_runs (
  refresh_run_id, dataset, provider, status, idempotency_key, started_at, finished_at
) values (
  'aaaaaaa8-aaaa-4aaa-8aaa-aaaaaaaaaaa8',
  'prices',
  'pgtap',
  'blocked',
  'pgtap-prices-blocked',
  timestamptz '2026-11-02 00:00:00+00',
  timestamptz '2026-11-02 00:00:01+00'
);

select throws_ok(
  $$
    delete from instruments.etf_refresh_runs
    where refresh_run_id = 'aaaaaaa8-aaaa-4aaa-8aaa-aaaaaaaaaaa8'
  $$,
  'P0001',
  null,
  'refresh runs cannot be deleted'
);

select * from finish();
rollback;
