"""Manual registration command. This is not added to research refresh."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from aqil_research.manual.register import (
    register_ai_infrastructure,
    register_publication_recorded,
    register_ustr_notice,
)
from aqil_research.manual.rights_gate import RegistrationBlocked
from aqil_research.manual.sec_capex import fetch_company_facts
from aqil_research.manual.ustr_notice import fetch_ustr_notice
from aqil_research.persistence.connection import research_connection
from aqil_research.sources.rights import find_source_rights, load_source_rights


def register_macro_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "register-macro",
        help="Manually register one macro event or theme. Not part of refresh.",
    )
    parser.add_argument(
        "--record",
        required=True,
        choices=("ustr-notice", "central-bank-publication", "ai-infrastructure"),
    )


def run_register_macro(args: argparse.Namespace) -> int:
    try:
        with research_connection() as conn:
            result = _run(conn, args.record)
    except RegistrationBlocked as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2
    print(f"{result.outcome} {result.detail}")
    return 0


def _run(conn, record: str):
    rights = load_source_rights()
    now = datetime.now(tz=UTC)
    if record == "ustr-notice":
        source = find_source_rights(rights, source_id="govinfo_federal_register")
        if source is None:
            raise RegistrationBlocked("govinfo_federal_register is not in the rights register")
        body = fetch_ustr_notice(source)
        return register_ustr_notice(
            conn,
            body=body,
            rights=source,
            record_class="recorded",
            retrieved_at=now,
            fetch_performed=True,
        )
    if record == "central-bank-publication":
        return register_publication_recorded(conn, record_class="recorded", rights_records=rights)
    if record == "ai-infrastructure":
        source = find_source_rights(rights, source_id="sec_edgar_company_filings")
        if source is None:
            raise RegistrationBlocked("sec_edgar_company_filings is not in the rights register")
        payload = fetch_company_facts(source)
        return register_ai_infrastructure(
            conn,
            payload=payload,
            rights=source,
            record_class="recorded",
            retrieved_at=now,
            fetch_performed=True,
        )
    raise RegistrationBlocked(f"unknown record {record}")
