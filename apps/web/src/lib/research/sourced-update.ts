/**
 * Sourced update v1 — mirrors packages/contracts/schemas/sourced_update.v1.json.
 * Field names come from that schema. A sourced update is not an investment conclusion.
 */
import schema from "../../../../../packages/contracts/schemas/sourced_update.v1.json";

export const sourcedUpdateSchema = schema;

/** Shared with the research worker. Do not rename these in the reader. */
export const sourcedUpdateFields = schema.required;

export type SourcedUpdateStatus = "sourced";

export type SourcedUpdateV1 = {
  schema_version: "1.0";
  update_id: string;
  source_id: string;
  title: string;
  canonical_url: string;
  published_at: string | null;
  retrieved_at: string;
  retrieval_id: string;
  content_hash: string;
  correction_of: string | null;
  status: SourcedUpdateStatus;
};

const typedFieldNames = Object.keys({
  schema_version: true,
  update_id: true,
  source_id: true,
  title: true,
  canonical_url: true,
  published_at: true,
  retrieved_at: true,
  retrieval_id: true,
  content_hash: true,
  correction_of: true,
  status: true,
} satisfies Record<keyof SourcedUpdateV1, true>);

if (
  typedFieldNames.length !== schema.required.length ||
  schema.required.some((name, index) => name !== typedFieldNames[index])
) {
  throw new Error(
    "Sourced update fields do not match packages/contracts/schemas/sourced_update.v1.json.",
  );
}
