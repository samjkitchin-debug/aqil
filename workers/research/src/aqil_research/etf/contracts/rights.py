"""Fail-closed rights gate for ETF collection.

A fragment is one REGISTER_COLUMNS row. Prohibited and unknown automated
access both refuse collection. This module does not download provider files.
"""

from __future__ import annotations

from pathlib import Path

from aqil_research.sources.rights import (
    OperationalStatus,
    RightsDecision,
    SourceRightsRecord,
    load_source_rights,
)


class EtfRightsError(Exception):
    """Raised when an ETF source is not cleared for the requested use."""


def load_etf_rights_fragment(path: Path) -> SourceRightsRecord:
    """Load one fragment. The file must already match REGISTER_COLUMNS."""
    records = load_source_rights(path)
    if len(records) != 1:
        raise EtfRightsError(f"{path} must contain exactly one source row")
    return records[0]


def assert_automated_collection_allowed(record: SourceRightsRecord) -> None:
    """Refuse automated collection unless the fragment explicitly permits it.

    ``prohibited`` and ``unknown`` both refuse. A disabled source also refuses.
    """
    decision = record.automated_access
    if decision != RightsDecision.PERMITTED:
        raise EtfRightsError(
            f"{record.source_id} automated collection is {decision.value}",
        )
    if record.operational_status != OperationalStatus.ENABLED:
        raise EtfRightsError(
            f"{record.source_id} is {record.operational_status.value}; "
            "automated collection is refused",
        )


def holdings_cleared_for_read(record: SourceRightsRecord) -> bool:
    """Holdings may be read only when collection and redistribution are permitted.

    Unknown and prohibited fail the gate. Macro must not treat a failed gate
    as an empty holding list that is safe to use.
    """
    return (
        record.operational_status == OperationalStatus.ENABLED
        and record.automated_access == RightsDecision.PERMITTED
        and record.redistribution == RightsDecision.PERMITTED
    )
