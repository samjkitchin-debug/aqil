"""Cited issuer documents persist only on an isolated disposable database.

The repository has no permitted issuer document. These tests do not connect to
the preserved databases postgres or aqil_etf, and they do not invent VWRA facts.
"""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import psycopg
import pytest
from pydantic import ValidationError

from aqil_research.etf.documents.command import cite_issuer_document, run_cite_etf
from aqil_research.etf.documents.ingest import (
    FIRST_INSERT_REQUIREMENT,
    CitedCharacteristic,
    CitedExposure,
    CitedIssuerDocument,
    CitedListing,
    DocumentIngestError,
    apply_repository_documents,
    load_repository_documents,
    persist_cited_share_class,
)
from aqil_research.etf.identity.catalogue import (
    ANCHOR_ISIN,
    ANCHOR_SOURCE_ID,
    ANCHOR_SOURCE_LOCATOR,
)
from aqil_research.sources.rights import (
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsDecision,
    SourceRightsRecord,
    find_source_rights,
    load_source_rights,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = REPO_ROOT / "supabase" / "migrations" / "20261024120000_etf_instruments.sql"
CONTAINER = "supabase_db_ojvswermsbbaltjohqph"
DISPOSABLE = "aqil_cited_document_test"
DISPOSABLE_URL = f"postgresql://research_worker:research_worker@127.0.0.1:55432/{DISPOSABLE}"
MARKER = "disposable-cited-document-test"
PRESERVED = frozenset({"postgres", "aqil_etf"})


class _Row:
    def __init__(self, row: tuple[object, ...] | None) -> None:
        self._row = row

    def fetchone(self) -> tuple[object, ...] | None:
        return self._row


class _Untouched:
    def execute(self, *_args: object, **_kwargs: object) -> _Row:
        raise AssertionError("the database must not be touched")

    def transaction(self) -> None:
        raise AssertionError("the database must not be touched")


class _NamedDatabase:
    def __init__(self, name: str) -> None:
        self.name = name
        self.sql: list[str] = []

    def execute(self, sql: str, _params: object = None) -> _Row:
        self.sql.append(sql)
        if "current_database" not in sql:
            raise AssertionError(sql)
        return _Row((self.name,))

    def transaction(self) -> None:
        raise AssertionError("a preserved database must not be written")


def _rights(
    *,
    source_id: str = "fixture_cited_issuer_document",
    automated_access: RightsDecision = RightsDecision.PERMITTED,
    raw_data_retention: RightsDecision = RightsDecision.PERMITTED,
    internal_computation: RightsDecision = RightsDecision.PERMITTED,
    redistribution: RightsDecision = RightsDecision.PERMITTED,
    status: OperationalStatus = OperationalStatus.ENABLED,
) -> SourceRightsRecord:
    return SourceRightsRecord(
        source_id=source_id,
        dataset_id="fixture.cited.document",
        provider_name="Synthetic issuer",
        publication_name="Synthetic issuer document",
        geography="IE",
        series_or_dataset_code="synthetic-cited-document",
        category="etf_reference",
        access_description="In-memory fixture. No issuer was contacted.",
        access_url="https://example.com/access",
        terms_url="https://example.com/terms",
        evidence_urls=("https://example.com/terms",),
        auth_requirement="None.",
        automated_access=automated_access,
        internal_computation=internal_computation,
        raw_data_retention=raw_data_retention,
        historical_archiving=RightsDecision.UNKNOWN,
        redistribution=redistribution,
        commercial_publication=RightsDecision.UNKNOWN,
        ai_processing=RightsDecision.UNKNOWN,
        ai_model_training=RightsDecision.UNKNOWN,
        attribution=AttributionRequirement.UNKNOWN,
        m1_role=M1Role.UNRESOLVED,
        operational_status=status,
        conditions="Synthetic rights row. Not an edit to SOURCE_RIGHTS.csv.",
        revision_behaviour="None.",
        unresolved_questions="None.",
        evidence_note="Not a provider assessment.",
        assessed_on=date(2026, 10, 24),
    )


def _document(**overrides: object) -> CitedIssuerDocument:
    values: dict[str, object] = {
        "source_id": "fixture_cited_issuer_document",
        "source_locator": "synthetic://aqil/etf/cited-document",
        "document_date": date(2026, 1, 15),
        "retrieved_on": date(2026, 1, 16),
        "founder_supplied": False,
        "isin": "IE00B0000009",
        "umbrella_legal_name": "Synthetic umbrella",
        "sub_fund_legal_name": "Synthetic sub-fund",
        "base_currency": "GBP",
        "distribution_policy": "distributing",
        "hedge_status": "unhedged",
    }
    values.update(overrides)
    return CitedIssuerDocument.model_validate(values)


def test_repository_has_no_cited_document() -> None:
    assert not cited_directory_has_json()
    assert load_repository_documents() == ()
    result = apply_repository_documents(_Untouched())  # type: ignore[arg-type]
    assert result.documents_found == 0
    assert result.inserted == 0
    assert result.requirement == FIRST_INSERT_REQUIREMENT
    for phrase in (
        "docs/sources/etf/cited/",
        "source_id",
        "source_locator",
        "document_date",
        "retrieved_on",
        "isin",
        "umbrella_legal_name",
        "sub_fund_legal_name",
        "base_currency",
        "distribution_policy",
        "hedge_status",
        "founder_supplied",
        "operational_status enabled",
        "automated_access",
        "raw_data_retention",
        "internal_computation",
        "redistribution",
        "SOURCE_RIGHTS.csv",
        "instruments.share_classes",
    ):
        assert phrase in FIRST_INSERT_REQUIREMENT


def test_resolution_uses_instruments_not_forward_tables() -> None:
    source = Path(persist_cited_share_class.__code__.co_filename).read_text(encoding="utf-8")
    assert "instruments.share_classes" in source
    assert "from forward" not in source
    assert "join forward" not in source


def test_unknown_founder_supplied_document_does_not_insert() -> None:
    rights = _rights(
        automated_access=RightsDecision.UNKNOWN,
        raw_data_retention=RightsDecision.UNKNOWN,
        internal_computation=RightsDecision.UNKNOWN,
        redistribution=RightsDecision.UNKNOWN,
    )
    result = persist_cited_share_class(_Untouched(), _document(founder_supplied=True), rights)  # type: ignore[arg-type]
    assert result.stored is False
    assert result.created is False
    assert result.founder_supplied is True
    assert result.blocked_uses == ("acquire", "retain", "extract", "display")
    assert {item.use: item.decision for item in result.use_decisions} == {
        "acquire": "unknown",
        "retain": "unknown",
        "extract": "unknown",
        "display": "unknown",
    }


def test_each_use_is_refused_on_its_own() -> None:
    blocked_extract = persist_cited_share_class(
        _Untouched(),  # type: ignore[arg-type]
        _document(),
        _rights(internal_computation=RightsDecision.UNKNOWN),
    )
    assert blocked_extract.blocked_uses == ("extract",)
    assert blocked_extract.stored is False

    blocked_display = persist_cited_share_class(
        _Untouched(),  # type: ignore[arg-type]
        _document(),
        _rights(redistribution=RightsDecision.PROHIBITED),
    )
    assert blocked_display.blocked_uses == ("display",)
    permitted = {item.use: item.permitted for item in blocked_display.use_decisions}
    assert permitted == {
        "acquire": True,
        "retain": True,
        "extract": True,
        "display": False,
    }


def test_a_disabled_source_is_not_usable() -> None:
    result = persist_cited_share_class(
        _Untouched(),  # type: ignore[arg-type]
        _document(),
        _rights(status=OperationalStatus.DISABLED),
    )
    assert result.stored is False
    assert result.blocked_uses == ("acquire", "retain", "extract", "display")
    assert all(
        item.decision == "permitted" and item.permitted is False for item in result.use_decisions
    )


def test_omitted_required_fields_stay_absent() -> None:
    result = persist_cited_share_class(
        _Untouched(),  # type: ignore[arg-type]
        _document(base_currency=None, inception_date=None),
        _rights(),
    )
    assert result.stored is False
    assert result.absent_fields == ("base_currency",)


def test_fixture_rows_are_not_issuer_documents() -> None:
    result = persist_cited_share_class(
        _Untouched(),  # type: ignore[arg-type]
        _document(
            isin=ANCHOR_ISIN,
            source_id=ANCHOR_SOURCE_ID,
            source_locator=ANCHOR_SOURCE_LOCATOR,
        ),
        _rights(source_id=ANCHOR_SOURCE_ID),
    )
    assert result.stored is False
    assert result.refusal == "the internal fixture is not a permitted issuer document"


def test_source_identity_must_match_the_rights_row() -> None:
    result = persist_cited_share_class(
        _Untouched(),  # type: ignore[arg-type]
        _document(),
        _rights(source_id="other_source"),
    )
    assert result.stored is False
    assert result.refusal == "source_id does not match the rights row"


@pytest.mark.parametrize("database", sorted(PRESERVED))
def test_preserved_databases_are_refused_without_a_write(database: str) -> None:
    conn = _NamedDatabase(database)
    with pytest.raises(DocumentIngestError, match=database):
        persist_cited_share_class(conn, _document(), _rights())  # type: ignore[arg-type]
    assert conn.sql == ["select current_database()"]


def test_a_document_needs_a_date() -> None:
    with pytest.raises(ValidationError):
        _document(document_date=None, retrieved_on=None)


def test_permitted_synthetic_document_is_idempotent_on_a_disposable_database(
    disposable_url: str,
) -> None:
    with _open(disposable_url) as conn:
        before = _counts(conn)
        repository = apply_repository_documents(conn)
        assert repository.documents_found == 0
        assert repository.inserted == 0
        assert _counts(conn) == before

        first = persist_cited_share_class(conn, _document(), _rights())
        assert first.created is True
        assert first.stored is True
        assert first.eligibility == "UNKNOWN"
        assert first.document_date == date(2026, 1, 15)
        assert first.retrieved_on == date(2026, 1, 16)
        after_first = _counts(conn)

        second = persist_cited_share_class(conn, _document(), _rights())
        assert second.created is False
        assert second.stored is True
        assert second.share_class_id == first.share_class_id
        assert second.eligibility == "UNKNOWN"
        assert _counts(conn) == after_first

        identity = conn.execute(
            """
            select s.evidence_status,
                   s.inception_date,
                   s.distribution_policy,
                   s.hedge_status,
                   f.base_currency,
                   u.domicile_iso2,
                   u.legal_name
            from instruments.share_classes s
            join instruments.sub_funds f on f.sub_fund_id = s.sub_fund_id
            join instruments.umbrellas u on u.umbrella_id = f.umbrella_id
            where s.isin = %s
            """,
            ("IE00B0000009",),
        ).fetchone()
        assert identity is not None
        assert identity[0] == "cited"
        assert identity[1] is None
        assert identity[2] == "distributing"
        assert identity[3] == "unhedged"
        assert identity[4] == "GBP"
        assert identity[5] is None
        assert identity[6] == "Synthetic umbrella"

        history = conn.execute(
            """
            select effective_on, source_id, source_locator
            from instruments.identifier_history
            where share_class_id = %s and identifier_kind = 'isin'
            """,
            (first.share_class_id,),
        ).fetchone()
        assert history == (
            date(2026, 1, 15),
            "fixture_cited_issuer_document",
            "synthetic://aqil/etf/cited-document",
        )
        assert (
            conn.execute(
                """
            select count(*)
            from instruments.dated_characteristics
            where share_class_id = %s
            """,
                (first.share_class_id,),
            ).fetchone()[0]
            == 0
        )

        cited = _document(
            isin="IE00B0000017",
            umbrella_legal_name="Synthetic umbrella two",
            sub_fund_legal_name="Synthetic sub-fund two",
            source_locator="synthetic://aqil/etf/cited-document-two",
            listings=(CitedListing(mic="XSYN", trading_currency="GBP", ticker="SYN"),),
            characteristics=(
                CitedCharacteristic(
                    code="ter",
                    value_text="synthetic-ter",
                    as_of_date=date(2026, 1, 15),
                ),
            ),
        )
        stored = persist_cited_share_class(conn, cited, _rights())
        codes = conn.execute(
            """
            select characteristic_code, value_text, source_id, source_locator
            from instruments.dated_characteristics
            where share_class_id = %s
            order by characteristic_code
            """,
            (stored.share_class_id,),
        ).fetchall()
        assert codes == [
            (
                "ter",
                "synthetic-ter",
                "fixture_cited_issuer_document",
                "synthetic://aqil/etf/cited-document-two",
            )
        ]
        assert conn.execute(
            """
            select mic, trading_currency, ticker
            from instruments.listings
            where share_class_id = %s
            """,
            (stored.share_class_id,),
        ).fetchone() == ("XSYN", "GBP", "SYN")

        retrieval_only = _document(
            isin="IE00B0000025",
            umbrella_legal_name="Synthetic umbrella three",
            sub_fund_legal_name="Synthetic sub-fund three",
            source_locator="synthetic://aqil/etf/cited-document-three",
            document_date=None,
            retrieved_on=date(2026, 2, 2),
        )
        dated = persist_cited_share_class(conn, retrieval_only, _rights())
        assert dated.document_date is None
        effective = conn.execute(
            """
            select effective_on
            from instruments.identifier_history
            where share_class_id = %s and identifier_kind = 'isin'
            """,
            (dated.share_class_id,),
        ).fetchone()
        assert effective == (date(2026, 2, 2),)
        payload = conn.execute(
            """
            select eligibility, payload
            from instruments.assessments
            where share_class_id = %s
            """,
            (dated.share_class_id,),
        ).fetchone()
        assert payload is not None
        assert payload[0] == "UNKNOWN"
        assert "document_date" not in payload[1]
        assert payload[1]["retrieved_on"] == "2026-02-02"
        assert payload[1]["source_locator"] == "synthetic://aqil/etf/cited-document-three"

        anchor = conn.execute(
            "select count(*) from instruments.share_classes where isin = %s",
            (ANCHOR_ISIN,),
        ).fetchone()
        assert anchor[0] == 0
        assert (
            conn.execute(
                "select to_regclass('forward.etf_instrument_records')",
            ).fetchone()[0]
            is None
        )


def cited_directory_has_json() -> bool:
    directory = REPO_ROOT / "docs" / "sources" / "etf" / "cited"
    return directory.is_dir() and any(directory.glob("*.json"))


def _counts(conn: psycopg.Connection) -> dict[str, int]:
    tables = (
        "instruments.umbrellas",
        "instruments.sub_funds",
        "instruments.share_classes",
        "instruments.listings",
        "instruments.identifier_history",
        "instruments.dated_characteristics",
        "instruments.assessments",
    )
    counts: dict[str, int] = {}
    for table in tables:
        counts[table] = int(conn.execute(f"select count(*) from {table}").fetchone()[0])
    return counts


def _open(url: str) -> psycopg.Connection:
    parsed = urlparse(url)
    database = parsed.path.strip("/")
    if database in PRESERVED or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("refusing a preserved or non-loopback database")
    if database != DISPOSABLE:
        raise RuntimeError(f"refusing database {database}")
    conn = psycopg.connect(url, connect_timeout=5)
    current = conn.execute("select current_database()").fetchone()
    marker = conn.execute("select marker from public.cited_document_test_marker").fetchone()
    if current is None or current[0] != DISPOSABLE or marker is None or marker[0] != MARKER:
        conn.close()
        raise RuntimeError("disposable database identity was not verified")
    return conn


@pytest.fixture(scope="module")
def disposable_url() -> Iterator[str]:
    _drop_disposable()
    try:
        _create_disposable()
        yield DISPOSABLE_URL
    finally:
        _drop_disposable()


def _create_disposable() -> None:
    _psql("template1", f"create database {DISPOSABLE} template template0")
    _psql("template1", f"grant connect on database {DISPOSABLE} to research_worker")
    copied = subprocess.run(
        ["docker", "cp", str(MIGRATION), f"{CONTAINER}:/tmp/aqil_cited_document_instruments.sql"],
        capture_output=True,
        text=True,
        check=False,
    )
    if copied.returncode != 0:
        raise RuntimeError(copied.stderr.strip() or "could not copy the instruments migration")
    applied = subprocess.run(
        [
            "docker",
            "exec",
            CONTAINER,
            "psql",
            "-U",
            "postgres",
            "-d",
            DISPOSABLE,
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            "/tmp/aqil_cited_document_instruments.sql",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if applied.returncode != 0:
        raise RuntimeError(applied.stderr.strip() or applied.stdout)
    _psql(
        DISPOSABLE,
        """
        create table public.cited_document_test_marker (marker text primary key);
        insert into public.cited_document_test_marker (marker)
        values ('disposable-cited-document-test');
        grant select on public.cited_document_test_marker to research_worker;
        """,
    )


def _drop_disposable() -> None:
    _psql(
        "template1",
        f"""
        select pg_terminate_backend(pid)
        from pg_stat_activity
        where datname = '{DISPOSABLE}' and pid <> pg_backend_pid();
        """,
    )
    _psql("template1", f"drop database if exists {DISPOSABLE}")


def _psql(database: str, sql: str) -> str:
    if database in PRESERVED:
        raise RuntimeError(f"refusing psql on preserved database {database}")
    completed = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            CONTAINER,
            "psql",
            "-U",
            "postgres",
            "-d",
            database,
            "-v",
            "ON_ERROR_STOP=1",
            "-tA",
        ],
        input=sql,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"psql failed on {database}")
    return completed.stdout


def test_optional_exposures_are_cited_and_idempotent(
    disposable_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = _document(
        isin="IE00B0000082",
        umbrella_legal_name="Synthetic umbrella exposures",
        sub_fund_legal_name="Synthetic sub-fund exposures",
        source_locator="synthetic://aqil/etf/cited-exposures",
        listings=(CitedListing(mic="XSYN", trading_currency="GBP", ticker="SYN2"),),
        exposures=(
            CitedExposure(
                exposure_kind="geographic",
                exposure_class="Synthetic geography",
                weight=Decimal("0.25"),
                as_of_date=date(2026, 1, 15),
            ),
            CitedExposure(
                exposure_kind="sector",
                exposure_class="Synthetic sector",
                weight=None,
                as_of_date=date(2026, 1, 15),
            ),
        ),
    )
    path = tmp_path / "cited.json"
    path.write_text(document.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(
        "aqil_research.etf.documents.command.load_source_rights",
        lambda: (_rights(),),
    )
    args = argparse.Namespace(document=path, database_url=disposable_url)
    assert run_cite_etf(args) == 0
    assert run_cite_etf(args) == 0
    with _open(disposable_url) as conn:
        rows = conn.execute(
            """
            select exposure_class, weight::text, evidence_status, source_id, source_locator
            from instruments.exposure_snapshots
            where share_class_id = (
              select share_class_id from instruments.share_classes where isin = %s
            )
            order by exposure_class
            """,
            ("IE00B0000082",),
        ).fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "Synthetic geography"
    assert Decimal(str(rows[0][1])) == Decimal("0.25")
    assert rows[0][2:] == (
        "cited",
        "fixture_cited_issuer_document",
        "synthetic://aqil/etf/cited-exposures",
    )
    assert rows[1] == (
        "Synthetic sector",
        None,
        "cited",
        "fixture_cited_issuer_document",
        "synthetic://aqil/etf/cited-exposures",
    )


def test_omitted_exposures_are_not_invented(disposable_url: str) -> None:
    with _open(disposable_url) as conn:
        stored = persist_cited_share_class(
            conn,
            _document(
                isin="IE00B0000090",
                umbrella_legal_name="Synthetic umbrella plain",
                sub_fund_legal_name="Synthetic sub-fund plain",
                source_locator="synthetic://aqil/etf/cited-plain",
            ),
            _rights(),
        )
        count = conn.execute(
            """
            select count(*)
            from instruments.exposure_snapshots
            where share_class_id = %s
            """,
            (stored.share_class_id,),
        ).fetchone()
    assert count is not None
    assert count[0] == 0


def test_trading_currency_is_not_an_exposure() -> None:
    with pytest.raises(ValidationError, match="trading currency"):
        _document(
            listings=(CitedListing(mic="XSYN", trading_currency="GBP", ticker="SYN"),),
            exposures=(
                CitedExposure(
                    exposure_kind="geographic",
                    exposure_class="GBP",
                    as_of_date=date(2026, 1, 15),
                ),
            ),
        )


def test_holdings_files_stay_out_of_the_cited_document() -> None:
    with pytest.raises(ValidationError):
        CitedIssuerDocument.model_validate(
            {
                "source_id": "fixture_cited_issuer_document",
                "source_locator": "synthetic://aqil/etf/cited-document",
                "document_date": "2026-01-15",
                "isin": "IE00B0000009",
                "umbrella_legal_name": "Synthetic umbrella",
                "sub_fund_legal_name": "Synthetic sub-fund",
                "base_currency": "GBP",
                "distribution_policy": "distributing",
                "hedge_status": "unhedged",
                "holdings": [{"name": "Example"}],
            }
        )


def test_cite_etf_refuses_preserved_databases_before_opening_a_document(tmp_path: Path) -> None:
    missing = tmp_path / "absent.json"
    for database in sorted(PRESERVED):
        code = run_cite_etf(
            argparse.Namespace(
                document=missing,
                database_url=f"postgresql://research_worker@127.0.0.1:55432/{database}",
            )
        )
        assert code == 1
    assert not missing.exists()


@pytest.mark.parametrize(
    "source_id",
    ["vanguard_uk_vwra_holdings", "ishares_ucits_holdings"],
)
def test_cite_etf_refuses_prohibited_issuer_rows(
    disposable_url: str,
    tmp_path: Path,
    source_id: str,
) -> None:
    rights = find_source_rights(load_source_rights(), source_id=source_id)
    assert rights is not None
    assert rights.automated_access == RightsDecision.PROHIBITED
    assert rights.redistribution == RightsDecision.PROHIBITED
    isin = "IE00B0000108" if source_id.startswith("vanguard") else "IE00B0000116"
    path = tmp_path / f"{source_id}.json"
    path.write_text(
        _document(
            source_id=source_id,
            source_locator="synthetic://aqil/etf/prohibited-issuer",
            isin=isin,
            founder_supplied=True,
            umbrella_legal_name="Synthetic umbrella refused",
            sub_fund_legal_name="Synthetic sub-fund refused",
        ).model_dump_json(),
        encoding="utf-8",
    )
    assert run_cite_etf(argparse.Namespace(document=path, database_url=disposable_url)) == 1
    with _open(disposable_url) as conn:
        count = conn.execute(
            "select count(*) from instruments.share_classes where isin = %s",
            (isin,),
        ).fetchone()
    assert count is not None
    assert count[0] == 0


def test_cite_issuer_document_refuses_a_missing_rights_row(disposable_url: str) -> None:
    with _open(disposable_url) as conn:
        result = cite_issuer_document(
            conn,
            _document(
                source_id="not_in_the_register",
                isin="IE00B0000124",
                umbrella_legal_name="Synthetic umbrella missing rights",
                sub_fund_legal_name="Synthetic sub-fund missing rights",
                source_locator="synthetic://aqil/etf/missing-rights",
            ),
            (),
        )
    assert result.stored is False
    assert result.refusal == "no rights row for this source_id"
