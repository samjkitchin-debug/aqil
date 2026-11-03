"""Recompute the stored inventory and intersection. Does not write."""

from __future__ import annotations

from dataclasses import replace

import psycopg

from aqil_research.long_horizon.events.compute import analyse
from aqil_research.long_horizon.events.definition import (
    MACRO_EXECUTION_ID,
    PILOT_EXECUTION_ID,
)
from aqil_research.long_horizon.events.package_hash import events_code_hash
from aqil_research.long_horizon.events.scan import load_macro, load_prices
from aqil_research.long_horizon.money import sha256_document
from aqil_research.long_horizon.pilot import (
    LOCAL_ETF_URL,
    LOCAL_RESEARCH_URL,
    PilotError,
    assert_loopback,
)
from aqil_research.long_horizon.reproduce import reproduce as reproduce_original


def reproduce_outcome() -> dict[str, str]:
    assert_loopback(LOCAL_RESEARCH_URL, "postgres")
    assert_loopback(LOCAL_ETF_URL, "aqil_etf")
    with psycopg.connect(LOCAL_ETF_URL) as etf:
        listings, hashes, fx_count, distribution_tables = load_prices(etf)
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        research.read_only = True
        facts = replace(
            load_macro(research),
            fx_count=fx_count,
            distribution_tables=distribution_tables,
        )
        analysis = analyse(listings, hashes, facts)
        artifact_hash = sha256_document(analysis.artifact)
        with research.cursor() as cursor:
            cursor.execute("select current_database()")
            if cursor.fetchone()[0] != "postgres":
                raise PilotError("reproduction reads database postgres")
            cursor.execute(
                """
                select e.artifact_sha256, e.code_hash, e.validation_status, e.state,
                       e.publication_allowed, ev.content_sha256, c.status
                from research.experiment_executions e
                join research.evidence_records ev on ev.execution_id = e.execution_id
                join research.current_scientific_status c
                  on c.subject_kind = 'claim' and c.subject_id = 'LH-C-002'
                where e.execution_id = %s and ev.evidence_id = 'LH-V-002'
                """,
                (PILOT_EXECUTION_ID,),
            )
            pilot = cursor.fetchone()
            cursor.execute(
                """
                select e.state, e.validation_status, e.artifact_sha256, e.publication_allowed,
                       c.status
                from research.experiment_executions e
                join research.current_scientific_status c
                  on c.subject_kind = 'claim' and c.subject_id = 'LH-C-003'
                where e.execution_id = %s
                """,
                (MACRO_EXECUTION_ID,),
            )
            macro = cursor.fetchone()
            cursor.execute(
                """
                select event_id, price_return, start_date::text, end_date::text
                from research.market_events
                where definition_id = 'EVT-DEF-001'
                order by event_id
                """
            )
            stored_events = cursor.fetchall()
            cursor.execute(
                """
                select count(*) from research.market_events
                where usable_as_investment_signal or publication_allowed
                """
            )
            promoted = int(cursor.fetchone()[0])
            cursor.execute(
                """
                select count(*) from research.comparison_periods
                where selected_on_future_return or publication_allowed
                """
            )
            selected = int(cursor.fetchone()[0])
    if pilot is None or macro is None:
        raise PilotError("the outcome-first executions are not stored")
    (
        stored_hash,
        stored_code,
        validation_status,
        state,
        published,
        evidence_hash,
        claim_status,
    ) = pilot
    if published or state != "succeeded":
        raise PilotError("the pilot execution is not an unpublished succeeded record")
    if stored_hash != evidence_hash or stored_hash != artifact_hash:
        raise PilotError("recomputed intersection does not match the stored evidence")
    if validation_status != claim_status or claim_status != analysis.artifact["status"]:
        raise PilotError("claim status and recomputed status differ")
    if claim_status in {"statistically_supported", "economically_useful", "forward_validated"}:
        raise PilotError("category C was promoted")
    if stored_code != events_code_hash():
        raise PilotError("stored event code hash does not match the package")
    recomputed_events = [
        (
            event.event_id,
            event.price_return,
            event.start_date.isoformat(),
            event.end_date.isoformat(),
        )
        for event in analysis.events
    ]
    if stored_events != recomputed_events:
        raise PilotError("stored price events do not match the recomputed catalogue")
    if promoted or selected:
        raise PilotError("a row was marked as a signal or as selected on the later return")
    macro_state, macro_validation, _macro_hash, macro_published, macro_status = macro
    if macro_published or macro_state != "blocked" or macro_validation != "retrospective_only":
        raise PilotError("the macro execution is not a blocked retrospective record")
    if macro_status != "retrospective_only":
        raise PilotError("the macro claim was promoted")
    original = reproduce_original()
    if original["execution_id"] != "LH-X-001" or original["status"] != "inconclusive":
        raise PilotError("LH-X-001 did not reproduce as inconclusive")
    return {
        "execution_id": PILOT_EXECUTION_ID,
        "status": str(claim_status),
        "event_count": str(len(analysis.events)),
        "comparison_count": str(len(analysis.decisions)),
        "macro_execution_id": MACRO_EXECUTION_ID,
        "macro_state": macro_state,
        "original_execution_id": original["execution_id"],
        "original_status": original["status"],
    }


def main() -> None:
    result = reproduce_outcome()
    print(
        f"reproduced {result['execution_id']} status {result['status']} "
        f"events {result['event_count']}"
    )


if __name__ == "__main__":
    main()
