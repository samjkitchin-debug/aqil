"""Persist one instruments share class from a cited issuer document.

Acquisition, retention, extraction, and display are separate rights uses.
``founder_supplied`` does not permit any of them. Unknown and prohibited stay
refused by ``source_usable``. Omitted facts are not invented. The internal
forward fixture is not an issuer document.

No cited document is in the repository. ``apply_repository_documents`` therefore
inserts nothing. The first insert needs the file and rights row described by
``FIRST_INSERT_REQUIREMENT``.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Literal

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aqil_research.etf.contracts import DistributionPolicy, HedgeStatus
from aqil_research.etf.identity.catalogue import ANCHOR_SOURCE_ID, ANCHOR_SOURCE_LOCATOR
from aqil_research.etf.vetting import EvidenceInput, assess_quality
from aqil_research.sources.rights import (
    OperationalStatus,
    RightsOperation,
    SourceRightsRecord,
    find_source_rights,
    load_source_rights,
    source_usable,
)

FIRST_INSERT_REQUIREMENT = (
    "A first share-class insert needs one cited issuer document at "
    "docs/sources/etf/cited/*.json and a rights row with the same source_id. "
    "The document must include source_id, source_locator, and a document_date "
    "or retrieved_on, plus isin, umbrella_legal_name, sub_fund_legal_name, "
    "base_currency, distribution_policy, and hedge_status. Omitted fields stay "
    "absent. founder_supplied does not permit acquire, retain, extract, or "
    "display. The rights row must have operational_status enabled, and "
    "automated_access (acquire), raw_data_retention (retain), "
    "internal_computation (extract), and redistribution (display) must each be "
    "permitted. Unknown and prohibited each refuse that use. Do not change an "
    "unknown or prohibited cell in docs/sources/SOURCE_RIGHTS.csv to permitted. "
    "The internal fixture apps/web/fixtures/forward-horizon.v1.json is not that "
    "document. Share classes resolve on instruments.share_classes by ISIN."
)

PRESERVED_DATABASES = frozenset({"postgres", "aqil_etf"})

_REQUIRED_FIELDS = (
    "isin",
    "umbrella_legal_name",
    "sub_fund_legal_name",
    "base_currency",
    "distribution_policy",
    "hedge_status",
)

_USES: tuple[tuple[Literal["acquire", "retain", "extract", "display"], RightsOperation], ...] = (
    ("acquire", RightsOperation.AUTOMATED_ACCESS),
    ("retain", RightsOperation.RAW_DATA_RETENTION),
    ("extract", RightsOperation.INTERNAL_COMPUTATION),
    ("display", RightsOperation.REDISTRIBUTION),
)

UseName = Literal["acquire", "retain", "extract", "display"]


class DocumentIngestError(Exception):
    """Raised when a write must not proceed."""


class CitedListing(BaseModel):
    """One cited listing. Trading currency stays on the listing."""

    model_config = ConfigDict(extra="forbid")

    mic: str = Field(pattern=r"^[A-Z0-9]{4}$")
    trading_currency: str = Field(pattern=r"^[A-Z]{3}$")
    ticker: str = Field(min_length=1)


class CitedCharacteristic(BaseModel):
    """One cited fact. An omitted fact is absent from this list."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    value_text: str = Field(min_length=1)
    unit: str | None = None
    as_of_date: date


class CitedIssuerDocument(BaseModel):
    """Facts taken from one issuer document. Blank optional fields stay absent."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    document_date: date | None = None
    retrieved_on: date | None = None
    founder_supplied: bool = False
    isin: str | None = None
    umbrella_legal_name: str | None = None
    domicile_iso2: str | None = None
    sub_fund_legal_name: str | None = None
    base_currency: str | None = None
    distribution_policy: DistributionPolicy | None = None
    hedge_status: HedgeStatus | None = None
    inception_date: date | None = None
    listings: tuple[CitedListing, ...] = ()
    characteristics: tuple[CitedCharacteristic, ...] = ()

    @field_validator("source_id", "source_locator")
    @classmethod
    def strip_identity(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("source identity is required")
        return stripped

    @field_validator(
        "isin",
        "umbrella_legal_name",
        "domicile_iso2",
        "sub_fund_legal_name",
        "base_currency",
        mode="before",
    )
    @classmethod
    def blank_is_absent(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def require_a_date_and_a_real_isin(self) -> CitedIssuerDocument:
        if self.document_date is None and self.retrieved_on is None:
            raise ValueError("a document date or a retrieval date is required")
        if self.isin is not None and re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", self.isin) is None:
            raise ValueError("isin is not a share-class ISIN")
        if self.base_currency is not None and re.fullmatch(r"[A-Z]{3}", self.base_currency) is None:
            raise ValueError("base currency must be three letters")
        if self.domicile_iso2 is not None and re.fullmatch(r"[A-Z]{2}", self.domicile_iso2) is None:
            raise ValueError("domicile must be two letters")
        return self


class UseDecision(BaseModel):
    """One use, judged on its own by the existing rights register."""

    model_config = ConfigDict(extra="forbid")

    use: UseName
    operation: str
    decision: str
    enabled: bool
    permitted: bool


class PersistResult(BaseModel):
    """Outcome of one document. ``created`` is false when the ISIN is already stored."""

    model_config = ConfigDict(extra="forbid")

    stored: bool
    created: bool
    share_class_id: str | None = None
    blocked_uses: tuple[str, ...] = ()
    use_decisions: tuple[UseDecision, ...] = ()
    absent_fields: tuple[str, ...] = ()
    eligibility: str | None = None
    founder_supplied: bool = False
    refusal: str | None = None
    document_date: date | None = None
    retrieved_on: date | None = None


class RepositoryIngestResult(BaseModel):
    """Repository scan. An empty cited directory inserts nothing."""

    model_config = ConfigDict(extra="forbid")

    documents_found: int
    inserted: int
    requirement: str


def cited_document_directory() -> Path:
    """Directory for authorised issuer documents. It is absent until one exists."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "sources" / "etf"
        if candidate.is_dir():
            return candidate / "cited"
    raise DocumentIngestError("ETF source directory was not found")


def load_repository_documents() -> tuple[CitedIssuerDocument, ...]:
    """Load cited JSON documents. A missing directory is an empty result."""
    directory = cited_document_directory()
    if not directory.is_dir():
        return ()
    documents: list[CitedIssuerDocument] = []
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        documents.append(CitedIssuerDocument.model_validate(payload))
    return tuple(documents)


def apply_repository_documents(conn: psycopg.Connection) -> RepositoryIngestResult:
    """Insert cited repository documents. With none on file, do not write."""
    documents = load_repository_documents()
    if not documents:
        return RepositoryIngestResult(
            documents_found=0,
            inserted=0,
            requirement=FIRST_INSERT_REQUIREMENT,
        )
    records = list(load_source_rights())
    fragments = cited_document_directory().parent / "fragments"
    if fragments.is_dir():
        for path in sorted(fragments.glob("*.csv")):
            records.extend(load_source_rights(path))
    inserted = 0
    for document in documents:
        rights = find_source_rights(tuple(records), source_id=document.source_id)
        if rights is None:
            continue
        result = persist_cited_share_class(conn, document, rights)
        if result.created:
            inserted += 1
    return RepositoryIngestResult(
        documents_found=len(documents),
        inserted=inserted,
        requirement=FIRST_INSERT_REQUIREMENT,
    )


def persist_cited_share_class(
    conn: psycopg.Connection,
    document: CitedIssuerDocument,
    rights: SourceRightsRecord,
) -> PersistResult:
    """Store one share class when every required use is permitted.

    The connection is not used until the document, the fixture check, and the
    four rights uses have already passed. ``postgres`` and ``aqil_etf`` are
    refused so this slice cannot write the preserved databases.
    """
    founder_supplied = document.founder_supplied
    dates = {
        "document_date": document.document_date,
        "retrieved_on": document.retrieved_on,
        "founder_supplied": founder_supplied,
    }
    refusal = _fixture_refusal(document)
    if refusal is not None:
        return PersistResult(stored=False, created=False, refusal=refusal, **dates)

    decisions = _use_decisions(rights)
    blocked = tuple(item.use for item in decisions if not item.permitted)
    if rights.source_id != document.source_id:
        return PersistResult(
            stored=False,
            created=False,
            blocked_uses=blocked,
            use_decisions=decisions,
            refusal="source_id does not match the rights row",
            **dates,
        )
    absent = _absent_fields(document)
    if blocked or absent:
        return PersistResult(
            stored=False,
            created=False,
            blocked_uses=blocked,
            use_decisions=decisions,
            absent_fields=absent,
            refusal="rights or cited fields do not allow an insert",
            **dates,
        )

    _refuse_preserved_database(conn)
    with conn.transaction():
        existing = _share_class_id(conn, document.isin or "")
        created = existing is None
        share_class_id = existing or _insert_share_class(conn, document)
        _ensure_provenance(conn, share_class_id, document)
        eligibility = _ensure_assessment(conn, share_class_id, document)
    return PersistResult(
        stored=True,
        created=created,
        share_class_id=share_class_id,
        use_decisions=decisions,
        eligibility=eligibility,
        **dates,
    )


def _use_decisions(rights: SourceRightsRecord) -> tuple[UseDecision, ...]:
    enabled = rights.operational_status == OperationalStatus.ENABLED
    return tuple(
        UseDecision(
            use=use,
            operation=operation.value,
            decision=rights.decision_for(operation).value,
            enabled=enabled,
            permitted=source_usable(rights, operation),
        )
        for use, operation in _USES
    )


def _fixture_refusal(document: CitedIssuerDocument) -> str | None:
    locator = document.source_locator
    if document.source_id == ANCHOR_SOURCE_ID or locator == ANCHOR_SOURCE_LOCATOR:
        return "the internal fixture is not a permitted issuer document"
    if "forward.etf" in locator or "forward-horizon" in locator:
        return "forward fixture rows are not issuer documents"
    return None


def _absent_fields(document: CitedIssuerDocument) -> tuple[str, ...]:
    absent: list[str] = []
    for name in _REQUIRED_FIELDS:
        value = getattr(document, name)
        if value is None or (isinstance(value, str) and not value.strip()):
            absent.append(name)
    return tuple(absent)


def _refuse_preserved_database(conn: psycopg.Connection) -> None:
    row = conn.execute("select current_database()").fetchone()
    name = "" if row is None else str(row[0])
    if name in PRESERVED_DATABASES:
        raise DocumentIngestError(
            f"refusing to persist a share class on preserved database {name}",
        )


def _effective_on(document: CitedIssuerDocument) -> date:
    if document.document_date is not None:
        return document.document_date
    if document.retrieved_on is not None:
        return document.retrieved_on
    raise DocumentIngestError("a document date or a retrieval date is required")


def _share_class_id(conn: psycopg.Connection, isin: str) -> str | None:
    row = conn.execute(
        "select share_class_id::text from instruments.share_classes where isin = %s",
        (isin,),
    ).fetchone()
    if row is None:
        return None
    return str(row[0])


def _insert_share_class(conn: psycopg.Connection, document: CitedIssuerDocument) -> str:
    umbrella = conn.execute(
        """
        insert into instruments.umbrellas (legal_name, domicile_iso2)
        values (%s, %s)
        returning umbrella_id::text
        """,
        (document.umbrella_legal_name, document.domicile_iso2),
    ).fetchone()
    sub_fund = conn.execute(
        """
        insert into instruments.sub_funds (umbrella_id, legal_name, base_currency)
        values (%s, %s, %s)
        returning sub_fund_id::text
        """,
        (umbrella[0], document.sub_fund_legal_name, document.base_currency),
    ).fetchone()
    created = conn.execute(
        """
        insert into instruments.share_classes (
          sub_fund_id, isin, distribution_policy, hedge_status, inception_date, evidence_status
        )
        values (%s, %s, %s, %s, %s, 'cited')
        on conflict (isin) do nothing
        returning share_class_id::text
        """,
        (
            sub_fund[0],
            document.isin,
            document.distribution_policy,
            document.hedge_status,
            document.inception_date,
        ),
    ).fetchone()
    if created is not None:
        return str(created[0])
    existing = _share_class_id(conn, document.isin or "")
    if existing is None:
        raise DocumentIngestError("share class insert did not resolve an ISIN")
    return existing


def _ensure_provenance(
    conn: psycopg.Connection,
    share_class_id: str,
    document: CitedIssuerDocument,
) -> None:
    effective_on = _effective_on(document)
    _insert_identifier(
        conn,
        share_class_id,
        None,
        "isin",
        document.isin or "",
        effective_on,
        document,
    )
    for listing in document.listings:
        listing_id = _insert_listing(conn, share_class_id, listing)
        _insert_identifier(
            conn,
            share_class_id,
            listing_id,
            "ticker",
            listing.ticker,
            effective_on,
            document,
        )
        _insert_identifier(
            conn,
            share_class_id,
            listing_id,
            "mic",
            listing.mic,
            effective_on,
            document,
        )
    for fact in document.characteristics:
        _insert_characteristic(conn, share_class_id, fact, document)


def _insert_listing(
    conn: psycopg.Connection,
    share_class_id: str,
    listing: CitedListing,
) -> str:
    row = conn.execute(
        """
        insert into instruments.listings (share_class_id, mic, trading_currency, ticker)
        values (%s, %s, %s, %s)
        on conflict (share_class_id, mic, trading_currency, ticker) do nothing
        returning listing_id::text
        """,
        (share_class_id, listing.mic, listing.trading_currency, listing.ticker),
    ).fetchone()
    if row is not None:
        return str(row[0])
    found = conn.execute(
        """
        select listing_id::text
        from instruments.listings
        where share_class_id = %s and mic = %s and trading_currency = %s and ticker = %s
        """,
        (share_class_id, listing.mic, listing.trading_currency, listing.ticker),
    ).fetchone()
    if found is None:
        raise DocumentIngestError("listing insert did not resolve")
    return str(found[0])


def _insert_identifier(
    conn: psycopg.Connection,
    share_class_id: str,
    listing_id: str | None,
    kind: str,
    value: str,
    effective_on: date,
    document: CitedIssuerDocument,
) -> None:
    exists = conn.execute(
        """
        select 1
        from instruments.identifier_history
        where share_class_id = %s
          and identifier_kind = %s
          and identifier_value = %s
          and effective_on = %s
          and source_id = %s
          and source_locator = %s
          and listing_id is not distinct from %s
        """,
        (
            share_class_id,
            kind,
            value,
            effective_on,
            document.source_id,
            document.source_locator,
            listing_id,
        ),
    ).fetchone()
    if exists is not None:
        return
    conn.execute(
        """
        insert into instruments.identifier_history (
          share_class_id, listing_id, identifier_kind, identifier_value,
          effective_on, source_id, source_locator
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            share_class_id,
            listing_id,
            kind,
            value,
            effective_on,
            document.source_id,
            document.source_locator,
        ),
    )


def _insert_characteristic(
    conn: psycopg.Connection,
    share_class_id: str,
    fact: CitedCharacteristic,
    document: CitedIssuerDocument,
) -> None:
    exists = conn.execute(
        """
        select 1
        from instruments.dated_characteristics
        where share_class_id = %s
          and as_of_date = %s
          and characteristic_code = %s
          and value_text = %s
          and availability = 'cited'
          and source_id = %s
          and source_locator = %s
        """,
        (
            share_class_id,
            fact.as_of_date,
            fact.code,
            fact.value_text,
            document.source_id,
            document.source_locator,
        ),
    ).fetchone()
    if exists is not None:
        return
    conn.execute(
        """
        insert into instruments.dated_characteristics (
          share_class_id, as_of_date, characteristic_code, value_text, unit,
          availability, source_id, source_locator
        )
        values (%s, %s, %s, %s, %s, 'cited', %s, %s)
        """,
        (
            share_class_id,
            fact.as_of_date,
            fact.code,
            fact.value_text,
            fact.unit,
            document.source_id,
            document.source_locator,
        ),
    )


def _citation_payload(document: CitedIssuerDocument) -> dict[str, str]:
    payload = {"source_locator": document.source_locator}
    if document.document_date is not None:
        payload["document_date"] = document.document_date.isoformat()
    if document.retrieved_on is not None:
        payload["retrieved_on"] = document.retrieved_on.isoformat()
    return payload


def _ensure_assessment(
    conn: psycopg.Connection,
    share_class_id: str,
    document: CitedIssuerDocument,
) -> str:
    """Record the existing eligibility gate. Missing hard evidence stays unknown."""
    cost_codes = {fact.code for fact in document.characteristics}
    quality = assess_quality(
        EvidenceInput(
            isin=document.isin,
            identity_cited=True,
            structure_cited=False,
            cost_cited="ter" in cost_codes and "tracking_difference" in cost_codes,
            benchmark_cited=False,
            holdings_rights="unknown",
            scale_cited=False,
            performance_cited=False,
        ),
    )
    if quality.eligibility == "UNKNOWN":
        statement = "Missing hard evidence stays unknown. There is no rank."
    else:
        statement = f"Eligibility is {quality.eligibility} under the existing evidence gate."
    payload = _citation_payload(document)
    exists = conn.execute(
        """
        select 1
        from instruments.assessments
        where share_class_id = %s
          and eligibility = %s
          and evidence_status = %s
          and statement = %s
          and source_id = %s
          and payload = %s
        """,
        (
            share_class_id,
            quality.eligibility,
            quality.evidence_status,
            statement,
            document.source_id,
            Jsonb(payload),
        ),
    ).fetchone()
    if exists is None:
        conn.execute(
            """
            insert into instruments.assessments (
              share_class_id, eligibility, evidence_status, statement, source_id, payload
            )
            values (%s, %s, %s, %s, %s, %s)
            """,
            (
                share_class_id,
                quality.eligibility,
                quality.evidence_status,
                statement,
                document.source_id,
                Jsonb(payload),
            ),
        )
    return quality.eligibility
