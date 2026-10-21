"""A changed copy of the same official page links to the copy it replaces."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest

from aqil_research.contracts.sourced_update import SourcedUpdate
from aqil_research.pipeline.amendments import link_amendment
from db_guard import open_isolated_test_database

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def require_db() -> str:
    return open_isolated_test_database()


def test_same_official_page_links_the_earlier_copy(require_db: str) -> None:
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    page = f"https://www.ecb.europa.eu/press/govcdec/otherdec/2026/html/{uuid4().hex}.en.html"
    first_hash = uuid4().hex + uuid4().hex
    second_hash = uuid4().hex + uuid4().hex
    with psycopg.connect(require_db) as conn:
        retrieval_id = _retrieval(conn, now)
        first = _row(retrieval_id, now, first_hash, "First title", page)
        _insert(conn, first)
        second = link_amendment(
            conn,
            _row(retrieval_id, now, second_hash, "Corrected title", page),
        )
        assert second.correction_of == first.update_id
        _insert(conn, second)
        rows = conn.execute(
            """
            select content_hash, correction_of::text
            from research.sourced_updates
            where retrieval_id = %s
            order by content_hash
            """,
            (retrieval_id,),
        ).fetchall()
    assert rows == sorted(
        [(first_hash, None), (second_hash, first.update_id)],
        key=lambda row: row[0],
    )


def _retrieval(conn: psycopg.Connection, now: datetime) -> str:
    row = conn.execute(
        """
        insert into research.source_retrievals (
          source_id, dataset_id, rights_record_id, provider_id,
          adapter_id, adapter_version, retrieved_at, collection_mode,
          endpoint_host
        )
        values (
          'ecb_monetary_press', 'ecb.press.monetary', 'ecb_monetary_press',
          'european_central_bank', 'ecb_monetary_press', '1', %s, 'fixture', 'fixture'
        )
        returning retrieval_id::text
        """,
        (now,),
    ).fetchone()
    assert row is not None
    return str(row[0])


def _row(
    retrieval_id: str,
    now: datetime,
    content_hash: str,
    title: str,
    page: str,
) -> SourcedUpdate:
    return SourcedUpdate(
        update_id=str(uuid4()),
        source_id="ecb_monetary_press",
        title=title,
        canonical_url=page,
        published_at=now,
        retrieved_at=now,
        retrieval_id=retrieval_id,
        content_hash=content_hash,
        status="sourced",
    )


def _insert(conn: psycopg.Connection, row: SourcedUpdate) -> None:
    conn.execute(
        """
        insert into research.sourced_updates (
          update_id, schema_version, source_id, title, canonical_url,
          published_at, retrieved_at, retrieval_id, content_hash,
          correction_of, status
        )
        values (%s::uuid, %s, %s, %s, %s, %s, %s, %s::uuid, %s, %s, %s)
        """,
        (
            row.update_id,
            row.schema_version,
            row.source_id,
            row.title,
            row.canonical_url,
            row.published_at,
            row.retrieved_at,
            row.retrieval_id,
            row.content_hash,
            row.correction_of,
            row.status,
        ),
    )
