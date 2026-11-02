"""SGD reference FX stays absent until a rights-cleared source can be stored.

The Bank of Japan yen series is not an SGD source. A disabled or unknown row
is a gap, not a rate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aqil_research.sources.rights import (
    RightsOperation,
    SourceRightsRecord,
    find_source_rights,
    source_usable,
)

MAS_SOURCE_ID = "mas_sgd_reference_fx"


class FxGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usable: bool
    source_id: str
    reason: str


def sgd_reference_fx_gap(records: tuple[SourceRightsRecord, ...]) -> FxGap:
    """Return the gap unless MAS retention and display are both usable."""

    record = find_source_rights(records, source_id=MAS_SOURCE_ID)
    if record is None:
        return FxGap(
            usable=False,
            source_id=MAS_SOURCE_ID,
            reason="No MAS SGD reference row is rights-cleared, so no FX rate is stored.",
        )
    retention = source_usable(record, RightsOperation.RAW_DATA_RETENTION)
    display = source_usable(record, RightsOperation.REDISTRIBUTION)
    if retention and display and source_usable(record, RightsOperation.AUTOMATED_ACCESS):
        return FxGap(
            usable=True,
            source_id=MAS_SOURCE_ID,
            reason="MAS SGD reference FX is usable for storage and display.",
        )
    return FxGap(
        usable=False,
        source_id=MAS_SOURCE_ID,
        reason=(
            "MAS SGD reference FX is not usable. "
            "Automated access, retention, or display is unknown, prohibited, or disabled. "
            "No rate is stored."
        ),
    )
