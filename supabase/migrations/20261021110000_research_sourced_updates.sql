-- Sourced updates: append-only publication items, separate from numeric observations.
-- A repeat fetch of the same source item is the same row. A correction is a new row.
-- Local migration only. Do not treat this file as a hosted apply.

create table research.sourced_updates (
  update_id uuid primary key default gen_random_uuid(),
  schema_version text not null default '1.0',
  source_id text not null,
  title text not null,
  canonical_url text not null,
  published_at timestamptz,
  retrieved_at timestamptz not null,
  retrieval_id uuid not null references research.source_retrievals (retrieval_id),
  content_hash text not null,
  correction_of uuid,
  status text not null default 'sourced',
  constraint sourced_updates_schema_version check (schema_version = '1.0'),
  constraint sourced_updates_source_id_present check (char_length(btrim(source_id)) >= 1),
  constraint sourced_updates_title_present check (char_length(btrim(title)) >= 1),
  constraint sourced_updates_canonical_url check (
    canonical_url ~ '^https://[^[:space:]]+$'
    and not research.text_contains_secret_pattern(canonical_url)
  ),
  constraint sourced_updates_published_not_after_retrieval check (
    published_at is null or published_at <= retrieved_at
  ),
  constraint sourced_updates_content_hash check (content_hash ~ '^[0-9a-f]{64}$'),
  constraint sourced_updates_status_sourced check (status = 'sourced'),
  constraint sourced_updates_not_self_correction check (
    correction_of is null or correction_of <> update_id
  ),
  constraint sourced_updates_source_content_key unique (source_id, content_hash),
  constraint sourced_updates_correction_of_fkey
    foreign key (correction_of) references research.sourced_updates (update_id)
);

comment on table research.sourced_updates is
  'Append-only sourced item: source, title, canonical URL, publication time and retrieval. Status is sourced. Not an investment conclusion. No user id.';

comment on column research.sourced_updates.source_id is
  'User-independent source identity from the rights register.';

comment on column research.sourced_updates.published_at is
  'Publication time stated by the source. Null when the source does not state one.';

comment on column research.sourced_updates.retrieved_at is
  'When this item was fetched. Not the publication time.';

comment on column research.sourced_updates.content_hash is
  'SHA-256 hex of the canonical sourced item. With source_id, a repeat fetch is one row.';

comment on column research.sourced_updates.correction_of is
  'Earlier sourced update this row corrects. A correction is a new row, not an update.';

comment on column research.sourced_updates.status is
  'Limited to sourced. Do not store an investment conclusion here.';

create index sourced_updates_retrieved_at_idx
  on research.sourced_updates (retrieved_at desc);

create index sourced_updates_retrieval_id_idx
  on research.sourced_updates (retrieval_id);

create or replace function research.enforce_sourced_update_consistency()
returns trigger
language plpgsql
set search_path = research, pg_temp
as $$
declare
  v_retrieval_source text;
  v_prior_source text;
begin
  select source_id
  into v_retrieval_source
  from research.source_retrievals
  where retrieval_id = new.retrieval_id;

  if v_retrieval_source is null then
    raise exception 'unknown retrieval_id %', new.retrieval_id;
  end if;

  if new.source_id is distinct from v_retrieval_source then
    raise exception 'sourced update source_id must match source_retrievals row';
  end if;

  if new.correction_of is not null then
    if new.correction_of = new.update_id then
      raise exception 'a sourced update cannot correct itself';
    end if;

    select source_id
    into v_prior_source
    from research.sourced_updates
    where update_id = new.correction_of;

    if v_prior_source is null then
      raise exception 'unknown correction_of %', new.correction_of;
    end if;

    if v_prior_source is distinct from new.source_id then
      raise exception 'correction must keep the same source_id';
    end if;
  end if;

  return new;
end;
$$;

comment on function research.enforce_sourced_update_consistency() is
  'Keeps a sourced update on the same source as its retrieval. A correction stays on that source.';

create trigger sourced_updates_consistency
before insert on research.sourced_updates
for each row
execute function research.enforce_sourced_update_consistency();

create trigger sourced_updates_deny_mutation
before update or delete on research.sourced_updates
for each row
execute function research.deny_row_mutation();

-- Same grants as the other research tables: worker read/append, no API role, no service_role.
revoke all on table research.sourced_updates from public;
revoke all on table research.sourced_updates from anon;
revoke all on table research.sourced_updates from authenticated;
revoke all on table research.sourced_updates from service_role;

grant select, insert on table research.sourced_updates to research_writer;

revoke all on function research.enforce_sourced_update_consistency() from public;
revoke all on function research.enforce_sourced_update_consistency() from anon;
revoke all on function research.enforce_sourced_update_consistency() from authenticated;
revoke all on function research.enforce_sourced_update_consistency() from service_role;

grant execute on function research.enforce_sourced_update_consistency() to research_writer;
