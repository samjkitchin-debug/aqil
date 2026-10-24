"""Manual macro registration. Synthetic rows stay out of the recorded loader query."""

from __future__ import annotations

from datetime import UTC, datetime

import psycopg
import pytest

from aqil_research.manual.register import (
    register_ai_infrastructure,
    register_publication_recorded,
    register_synthetic_supersession,
    register_ustr_notice,
)
from aqil_research.manual.rights_gate import RegistrationBlocked
from aqil_research.manual.sec_capex import (
    THEME_DOES_NOT_ESTABLISH,
    extract_annual_capex,
    fetch_company_facts,
)
from aqil_research.manual.ustr_notice import fetch_ustr_notice, notice_supports_ustr_claim
from aqil_research.sources.rights import find_source_rights, load_source_rights
from aqil_research.workflow import refresh as refresh_module
from db_guard import open_isolated_test_database

pytestmark = pytest.mark.integration

RETRIEVED_AT = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)

SUPPORTING_NOTICE = """
OFFICE OF THE UNITED STATES TRADE REPRESENTATIVE
Continuation of Actions: China's Acts, Policies, and Practices
Federal Register Volume 91, Number 193 (Wednesday, October 7, 2026)
SUMMARY: In a notice published on May 6, 2026, the Office of the United States
Trade Representative (USTR) announced the first step. The notice informed
representatives of the possible termination. Accordingly, the actions have not
terminated and will remain in effect, subject to possible further modifications,
including any modifications resulting from the statutory four-year review.
DATES: The July 6, 2018 action, as modified, did not terminate on July 6, 2026,
and will remain in effect, subject to possible further modifications.
The August 23, 2018 action, as modified, did not terminate on August 23, 2026,
and will remain in effect, subject to possible modifications.
FOR FURTHER INFORMATION CONTACT: Philip Butler.
Section 301 of the Trade Act of 1974.
"""

UNSUPPORTED_NOTICE = """
SUMMARY: A hearing will be held.
DATES: Comments are due on 1 May 2026.
Office of the United States Trade Representative
China
Section 301
October 7, 2026
"""


def _fact(start: str, end: str, filed: str, value: int, accession: str, form: str = "10-K") -> dict:
    return {
        "start": start,
        "end": end,
        "filed": filed,
        "val": value,
        "accn": accession,
        "fy": int(end[:4]),
        "fp": "FY",
        "form": form,
    }


def _payload(rows: list[dict]) -> dict:
    return {
        "cik": 789019,
        "entityName": "MICROSOFT CORP",
        "facts": {
            "us-gaap": {
                "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": rows}},
            }
        },
    }


@pytest.fixture(scope="module")
def database_url() -> str:
    return open_isolated_test_database()


def test_supporting_notice_is_recognised_and_a_partial_notice_is_not() -> None:
    assert notice_supports_ustr_claim(SUPPORTING_NOTICE)
    assert not notice_supports_ustr_claim(UNSUPPORTED_NOTICE)
    assert "ETF" not in THEME_DOES_NOT_ESTABLISH
    assert "allocation" not in THEME_DOES_NOT_ESTABLISH


def test_govinfo_terms_block_a_new_fetch() -> None:
    rights = find_source_rights(load_source_rights(), source_id="govinfo_federal_register")
    assert rights is not None
    with pytest.raises(RegistrationBlocked, match="automated_access"):
        fetch_ustr_notice(rights)


def test_sec_fetch_stops_when_the_user_agent_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AQIL_SEC_USER_AGENT", raising=False)
    rights = find_source_rights(load_source_rights(), source_id="sec_edgar_company_filings")
    assert rights is not None
    with pytest.raises(RegistrationBlocked, match="AQIL_SEC_USER_AGENT"):
        fetch_company_facts(rights)


def test_two_annual_facts_are_required() -> None:
    rows = [
        _fact("2023-07-01", "2024-06-30", "2024-07-30", 44477000000, "0000789019-24-000012"),
        _fact("2024-07-01", "2025-06-30", "2025-07-30", 64551000000, "0000789019-25-000013"),
        _fact("2025-01-01", "2025-03-31", "2025-04-30", 100, "0000789019-25-000099", form="10-Q"),
    ]
    rows[-1]["fp"] = "Q3"
    pair = extract_annual_capex(_payload(rows))
    assert pair is not None
    newer, older = pair
    assert newer.period_end.isoformat() == "2025-06-30"
    assert older.period_end.isoformat() == "2024-06-30"
    assert newer.unit == older.unit == "USD"
    assert newer.amount == "64551000000"
    assert "sec.gov/Archives/edgar/data/789019/" in newer.filing_url
    assert extract_annual_capex(_payload(rows[:1])) is None


def test_refresh_does_not_register_macro_events() -> None:
    source = refresh_module.__file__
    assert source is not None
    text = open(source, encoding="utf-8").read()
    assert "register-macro" not in text
    assert "register_ustr_notice" not in text
    assert "register_ai_infrastructure" not in text


def test_synthetic_ustr_pathway_is_idempotent_and_hidden(
    database_url: str,
) -> None:
    rights = find_source_rights(load_source_rights(), source_id="govinfo_federal_register")
    assert rights is not None
    with psycopg.connect(database_url) as conn:
        try:
            with pytest.raises(RegistrationBlocked, match="does not support"):
                register_ustr_notice(
                    conn,
                    body=UNSUPPORTED_NOTICE,
                    rights=rights,
                    record_class="synthetic_fixture",
                    retrieved_at=RETRIEVED_AT,
                    fetch_performed=False,
                )
            first = register_ustr_notice(
                conn,
                body=SUPPORTING_NOTICE,
                rights=rights,
                record_class="synthetic_fixture",
                retrieved_at=RETRIEVED_AT,
                fetch_performed=False,
            )
            second = register_ustr_notice(
                conn,
                body=SUPPORTING_NOTICE,
                rights=rights,
                record_class="synthetic_fixture",
                retrieved_at=RETRIEVED_AT,
                fetch_performed=False,
            )
            assert first.outcome == "recorded"
            assert second.outcome == "unchanged"
            recorded = conn.execute(
                """
                select count(*) from research.macro_events
                where event_key = %s and record_class = 'recorded'
                """,
                (first.detail,),
            ).fetchone()
            assert recorded is not None and recorded[0] == 0
            hidden = conn.execute(
                """
                select count(*) from research.macro_events
                where record_class = 'recorded'
                """
            ).fetchone()
            assert hidden is not None and hidden[0] == 0
        finally:
            conn.rollback()


def test_publication_record_does_not_say_policy_changed(database_url: str) -> None:
    with psycopg.connect(database_url) as conn:
        try:
            with pytest.raises(RegistrationBlocked, match="sourced update is stored"):
                register_publication_recorded(conn, record_class="synthetic_fixture")
            conn.rollback()
            retrieval = conn.execute(
                """
                insert into research.source_retrievals (
                  source_id, dataset_id, rights_record_id, provider_id,
                  adapter_id, adapter_version, retrieved_at, collection_mode, endpoint_host
                ) values (
                  'federal_reserve_monetary_press', 'fed.press.monetary',
                  'federal_reserve_monetary_press', 'federal_reserve',
                  'fed_press', '1', %s, 'fixture', 'www.federalreserve.gov'
                )
                returning retrieval_id
                """,
                (RETRIEVED_AT,),
            ).fetchone()
            assert retrieval is not None
            conn.execute(
                """
                insert into research.sourced_updates (
                  source_id, title, canonical_url, published_at, retrieved_at,
                  retrieval_id, content_hash
                ) values (
                  'federal_reserve_monetary_press',
                  'Federal Reserve issues FOMC statement',
                  'https://www.federalreserve.gov/newsevents/pressreleases/monetary20261001a.htm',
                  %s, %s, %s, %s
                )
                """,
                (
                    datetime(2026, 10, 1, 18, 0, tzinfo=UTC),
                    RETRIEVED_AT,
                    retrieval[0],
                    "d" * 64,
                ),
            )
            result = register_publication_recorded(conn, record_class="synthetic_fixture")
            row = conn.execute(
                """
                select summary, claim_scope, surface_on_today, record_class
                from research.macro_events
                where event_key = %s
                """,
                (result.detail,),
            ).fetchone()
            assert row is not None
            summary, scope, surface, record_class = row
            assert "published" in summary.lower()
            assert "policy changed" not in summary.lower()
            assert scope == "publication_recorded"
            assert surface is False
            assert record_class == "synthetic_fixture"
        finally:
            conn.rollback()


def test_theme_supersession_keeps_the_prior_row(database_url: str) -> None:
    rights = find_source_rights(load_source_rights(), source_id="sec_edgar_company_filings")
    assert rights is not None
    payload = _payload(
        [
            _fact("2023-07-01", "2024-06-30", "2024-07-30", 10, "0000789019-24-000012"),
            _fact("2024-07-01", "2025-06-30", "2025-07-30", 12, "0000789019-25-000013"),
        ]
    )
    with psycopg.connect(database_url) as conn:
        try:
            with pytest.raises(RegistrationBlocked, match="two comparable"):
                register_ai_infrastructure(
                    conn,
                    payload=_payload(
                        payload["facts"]["us-gaap"]["PaymentsToAcquirePropertyPlantAndEquipment"][
                            "units"
                        ]["USD"][:1]
                        and [
                            _fact(
                                "2024-07-01",
                                "2025-06-30",
                                "2025-07-30",
                                12,
                                "0000789019-25-000013",
                            )
                        ]
                    ),
                    rights=rights,
                    record_class="synthetic_fixture",
                    retrieved_at=RETRIEVED_AT,
                    fetch_performed=False,
                )
            conn.rollback()
            stored = register_ai_infrastructure(
                conn,
                payload=payload,
                rights=rights,
                record_class="synthetic_fixture",
                retrieved_at=RETRIEVED_AT,
                fetch_performed=False,
            )
            again = register_ai_infrastructure(
                conn,
                payload=payload,
                rights=rights,
                record_class="synthetic_fixture",
                retrieved_at=RETRIEVED_AT,
                fetch_performed=False,
            )
            assert stored.outcome == "recorded"
            assert again.outcome == "unchanged"
            supersession = register_synthetic_supersession(conn)
            kept = conn.execute(
                """
                select count(*) from research.theme_assessments
                where assessment_id = %s::uuid
                   or supersedes_assessment_id = %s::uuid
                """,
                (supersession.detail, supersession.detail),
            ).fetchone()
            assert kept is not None and kept[0] == 2
            visible = conn.execute(
                """
                select count(*) from research.theme_assessments
                where record_class = 'recorded'
                """
            ).fetchone()
            assert visible is not None and visible[0] == 0
            text = conn.execute(
                """
                select real_economy_activity from research.theme_assessments
                where assessment_id = %s::uuid
                """,
                (stored.detail,),
            ).fetchone()
            assert text is not None
            assert THEME_DOES_NOT_ESTABLISH in text[0]
            assert "AI-only spending" in text[0]
        finally:
            conn.rollback()
