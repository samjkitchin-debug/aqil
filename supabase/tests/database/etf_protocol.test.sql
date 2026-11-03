-- ETF protocol trials. Append-only, unpublished, and category C stays unpromoted.
begin;

select plan(8);

insert into research.etf_protocol_specifications (
  specification_id, version, specification, specification_hash, frozen_at, publication_allowed
) values (
  'ETF-PROT-001',
  1,
  '{"schema_version":"1.0"}'::jsonb,
  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  timestamptz '2026-11-04 00:00:00+00',
  false
);

insert into research.etf_protocol_trials (
  trial_id, specification_id, specification_version, specification_hash, dossier_id,
  symbol, feature, transform, horizon_label, outcome, statistic, eligibility,
  result_text, refusal_reason, effect_text, result_status, detail,
  publication_allowed, recorded_at
) values (
  'trial-1',
  'ETF-PROT-001',
  1,
  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  'LH-X-005',
  'VWRA',
  'trailing_return_63',
  'continuous',
  '6m',
  'advance',
  'spearman',
  'category_c_price_only',
  '0.1',
  null,
  '0.1',
  'inconclusive',
  'synthetic',
  false,
  timestamptz '2026-11-04 00:00:00+00'
);

select has_table('research', 'etf_protocol_trials', 'protocol trials exist');

select is(
  (
    select c.relkind
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'research' and c.relname = 'etf_protocol_coverage'
  ),
  'v',
  'coverage is a view'
);

select ok(
  not has_table_privilege('anon', 'research.etf_protocol_trials', 'SELECT'),
  'anon cannot select protocol trials'
);

select ok(
  has_table_privilege('research_writer', 'research.etf_protocol_trials', 'INSERT'),
  'research writer can insert a protocol trial'
);

select throws_ok(
  $$
    update research.etf_protocol_trials
    set detail = 'changed'
    where trial_id = 'trial-1'
  $$,
  'P0001',
  null,
  'protocol trials are append-only'
);

select throws_ok(
  $$
    delete from research.etf_protocol_trials where trial_id = 'trial-1'
  $$,
  'P0001',
  null,
  'protocol trials cannot be deleted'
);

select throws_ok(
  $$
    insert into research.etf_protocol_trials (
      trial_id, specification_id, specification_version, specification_hash, dossier_id,
      symbol, feature, transform, horizon_label, outcome, statistic, eligibility,
      result_text, refusal_reason, effect_text, detail, publication_allowed, recorded_at
    ) values (
      'trial-published', 'ETF-PROT-001', 1,
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      'LH-X-005', 'VWRA', 'trailing_return_63', 'continuous', '6m', 'advance',
      'spearman', 'category_c_price_only', '0.1', null, '0.1', 'synthetic', true,
      timestamptz '2026-11-04 00:00:00+00'
    )
  $$,
  '23514',
  null,
  'a protocol trial cannot be published'
);

select throws_ok(
  $$
    insert into research.etf_protocol_trials (
      trial_id, specification_id, specification_version, specification_hash, dossier_id,
      symbol, feature, transform, horizon_label, outcome, statistic, eligibility,
      result_text, refusal_reason, effect_text, result_status, detail,
      publication_allowed, recorded_at
    ) values (
      'trial-promoted', 'ETF-PROT-001', 1,
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      'LH-X-005', 'VWRA', 'trailing_return_63', 'continuous', '6m', 'advance',
      'spearman', 'category_c_price_only', '0.1', null, '0.1', 'statistically_supported',
      'synthetic', false, timestamptz '2026-11-04 00:00:00+00'
    )
  $$,
  '23514',
  null,
  'category C cannot record a promoted status'
);

select * from finish();
rollback;
