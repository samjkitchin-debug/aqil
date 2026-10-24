"""Thin cite command. Rights stay on the existing register."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from pydantic import ValidationError

from aqil_research.etf.documents.ingest import (
    PRESERVED_DATABASES,
    CitedIssuerDocument,
    PersistResult,
    persist_cited_share_class,
)
from aqil_research.sources.rights import SourceRightsRecord, find_source_rights, load_source_rights


def register_cite_etf_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "cite-etf",
        help=(
            "Store one cited issuer document when acquire, retain, extract, "
            "and display are already permitted."
        ),
    )
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument(
        "--database-url",
        required=True,
        help="Instruments database. postgres and aqil_etf are refused.",
    )


def cite_issuer_document(
    conn: psycopg.Connection,
    document: CitedIssuerDocument,
    records: tuple[SourceRightsRecord, ...],
) -> PersistResult:
    """Find the rights row, then call the existing persist function."""
    rights = find_source_rights(records, source_id=document.source_id)
    if rights is None:
        return PersistResult(
            stored=False,
            created=False,
            refusal="no rights row for this source_id",
            document_date=document.document_date,
            retrieved_on=document.retrieved_on,
            founder_supplied=document.founder_supplied,
        )
    return persist_cited_share_class(conn, document, rights)


def run_cite_etf(args: argparse.Namespace) -> int:
    database = urlparse(str(args.database_url)).path.strip("/")
    if database in PRESERVED_DATABASES:
        print(
            f"refusing to persist a share class on preserved database {database}",
            file=sys.stderr,
        )
        return 1
    payload = json.loads(Path(args.document).read_text(encoding="utf-8"))
    try:
        document = CitedIssuerDocument.model_validate(payload)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    with psycopg.connect(str(args.database_url), connect_timeout=5) as conn:
        result = cite_issuer_document(conn, document, load_source_rights())
    if result.refusal or not result.stored:
        print(result.refusal or "cited document was not stored", file=sys.stderr)
        return 1
    print("stored")
    return 0
