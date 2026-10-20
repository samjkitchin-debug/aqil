"""Offline tests for BLS Employment Situation publication feed collection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aqil_research.adapters.bls_release import (
    InMemorySourcedUpdateStore,
    collect_bls_releases,
)
from aqil_research.adapters.bls_release.adapter import BlsEmpsitReleaseAdapter
from aqil_research.adapters.bls_release.client import BlsReleaseClientError, _assert_url_allowed
from aqil_research.adapters.bls_release.constants import BLS_EMPSIT_ARCHIVE_URL, BLS_EMPSIT_RSS_URL
from aqil_research.adapters.bls_release.normalize import SourcedUpdateDraft, content_hash_for_item
from aqil_research.adapters.bls_release.parse import parse_publication_feed
from aqil_research.pipeline.feed_freshness import FeedPollSnapshot
from aqil_research.sources.rights import OperationalStatus, load_source_rights

FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "empsit_release.rss"
RETRIEVED = datetime(2025, 10, 17, 12, 0, tzinfo=UTC)


def test_parse_fixture_rss() -> None:
    body = FIXTURE.read_bytes()
    items = parse_publication_feed(body, base_url=BLS_EMPSIT_RSS_URL)
    assert len(items) == 2
    assert items[0].canonical_url.startswith("https://www.bls.gov/")
    assert items[0].title == "Employment Situation Summary"


def test_collect_offline_success() -> None:
    store = InMemorySourcedUpdateStore()
    result = collect_bls_releases(
        store,
        live=False,
        fixture_path=FIXTURE,
        retrieved_at=RETRIEVED,
    )
    assert result.outcome == "success"
    assert result.updates_received == 2
    assert result.updates_newly_stored == 2
    assert len(store.updates) == 2
    row = store.updates[0]
    assert row.source_id == "bls_employment_situation_archive"
    assert row.status == "sourced"
    assert row.canonical_url.startswith("https://www.bls.gov/")
    assert row.retrieval_id


def test_collect_idempotent_on_content_hash() -> None:
    store = InMemorySourcedUpdateStore()
    first = collect_bls_releases(
        store,
        live=False,
        fixture_path=FIXTURE,
        retrieved_at=RETRIEVED,
    )
    second = collect_bls_releases(
        store,
        live=False,
        fixture_path=FIXTURE,
        retrieved_at=RETRIEVED,
    )
    assert first.updates_newly_stored == 2
    assert second.outcome == "unchanged"
    assert second.updates_newly_stored == 0
    assert second.updates_unchanged == 2
    assert len(store.updates) == 2


def test_rights_gate_blocks_before_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    from aqil_research.adapters import bls_release as package
    from aqil_research.sources import rights as rights_mod

    called = {"fetch": False}

    def _boom(*_args: object, **_kwargs: object) -> None:
        called["fetch"] = True
        raise AssertionError("fetch should not run when rights fail")

    monkeypatch.setattr(package.collect, "assert_rights_for_ingest", _boom)

    records = load_source_rights()
    disabled = [
        row.model_copy(update={"operational_status": OperationalStatus.DISABLED})
        if row.source_id == "bls_employment_situation_archive"
        else row
        for row in records
    ]
    monkeypatch.setattr(rights_mod, "load_source_rights", lambda: disabled)
    monkeypatch.setattr(package.collect, "load_source_rights", lambda: disabled)

    result = collect_bls_releases(
        InMemorySourcedUpdateStore(),
        live=False,
        fixture_path=FIXTURE,
        retrieved_at=RETRIEVED,
    )
    assert result.outcome == "failed_rights"
    assert called["fetch"] is False


def test_live_urls_are_allowlisted() -> None:
    _assert_url_allowed(BLS_EMPSIT_RSS_URL)
    _assert_url_allowed(BLS_EMPSIT_ARCHIVE_URL)
    with pytest.raises(BlsReleaseClientError):
        _assert_url_allowed("https://api.bls.gov/publicAPI/v2/timeseries/data/")


def test_ten_copies_of_one_release_store_one_row(monkeypatch: pytest.MonkeyPatch) -> None:
    published = datetime(2025, 10, 3, 12, 30, tzinfo=UTC)
    url = "https://www.bls.gov/news.release/empsit.nr0.htm"
    draft = SourcedUpdateDraft(
        title="Employment Situation Summary",
        canonical_url=url,
        published_at=published,
        content_hash=content_hash_for_item(
            title="Employment Situation Summary",
            canonical_url=url,
            published_at=published,
        ),
    )

    def _fetch(_self: BlsEmpsitReleaseAdapter) -> tuple[tuple[SourcedUpdateDraft, ...], tuple[()]]:
        return (tuple(draft for _ in range(10)), ())

    monkeypatch.setattr(BlsEmpsitReleaseAdapter, "fetch_publications", _fetch)
    store = InMemorySourcedUpdateStore()
    result = collect_bls_releases(
        store,
        live=False,
        fixture_path=FIXTURE,
        retrieved_at=RETRIEVED,
    )
    assert result.outcome == "success"
    assert result.updates_received == 10
    assert result.updates_newly_stored == 1
    assert result.updates_unchanged == 0
    assert len(store.updates) == 1
    assert store.updates[0].status == "sourced"
    assert store.updates[0].canonical_url == url


def test_stale_feed_inserts_nothing() -> None:
    snapshot = FeedPollSnapshot(
        source_id="bls_employment_situation_archive",
        last_success_at=RETRIEVED - timedelta(hours=12),
        last_attempt_at=RETRIEVED - timedelta(hours=12),
        last_attempt_succeeded=True,
    )
    store = InMemorySourcedUpdateStore()
    result = collect_bls_releases(
        store,
        live=False,
        fixture_path=FIXTURE,
        retrieved_at=RETRIEVED,
        feed_snapshot=snapshot,
    )
    assert result.outcome == "failed_validation"
    assert result.updates_newly_stored == 0
    assert result.updates_unchanged == 0
    assert result.retrieval_id is None
    assert store.updates == []


def test_content_hash_stable() -> None:
    published = datetime(2025, 10, 3, 12, 30, tzinfo=UTC)
    first = content_hash_for_item(
        title="Employment Situation Summary",
        canonical_url="https://www.bls.gov/news.release/empsit.nr0.htm",
        published_at=published,
    )
    second = content_hash_for_item(
        title="Employment Situation Summary",
        canonical_url="https://www.bls.gov/news.release/empsit.nr0.htm",
        published_at=published,
    )
    assert first == second
    assert len(first) == 64
