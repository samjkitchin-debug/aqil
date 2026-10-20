-- pgTAP: sourced updates are append-only, idempotent per source and content hash,
-- and invisible to API roles.
begin;

select plan(25);

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
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    'fixture_sourced_update',
    'fixture.sourced.update',
    'fixture_sourced_update',
    'fixture',
    'fixture_sourced',
    '1.0.0',
    timestamptz '2025-02-01 12:00:00+00',
    'fixture',
    'example.test'
  ),
  (
    'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    'fixture_sourced_update_other',
    'fixture.sourced.other',
    'fixture_sourced_update_other',
    'fixture',
    'fixture_sourced',
    '1.0.0',
    timestamptz '2025-02-01 12:00:00+00',
    'fixture',
    'example.test'
  );

select lives_ok(
  $$
    insert into research.sourced_updates (
      update_id, source_id, title, canonical_url, published_at, retrieved_at,
      retrieval_id, content_hash
    ) values (
      'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
      'fixture_sourced_update',
      'Employment situation',
      'https://example.test/news/employment-situation',
      timestamptz '2025-02-01 08:30:00+00',
      timestamptz '2025-02-01 12:00:00+00',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    )
  $$,
  'first sourced update inserts'
);

select throws_ok(
  $$
    insert into research.sourced_updates (
      source_id, title, canonical_url, published_at, retrieved_at,
      retrieval_id, content_hash
    ) values (
      'fixture_sourced_update',
      'Employment situation',
      'https://example.test/news/employment-situation',
      timestamptz '2025-02-01 08:30:00+00',
      timestamptz '2025-02-01 13:00:00+00',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    )
  $$,
  '23505',
  null,
  'repeat fetch of the same source and content hash is rejected'
);

select lives_ok(
  $$
    insert into research.sourced_updates (
      update_id, source_id, title, canonical_url, published_at, retrieved_at,
      retrieval_id, content_hash, correction_of
    ) values (
      'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
      'fixture_sourced_update',
      'Employment situation (corrected)',
      'https://example.test/news/employment-situation',
      timestamptz '2025-02-01 09:00:00+00',
      timestamptz '2025-02-01 12:30:00+00',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
      'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
    )
  $$,
  'correction is a new row'
);

select results_eq(
  $$
    select title
    from research.sourced_updates
    where update_id = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
  $$,
  $$ values ('Employment situation') $$,
  'original title is unchanged after a correction row'
);

select throws_ok(
  $$
    insert into research.sourced_updates (
      source_id, title, canonical_url, retrieved_at, retrieval_id, content_hash, status
    ) values (
      'fixture_sourced_update',
      'Employment situation',
      'https://example.test/news/employment-situation',
      timestamptz '2025-02-01 12:00:00+00',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
      'inferred'
    )
  $$,
  '23514',
  null,
  'status other than sourced is rejected'
);

select throws_ok(
  $$
    update research.sourced_updates
    set title = 'rewritten'
    where update_id = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
  $$,
  'P0001',
  null,
  'update is blocked'
);

select throws_ok(
  $$
    delete from research.sourced_updates
    where update_id = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
  $$,
  'P0001',
  null,
  'delete is blocked'
);

select throws_ok(
  $$
    insert into research.sourced_updates (
      source_id, title, canonical_url, retrieved_at, retrieval_id, content_hash
    ) values (
      'fixture_sourced_update_other',
      'Wrong source',
      'https://example.test/news/other',
      timestamptz '2025-02-01 12:00:00+00',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'
    )
  $$,
  'P0001',
  null,
  'source_id must match the retrieval'
);

select throws_ok(
  $$
    insert into research.sourced_updates (
      source_id, title, canonical_url, published_at, retrieved_at, retrieval_id, content_hash
    ) values (
      'fixture_sourced_update',
      'Backdated publication',
      'https://example.test/news/employment-situation',
      timestamptz '2025-03-01 00:00:00+00',
      timestamptz '2025-02-01 12:00:00+00',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
    )
  $$,
  '23514',
  null,
  'published_at cannot be after retrieved_at'
);

select throws_ok(
  $$
    insert into research.sourced_updates (
      source_id, title, canonical_url, retrieved_at, retrieval_id, content_hash
    ) values (
      'fixture_sourced_update',
      'Secret URL',
      'https://user:password@example.test/news',
      timestamptz '2025-02-01 12:00:00+00',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
    )
  $$,
  '23514',
  null,
  'canonical URL must not carry a secret'
);

select throws_ok(
  $$
    insert into research.sourced_updates (
      source_id, title, canonical_url, retrieved_at, retrieval_id, content_hash
    ) values (
      'fixture_sourced_update',
      'Bad hash',
      'https://example.test/news/employment-situation',
      timestamptz '2025-02-01 12:00:00+00',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      'not-a-hash'
    )
  $$,
  '23514',
  null,
  'content hash must be SHA-256 hex'
);

select throws_ok(
  $$
    insert into research.sourced_updates (
      source_id, title, canonical_url, retrieved_at, retrieval_id, content_hash, correction_of
    ) values (
      'fixture_sourced_update_other',
      'Cross-source correction',
      'https://example.test/news/other',
      timestamptz '2025-02-01 12:00:00+00',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
      'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
    )
  $$,
  'P0001',
  null,
  'correction must keep the same source_id'
);

select throws_ok(
  $$
    insert into research.sourced_updates (
      update_id, source_id, title, canonical_url, retrieved_at, retrieval_id,
      content_hash, correction_of
    ) values (
      'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
      'fixture_sourced_update',
      'Self correction',
      'https://example.test/news/self',
      timestamptz '2025-02-01 12:00:00+00',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      'fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210',
      'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'
    )
  $$,
  'P0001',
  null,
  'a row cannot correct itself'
);

select ok(
  not has_table_privilege('authenticated', 'research.sourced_updates', 'SELECT'),
  'authenticated cannot select sourced updates'
);

select ok(
  not has_table_privilege('anon', 'research.sourced_updates', 'SELECT'),
  'anon cannot select sourced updates'
);

select ok(
  not has_table_privilege('anon', 'research.sourced_updates', 'INSERT'),
  'anon cannot insert sourced updates'
);

select ok(
  not has_table_privilege('service_role', 'research.sourced_updates', 'SELECT'),
  'service_role cannot select sourced updates'
);

select ok(
  has_table_privilege('research_writer', 'research.sourced_updates', 'SELECT'),
  'research_writer can select sourced updates'
);

select ok(
  has_table_privilege('research_writer', 'research.sourced_updates', 'INSERT'),
  'research_writer can insert sourced updates'
);

select ok(
  not has_table_privilege('research_writer', 'research.sourced_updates', 'UPDATE'),
  'research_writer cannot update sourced updates'
);

select ok(
  not has_table_privilege('research_writer', 'research.sourced_updates', 'DELETE'),
  'research_writer cannot delete sourced updates'
);

select ok(
  has_table_privilege('research_worker', 'research.sourced_updates', 'SELECT'),
  'research_worker can select sourced updates'
);

select ok(
  has_table_privilege('research_worker', 'research.sourced_updates', 'INSERT'),
  'research_worker can insert sourced updates'
);

select ok(
  not has_table_privilege('research_worker', 'research.sourced_updates', 'UPDATE'),
  'research_worker cannot update sourced updates'
);

select ok(
  not has_table_privilege('research_worker', 'research.sourced_updates', 'DELETE'),
  'research_worker cannot delete sourced updates'
);

select * from finish();
rollback;
