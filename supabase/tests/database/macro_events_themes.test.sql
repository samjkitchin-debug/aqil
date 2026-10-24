-- pgTAP: macro events and theme assessments are append-only.
-- A confirmed event needs primary evidence in the same transaction.
-- The web loader predicate is record_class = 'recorded'.
begin;

select plan(32);

insert into research.source_retrievals (
  retrieval_id,
  source_id,
  dataset_id,
  rights_record_id,
  provider_id,
  adapter_id,
  adapter_version,
  retrieved_at,
  collection_mode,
  endpoint_host
)
values
  (
    '11111111-1111-4111-8111-111111111111',
    'govinfo_federal_register',
    'govinfo.federal_register.notices',
    'govinfo_federal_register',
    'govinfo',
    'manual_macro',
    '1.0.0',
    timestamptz '2026-10-24 12:00:00+00',
    'fixture',
    'example.test'
  ),
  (
    '22222222-2222-4222-8222-222222222222',
    'federal_reserve_monetary_press',
    'fed.press.monetary',
    'federal_reserve_monetary_press',
    'federal_reserve',
    'manual_macro',
    '1.0.0',
    timestamptz '2026-10-24 12:00:00+00',
    'fixture',
    'example.test'
  );

insert into research.sourced_updates (
  update_id, source_id, title, canonical_url, published_at, retrieved_at,
  retrieval_id, content_hash
)
values
  (
    '33333333-3333-4333-8333-333333333333',
    'govinfo_federal_register',
    'Continuation of section 301 actions',
    'https://example.test/fr/2026-20510',
    timestamptz '2026-10-07 00:00:00+00',
    timestamptz '2026-10-24 12:00:00+00',
    '11111111-1111-4111-8111-111111111111',
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
  ),
  (
    '88888888-8888-4888-8888-888888888888',
    'govinfo_federal_register',
    'Reprint of the same notice',
    'https://example.test/fr/2026-20510-reprint',
    timestamptz '2026-10-07 00:00:00+00',
    timestamptz '2026-10-24 12:00:00+00',
    '11111111-1111-4111-8111-111111111111',
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'
  ),
  (
    '44444444-4444-4444-8444-444444444444',
    'federal_reserve_monetary_press',
    'Federal Reserve issues FOMC statement',
    'https://example.test/fed/fomc',
    timestamptz '2026-10-01 18:00:00+00',
    timestamptz '2026-10-24 12:00:00+00',
    '22222222-2222-4222-8222-222222222222',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
  );

select throws_ok(
  $$
    do $body$
    begin
      set constraints all deferred;
      insert into research.macro_events (
        event_id, event_key, category, epistemic_class, claim_scope, summary,
        event_on, event_dates_stated, record_class, investment_implication
      ) values (
        '99999999-9999-4999-8999-999999999999',
        'unconfirmed_fixture',
        'trade_policy',
        'confirmed_event',
        'policy_action_stated',
        'A confirmed event with no primary evidence.',
        date '2026-08-23',
        '23 August 2026',
        'synthetic_fixture',
        'insufficient_evidence'
      );
      set constraints all immediate;
    end
    $body$;
  $$,
  '23514',
  null,
  'confirmed event without primary evidence is refused'
);

select lives_ok(
  $$
    do $body$
    begin
      set constraints all deferred;
      insert into research.macro_events (
        event_id, event_key, category, epistemic_class, claim_scope, summary,
        country, event_on, event_dates_stated, indicator_source_ids, channel_note,
        surface_on_today, surface_reason, surfaced_at, record_class, investment_implication
      ) values (
        '55555555-5555-4555-8555-555555555555',
        'ustr_continuation_fixture',
        'trade_policy',
        'confirmed_event',
        'policy_action_stated',
        'USTR states that the actions remain in effect.',
        'United States',
        date '2026-08-23',
        '6 July 2026 and 23 August 2026',
        array['bls_cpi_u_all_items', 'federal_reserve_g17_total_ip'],
        'CPI-U and industrial production are plausible channels, not a measured effect.',
        true,
        'USTR states that the actions did not terminate and remain in effect.',
        timestamptz '2026-10-24 12:00:00+00',
        'synthetic_fixture',
        'no_action'
      );
      insert into research.macro_event_evidence (
        event_id, update_id, role, cluster_key
      ) values (
        '55555555-5555-4555-8555-555555555555',
        '33333333-3333-4333-8333-333333333333',
        'primary',
        'fr-2026-20510'
      );
      set constraints all immediate;
    end
    $body$;
  $$,
  'confirmed event with primary evidence commits'
);

select results_eq(
  $$
    select e.event_on::text <> u.published_at::date::text
    from research.macro_events e
    join research.macro_event_evidence ev on ev.event_id = e.event_id
    join research.sourced_updates u on u.update_id = ev.update_id
    where e.event_id = '55555555-5555-4555-8555-555555555555'
  $$,
  $$ values (true) $$,
  'event date is stored apart from the source publication date'
);

select throws_ok(
  $$
    insert into research.macro_event_evidence (
      event_id, update_id, role, cluster_key
    ) values (
      '55555555-5555-4555-8555-555555555555',
      '33333333-3333-4333-8333-333333333333',
      'secondary',
      'fr-2026-20510-other'
    )
  $$,
  '23505',
  null,
  'the same update cannot be linked twice'
);

select throws_ok(
  $$
    insert into research.macro_event_evidence (
      event_id, update_id, role, cluster_key
    ) values (
      '55555555-5555-4555-8555-555555555555',
      '88888888-8888-4888-8888-888888888888',
      'primary',
      'fr-2026-20510'
    )
  $$,
  '23505',
  null,
  'one origin and role is one evidence row'
);

select lives_ok(
  $$
    insert into research.macro_event_evidence (
      event_id, update_id, role, cluster_key
    ) values (
      '55555555-5555-4555-8555-555555555555',
      '88888888-8888-4888-8888-888888888888',
      'primary',
      'fr-2026-20510-independent'
    )
  $$,
  'a second origin can be primary evidence'
);

select results_eq(
  $$
    select count(distinct cluster_key)::int
    from research.macro_event_evidence
    where event_id = '55555555-5555-4555-8555-555555555555'
      and role = 'primary'
  $$,
  $$ values (2) $$,
  'independent confirmation is a distinct cluster count, not a stored score'
);

select throws_ok(
  $$
    do $body$
    begin
      set constraints all deferred;
      insert into research.macro_events (
        event_id, event_key, category, epistemic_class, claim_scope, summary,
        event_on, event_dates_stated, record_class, investment_implication
      ) values (
        'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01',
        'press_is_not_a_policy_action',
        'monetary_publication',
        'confirmed_event',
        'policy_action_stated',
        'This must not treat a press release as a policy action.',
        date '2026-10-01',
        '1 October 2026',
        'synthetic_fixture',
        'insufficient_evidence'
      );
      insert into research.macro_event_evidence (
        event_id, update_id, role, cluster_key
      ) values (
        'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01',
        '44444444-4444-4444-8444-444444444444',
        'primary',
        'fed-press-only'
      );
      set constraints all immediate;
    end
    $body$;
  $$,
  '23514',
  null,
  'policy action stated is refused when the only primary source is central-bank press'
);

select lives_ok(
  $$
    do $body$
    begin
      set constraints all deferred;
      insert into research.macro_events (
        event_id, event_key, category, epistemic_class, claim_scope, summary,
        event_on, event_dates_stated, record_class, investment_implication
      ) values (
        'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa02',
        'fed_publication_recorded',
        'monetary_publication',
        'confirmed_event',
        'publication_recorded',
        'The Federal Reserve Board published this document.',
        date '2026-10-01',
        '1 October 2026',
        'recorded',
        'no_action'
      );
      insert into research.macro_event_evidence (
        event_id, update_id, role, cluster_key
      ) values (
        'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa02',
        '44444444-4444-4444-8444-444444444444',
        'primary',
        'fed-publication'
      );
      set constraints all immediate;
    end
    $body$;
  $$,
  'a central-bank row may record that the document was published'
);

select throws_ok(
  $$
    insert into research.macro_events (
      event_key, category, epistemic_class, claim_scope, summary,
      event_on, event_dates_stated, record_class, investment_implication,
      publication_allowed
    ) values (
      'publication_not_allowed',
      'trade_policy',
      'interpretation',
      'publication_recorded',
      'Publication stays closed.',
      date '2026-08-23',
      '23 August 2026',
      'synthetic_fixture',
      'no_action',
      true
    )
  $$,
  '23514',
  null,
  'publication_allowed cannot be true'
);

select throws_ok(
  $$
    insert into research.macro_events (
      event_key, category, epistemic_class, claim_scope, summary,
      event_on, event_dates_stated, record_class, investment_implication
    ) values (
      'not_a_recommendation',
      'trade_policy',
      'interpretation',
      'publication_recorded',
      'No investment instruction is stored.',
      date '2026-08-23',
      '23 August 2026',
      'synthetic_fixture',
      'buy'
    )
  $$,
  '23514',
  null,
  'investment implication is only no_action or insufficient_evidence'
);

select throws_ok(
  $$
    insert into research.macro_events (
      event_key, category, epistemic_class, claim_scope, summary,
      event_on, event_dates_stated, indicator_source_ids, record_class,
      investment_implication
    ) values (
      'unknown_channel',
      'trade_policy',
      'interpretation',
      'publication_recorded',
      'An unknown indicator is not a channel.',
      date '2026-08-23',
      '23 August 2026',
      array['not_a_macro_series'],
      'synthetic_fixture',
      'insufficient_evidence'
    )
  $$,
  '23514',
  null,
  'indicator ids must be one of the ten macro series'
);

select throws_ok(
  $$
    insert into research.macro_events (
      event_key, category, epistemic_class, claim_scope, summary,
      event_on, event_dates_stated, indicator_source_ids, record_class,
      investment_implication
    ) values (
      'channel_without_note',
      'trade_policy',
      'interpretation',
      'publication_recorded',
      'A channel needs a note.',
      date '2026-08-23',
      '23 August 2026',
      array['bls_cpi_u_all_items'],
      'synthetic_fixture',
      'insufficient_evidence'
    )
  $$,
  '23514',
  null,
  'a channel note is required when indicator ids are present'
);

select throws_ok(
  $$
    insert into research.macro_events (
      event_key, category, epistemic_class, claim_scope, summary,
      event_on, event_dates_stated, surface_reason, record_class,
      investment_implication
    ) values (
      'reason_without_time',
      'trade_policy',
      'interpretation',
      'publication_recorded',
      'A surface reason needs a time.',
      date '2026-08-23',
      '23 August 2026',
      'This reason is long enough to be meaningful but has no time.',
      'synthetic_fixture',
      'insufficient_evidence'
    )
  $$,
  '23514',
  null,
  'surface reason and surfaced time are required together'
);

select throws_ok(
  $$
    insert into research.macro_events (
      event_key, category, epistemic_class, claim_scope, summary,
      event_on, event_dates_stated, record_class, investment_implication
    ) values (
      'summary_too_long',
      'trade_policy',
      'interpretation',
      'publication_recorded',
      repeat('n', 501),
      date '2026-08-23',
      '23 August 2026',
      'synthetic_fixture',
      'insufficient_evidence'
    )
  $$,
  '23514',
  null,
  'summary is capped and is not a document body'
);

select throws_ok(
  $$
    update research.macro_events
    set summary = 'rewritten'
    where event_id = '55555555-5555-4555-8555-555555555555'
  $$,
  'P0001',
  null,
  'macro events cannot be updated'
);

select throws_ok(
  $$
    delete from research.macro_events
    where event_id = '55555555-5555-4555-8555-555555555555'
  $$,
  'P0001',
  null,
  'macro events cannot be deleted'
);

select lives_ok(
  $$
    insert into research.macro_events (
      event_id, event_key, category, epistemic_class, claim_scope, summary,
      event_on, event_dates_stated, record_class, investment_implication
    ) values (
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1',
      'synthetic_only_event',
      'trade_policy',
      'interpretation',
      'publication_recorded',
      'Synthetic fixture that the web loader must not select.',
      date '2026-08-23',
      '23 August 2026',
      'synthetic_fixture',
      'insufficient_evidence'
    )
  $$,
  'synthetic event inserts'
);

select results_eq(
  $$
    select event_key
    from research.macro_events
    where record_class = 'recorded'
    order by event_key
  $$,
  $$ values ('fed_publication_recorded'::text) $$,
  'web loader predicate record_class = recorded hides synthetic fixtures'
);

select lives_ok(
  $$
    insert into research.theme_assessments (
      assessment_id, theme_key, real_economy_activity, earnings, market_prices,
      media_attention, record_class
    ) values (
      '66666666-6666-4666-8666-666666666666',
      'ai_infrastructure_investment',
      'Prior synthetic assessment of company-wide capital expenditure.',
      'Earnings are not established by this prior row.',
      'Market prices are not established by this prior row.',
      'Media attention is not established by this prior row.',
      'synthetic_fixture'
    )
  $$,
  'first theme assessment inserts'
);

select lives_ok(
  $$
    insert into research.theme_assessments (
      assessment_id, theme_key, supersedes_assessment_id, real_economy_activity,
      earnings, market_prices, media_attention, record_class
    ) values (
      '77777777-7777-4777-8777-777777777777',
      'ai_infrastructure_investment',
      '66666666-6666-4666-8666-666666666666',
      'Later synthetic assessment. The prior row stays.',
      'Earnings are still not established.',
      'Market prices are still not established.',
      'Media attention is still not established.',
      'synthetic_fixture'
    )
  $$,
  'superseding assessment inserts without rewriting the prior row'
);

select results_eq(
  $$
    select count(*)::int
    from research.theme_assessments
    where assessment_id in (
      '66666666-6666-4666-8666-666666666666',
      '77777777-7777-4777-8777-777777777777'
    )
  $$,
  $$ values (2) $$,
  'supersession keeps the prior assessment'
);

select throws_ok(
  $$
    insert into research.theme_dimension_evidence (
      assessment_id, dimension, status, measure_kind, explanation, relationship
    ) values (
      '66666666-6666-4666-8666-666666666666',
      'infrastructure_investment',
      'insufficient',
      'equity_price',
      'An equity price is not infrastructure investment evidence.',
      'supports'
    )
  $$,
  '23514',
  null,
  'equity price is rejected as infrastructure investment evidence'
);

select throws_ok(
  $$
    insert into research.theme_dimension_evidence (
      assessment_id, dimension, status, measure_kind, explanation
    ) values (
      '66666666-6666-4666-8666-666666666666',
      'infrastructure_investment',
      'available',
      'actual_capital_expenditure',
      'Available evidence needs a sourced update and this row has none.'
    )
  $$,
  '23514',
  null,
  'available evidence requires a sourced update'
);

select lives_ok(
  $$
    insert into research.theme_dimension_evidence (
      assessment_id, dimension, status, measure_kind, explanation, update_id,
      relationship, amount, unit, period_start, period_end, reporting_entity, filed_at
    ) values (
      '66666666-6666-4666-8666-666666666666',
      'infrastructure_investment',
      'available',
      'actual_capital_expenditure',
      'Company-wide actual capital expenditure for one annual period.',
      '33333333-3333-4333-8333-333333333333',
      'supports',
      '100',
      'USD',
      date '2024-07-01',
      date '2025-06-30',
      'Example entity',
      date '2025-07-30'
    )
  $$,
  'actual capital expenditure can support infrastructure investment'
);

select lives_ok(
  $$
    insert into research.theme_dimension_evidence (
      assessment_id, dimension, status, measure_kind, explanation
    ) values (
      '66666666-6666-4666-8666-666666666666',
      'commercial_adoption',
      'not_yet_monitored',
      'none',
      'A customer adoption observation is still required.'
    )
  $$,
  'a dimension can stay not yet monitored'
);

select ok(
  not has_table_privilege('anon', 'research.macro_events', 'SELECT'),
  'anon cannot select macro events'
);
select ok(
  not has_table_privilege('authenticated', 'research.macro_events', 'SELECT'),
  'authenticated cannot select macro events'
);
select ok(
  not has_table_privilege('service_role', 'research.macro_events', 'SELECT'),
  'service_role cannot select macro events'
);
select ok(
  has_table_privilege('research_writer', 'research.macro_events', 'SELECT')
    and has_table_privilege('research_writer', 'research.macro_events', 'INSERT')
    and not has_table_privilege('research_writer', 'research.macro_events', 'UPDATE')
    and not has_table_privilege('research_writer', 'research.macro_events', 'DELETE'),
  'research_writer can read and append macro events only'
);
select ok(
  has_table_privilege('research_worker', 'research.macro_events', 'SELECT')
    and has_table_privilege('research_worker', 'research.macro_event_evidence', 'INSERT')
    and not has_table_privilege('research_worker', 'research.macro_event_evidence', 'UPDATE'),
  'research_worker inherits append on event evidence and cannot update it'
);
select ok(
  has_table_privilege('research_writer', 'research.theme_assessments', 'INSERT')
    and not has_table_privilege('anon', 'research.theme_assessments', 'SELECT')
    and not has_table_privilege('service_role', 'research.theme_dimension_evidence', 'SELECT')
    and not has_table_privilege('research_writer', 'research.theme_dimension_evidence', 'DELETE'),
  'theme tables match the sourced update grant boundary'
);

select * from finish();
rollback;
