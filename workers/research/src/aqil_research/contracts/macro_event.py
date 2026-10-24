"""Macro event v1. Field names match docs/schemas/macro_event.v1.json."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MACRO_EVENT_SCHEMA_FILE = "macro_event.v1.json"

EpistemicClass = Literal[
    "confirmed_event",
    "reported_allegation",
    "forecast",
    "interpretation",
]
ClaimScope = Literal["policy_action_stated", "publication_recorded"]
EvidenceRole = Literal[
    "primary",
    "secondary",
    "supporting",
    "conflicting",
    "subsequent_development",
]
RecordClass = Literal["recorded", "synthetic_fixture"]
InvestmentImplication = Literal["no_action", "insufficient_evidence"]
MacroSourceId = Literal[
    "bls_cps_unemployment_rate",
    "bls_ces_total_nonfarm_payrolls",
    "bls_jolts_total_nonfarm_job_openings",
    "bls_cpi_u_all_items",
    "federal_reserve_g17_total_ip",
    "federal_reserve_sloos_cil",
    "federal_reserve_h8_bank_credit",
    "federal_reserve_h15_federal_funds_effective",
    "federal_reserve_h15_treasury_10y_constant_maturity",
    "ecb_sdw_hicp_sa",
]


def macro_event_schema_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "schemas" / MACRO_EVENT_SCHEMA_FILE
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(MACRO_EVENT_SCHEMA_FILE)


def macro_event_field_names() -> tuple[str, ...]:
    document = json.loads(macro_event_schema_path().read_text(encoding="utf-8"))
    required = document["required"]
    if not isinstance(required, list) or not all(isinstance(name, str) for name in required):
        raise ValueError("macro event schema required list is not a list of names")
    return tuple(required)


class MacroEventEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    update_id: str = Field(min_length=1)
    role: EvidenceRole
    cluster_key: str = Field(min_length=1)


class MacroEvent(BaseModel):
    """Write shape for one event and its evidence. Not an investment instruction."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    event_id: str = Field(min_length=1)
    event_key: str = Field(pattern=r"^[a-z0-9_]{1,80}$")
    category: str = Field(pattern=r"^[a-z0-9_]{1,80}$")
    epistemic_class: EpistemicClass
    claim_scope: ClaimScope
    summary: str = Field(min_length=1, max_length=500)
    country: str | None = None
    region: str | None = None
    industries: list[str] = Field(default_factory=list)
    event_on: date
    event_dates_stated: str = Field(min_length=1, max_length=400)
    indicator_source_ids: list[MacroSourceId] = Field(default_factory=list)
    channel_note: str | None = None
    surface_on_today: bool = False
    surface_reason: str | None = None
    surfaced_at: datetime | None = None
    record_class: RecordClass
    monitoring: Literal["manual"] = "manual"
    publication_allowed: Literal[False] = False
    investment_implication: InvestmentImplication
    evidence: list[MacroEventEvidence]

    @model_validator(mode="after")
    def confirmed_event_has_primary(self) -> MacroEvent:
        if self.epistemic_class == "confirmed_event" and not any(
            item.role == "primary" for item in self.evidence
        ):
            raise ValueError("confirmed_event requires primary evidence")
        if self.surface_on_today and (not self.surface_reason or self.surfaced_at is None):
            raise ValueError("surfacing on Today requires a reason and a time")
        if bool(self.indicator_source_ids) != bool(self.channel_note):
            raise ValueError("indicator channels and the channel note are required together")
        return self
