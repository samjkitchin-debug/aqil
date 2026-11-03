-- Historical-state atlas. Append-only, unpublished, and outcomes are not states.
begin;

select plan(15);

insert into research.atlas_specifications (
  specification_id, version, specification, specification_hash, frozen_at, publication_allowed
) values (
  'ATLAS-DEF-001',
  1,
  '{"schema_version":"1.0"}'::jsonb,
  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  timestamptz '2026-11-04 00:00:00+00',
  false
);

insert into research.decision_anchors (
  anchor_id, specification_id, specification_version, specification_hash, symbol,
  anchor_kind, session_date, lookback_sufficient, listing_currency,
  publication_allowed, recorded_at
) values (
  'anchor-1',
  'ATLAS-DEF-001',
  1,
  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  'VWRA',
  'listing_month_end',
  date '2024-01-31',
  false,
  'USD',
  false,
  timestamptz '2026-11-04 00:00:00+00'
);

insert into research.state_observations (
  state_id, anchor_id, feature_id, feature_family, availability, clock,
  usable_as_decision_input, value_text, detail, publication_allowed, recorded_at
) values (
  'state-1',
  'anchor-1',
  'split_adjusted_close',
  'market',
  'observed',
  'stored_sessions',
  true,
  '100',
  'split-adjusted close, not a total return',
  false,
  timestamptz '2026-11-04 00:00:00+00'
);

insert into research.outcome_measures (
  outcome_id, anchor_id, horizon_label, session_steps, status, value_text,
  labelled_advance, readable_as_state_input, known_at_anchor,
  publication_allowed, recorded_at
) values (
  'outcome-1',
  'anchor-1',
  '6m',
  126,
  'censored',
  null,
  null,
  false,
  false,
  false,
  timestamptz '2026-11-04 00:00:00+00'
);

select has_table('research', 'decision_anchors', 'decision anchors exist');
select has_table('research', 'state_observations', 'state observations exist');
select has_table('research', 'outcome_measures', 'outcome measures exist');

select is(
  (
    select c.relkind
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'research' and c.relname = 'anchor_research_matrix'
  ),
  'v',
  'the research matrix is a view'
);

select ok(
  not has_table_privilege('anon', 'research.state_observations', 'SELECT'),
  'anon cannot select state observations'
);

select ok(
  has_table_privilege('research_writer', 'research.state_observations', 'INSERT'),
  'research writer can insert a state'
);

select throws_ok(
  $$
    update research.decision_anchors
    set lookback_sufficient = true
    where anchor_id = 'anchor-1'
  $$,
  'P0001',
  null,
  'decision anchors are append-only'
);

select throws_ok(
  $$
    delete from research.outcome_measures where outcome_id = 'outcome-1'
  $$,
  'P0001',
  null,
  'outcome measures are append-only'
);

select throws_ok(
  $$
    insert into research.state_observations (
      state_id, anchor_id, feature_id, feature_family, availability, clock,
      usable_as_decision_input, value_text, detail, publication_allowed, recorded_at
    ) values (
      'state-published', 'anchor-1', 'split_adjusted_close', 'market', 'observed',
      'stored_sessions', true, '1', 'detail', true, timestamptz '2026-11-04 00:00:00+00'
    )
  $$,
  '23514',
  null,
  'a state cannot be published'
);

select throws_ok(
  $$
    insert into research.state_observations (
      state_id, anchor_id, feature_id, feature_family, availability, clock,
      usable_as_decision_input, value_text, detail, publication_allowed, recorded_at
    ) values (
      'state-outcome', 'anchor-1', 'outcome_forward_return', 'market', 'observed',
      'stored_sessions', true, '0.1', 'detail', false, timestamptz '2026-11-04 00:00:00+00'
    )
  $$,
  '23514',
  null,
  'an outcome feature cannot be stored as a state'
);

select throws_ok(
  $$
    insert into research.outcome_measures (
      outcome_id, anchor_id, horizon_label, session_steps, status, value_text,
      labelled_advance, readable_as_state_input, known_at_anchor,
      publication_allowed, recorded_at
    ) values (
      'outcome-readable', 'anchor-1', '1m', 21, 'observed', '0.01', null,
      true, false, false, timestamptz '2026-11-04 00:00:00+00'
    )
  $$,
  '23514',
  null,
  'an outcome cannot be marked readable as a state input'
);

select throws_ok(
  $$
    insert into research.state_observations (
      state_id, anchor_id, feature_id, feature_family, availability, clock,
      usable_as_decision_input, value_text, detail, publication_allowed, recorded_at
    ) values (
      'state-retro', 'anchor-1', 'bls.cu.CUSR0000SA0:level', 'economic_retrospective',
      'observed', 'retrospective_latest_revised_release_lag_unknown', true, '1',
      'detail', false, timestamptz '2026-11-04 00:00:00+00'
    )
  $$,
  '23514',
  null,
  'a latest-revised state cannot be a decision input'
);

select throws_ok(
  $$
    insert into research.decision_anchors (
      anchor_id, specification_id, specification_version, specification_hash, symbol,
      anchor_kind, session_date, lookback_sufficient, publication_allowed, recorded_at
    ) values (
      'anchor-transition', 'ATLAS-DEF-001', 1,
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      'VWRA', 'market_transition', date '2024-02-01', false, false,
      timestamptz '2026-11-04 00:00:00+00'
    )
  $$,
  '23514',
  null,
  'a market-transition anchor is refused'
);

select lives_ok(
  $$
    insert into research.scientific_status_events (
      status_event_id, subject_kind, subject_id, subject_version, status,
      rationale, derivation, recorded_at, publication_allowed
    ) values (
      'ATLAS-STATUS-FIXTURE', 'claim', 'LH-C-004-fixture', 1,
      'no_incremental_information', 'fixture', 'deterministic_criteria',
      timestamptz '2026-11-04 00:00:00+00', false
    )
  $$,
  'no incremental information is an allowed status and is not a promotion'
);

select throws_ok(
  $$
    do $body$
    begin
    insert into research.hypotheses (
      hypothesis_id, version, proposition, economic_rationale, expected_mechanism,
      expected_direction, horizon, falsification_criteria, alternative_explanations,
      relevant_indicators, relevant_methodologies, target_instruments, initial_status,
      registered_at, registered_by, publication_allowed
    ) values (
      'ATLAS-H-FIXTURE', 1, 'proposition', 'rationale', 'none', 'none', 'none',
      'none', '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 'proposed',
      timestamptz '2026-11-04 00:00:00+00', 'fixture', false
    );
    insert into research.experiment_specifications (
      experiment_id, version, category, category_label, specification,
      specification_hash, frozen_at, publication_allowed
    ) values (
      'ATLAS-E-FIXTURE', 1, 'C', 'price_only_simulator_research',
      '{"not_macroeconomic_investment_intelligence":"true"}'::jsonb,
      'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
      timestamptz '2026-11-04 00:00:00+00', false
    );
    insert into research.experiment_executions (
      execution_id, experiment_id, experiment_version, state, git_commit, code_hash,
      input_manifest, macro_vintage_ids, price_series_versions, library_versions,
      executed_at, availability_cutoff, artifact_sha256, reproduction_command,
      validation_status, configuration, publication_allowed
    ) values (
      'ATLAS-X-FIXTURE', 'ATLAS-E-FIXTURE', 1, 'succeeded', 'abc',
      'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
      '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, '{}'::jsonb,
      timestamptz '2026-11-04 00:00:00+00', timestamptz '2026-11-04 00:00:00+00',
      'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
      'fixture', 'inconclusive', '{}'::jsonb, false
    );
    insert into research.evidence_records (
      evidence_id, execution_id, evidence_kind, content_sha256, body, recorded_at,
      publication_allowed
    ) values (
      'ATLAS-V-FIXTURE', 'ATLAS-X-FIXTURE', 'statistical_note',
      'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
      '{}'::jsonb, timestamptz '2026-11-04 00:00:00+00', false
    );
    insert into research.scientific_claims (
      claim_id, version, proposition, status_at_claim, eligibility_class,
      statistical_validity, economic_usefulness, independent_validation,
      remaining_uncertainty, publication_eligible, publication_allowed, derivation,
      reviewer_note, recorded_at
    ) values (
      'ATLAS-C-FIXTURE', 1, 'promoted', 'statistically_supported',
      'category_c_price_only', 'none', 'none', 'none', 'none', false, false,
      'deterministic_criteria', 'none',       timestamptz '2026-11-04 00:00:00+00'
    );
    end
    $body$;
  $$,
  '23514',
  null,
  'category C remains unable to be statistically supported'
);

select * from finish();
rollback;
