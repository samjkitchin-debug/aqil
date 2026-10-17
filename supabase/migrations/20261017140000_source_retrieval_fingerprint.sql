-- M3: idempotent collection — fingerprint identical provider payloads per dataset.

alter table research.source_retrievals
  add column if not exists response_fingerprint text;

comment on column research.source_retrievals.response_fingerprint is
  'SHA-256 hex of canonical observation payload for duplicate-response detection.';

create index if not exists source_retrievals_dataset_fingerprint_idx
  on research.source_retrievals (dataset_id, response_fingerprint)
  where response_fingerprint is not null;
