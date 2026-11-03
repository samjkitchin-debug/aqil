"""Recompute the frozen pilot and compare it with the stored artifact."""

from __future__ import annotations

import psycopg

from aqil_research.long_horizon.documents import pilot_artifact
from aqil_research.long_horizon.money import sha256_document
from aqil_research.long_horizon.pilot import (
    LOCAL_ETF_URL,
    LOCAL_RESEARCH_URL,
    PilotError,
    assert_loopback,
    load_listing_prices,
    package_code_hash,
    run_frozen_comparison,
)
from aqil_research.long_horizon.spec import frozen_specification_hash


def reproduce() -> dict[str, str]:
    assert_loopback(LOCAL_RESEARCH_URL, "postgres")
    assert_loopback(LOCAL_ETF_URL, "aqil_etf")
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        research.read_only = True
        with research.cursor() as cursor:
            cursor.execute("select current_database()")
            if cursor.fetchone()[0] != "postgres":
                raise PilotError("reproduction reads database postgres")
            cursor.execute(
                """
                select e.artifact_sha256, e.code_hash, e.validation_status,
                       e.publication_allowed, s.specification_hash, ev.content_sha256,
                       c.status
                from research.experiment_executions e
                join research.experiment_specifications s
                  on s.experiment_id = e.experiment_id
                 and s.version = e.experiment_version
                join research.evidence_records ev
                  on ev.execution_id = e.execution_id
                join research.current_scientific_status c
                  on c.subject_kind = 'claim' and c.subject_id = 'LH-C-001'
                where e.execution_id = 'LH-X-001'
                  and ev.evidence_id = 'LH-V-001'
                """
            )
            row = cursor.fetchone()
    if row is None:
        raise PilotError("LH-X-001 is not stored")
    (
        artifact_sha256,
        code_hash,
        validation_status,
        publication_allowed,
        specification_hash,
        evidence_sha256,
        current_status,
    ) = row
    if publication_allowed:
        raise PilotError("publication_allowed must stay false")
    if specification_hash != frozen_specification_hash():
        raise PilotError("stored specification hash does not match the frozen code")
    if code_hash != package_code_hash():
        raise PilotError("stored code hash does not match the current package")
    if artifact_sha256 != evidence_sha256:
        raise PilotError("execution artifact hash does not match the evidence row")
    if validation_status != current_status:
        raise PilotError("claim status and execution validation status differ")
    with psycopg.connect(LOCAL_ETF_URL) as etf:
        prices, combined_hash, _symbol_hashes = load_listing_prices(etf)
    _sessions, _contributions, passive, alternative, status = run_frozen_comparison(prices)
    recomputed = sha256_document(
        pilot_artifact(
            specification_hash=specification_hash,
            price_series_sha256=combined_hash,
            status=status,
            passive=passive,
            alternative=alternative,
        )
    )
    if recomputed != artifact_sha256 or status != validation_status:
        raise PilotError("recomputed artifact does not match the stored evidence")
    return {
        "execution_id": "LH-X-001",
        "status": status,
        "artifact_sha256": recomputed,
        "passive_terminal_wealth": str(passive.terminal_wealth),
        "alternative_terminal_wealth": str(alternative.terminal_wealth),
    }


def main() -> None:
    result = reproduce()
    print(
        f"reproduced {result['execution_id']} status {result['status']} "
        f"artifact {result['artifact_sha256']}"
    )


if __name__ == "__main__":
    main()
