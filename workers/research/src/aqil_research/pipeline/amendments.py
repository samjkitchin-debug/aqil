"""Link a new copy of the same official page to the copy it replaces.

The earlier row stays. A matching content hash is not an amendment.
"""

from __future__ import annotations

import psycopg

from aqil_research.contracts.sourced_update import SourcedUpdate


def link_amendment(conn: psycopg.Connection, row: SourcedUpdate) -> SourcedUpdate:
    if row.correction_of is not None:
        return row
    with conn.cursor() as cur:
        cur.execute(
            """
            select update_id::text
            from research.sourced_updates
            where source_id = %s
              and canonical_url = %s
              and content_hash <> %s
            order by retrieved_at desc
            limit 1
            """,
            (row.source_id, row.canonical_url, row.content_hash),
        )
        found = cur.fetchone()
    if found is None:
        return row
    return row.model_copy(update={"correction_of": found[0]})
