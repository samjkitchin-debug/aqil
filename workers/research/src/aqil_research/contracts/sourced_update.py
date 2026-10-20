"""Sourced update v1 — a retrieved source item, not an investment conclusion.

Field names are the required list in docs/schemas/sourced_update.v1.json
(mirrored at packages/contracts/schemas/). Do not invent a second name for a column.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SOURCED_UPDATE_SCHEMA_FILE = "sourced_update.v1.json"


def sourced_update_schema_path() -> Path:
    """Authoritative JSON Schema. The packages/contracts copy must stay identical."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "schemas" / SOURCED_UPDATE_SCHEMA_FILE
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(SOURCED_UPDATE_SCHEMA_FILE)


def sourced_update_field_names() -> tuple[str, ...]:
    """Column and contract names, in schema order. Shared with the web reader."""
    document = json.loads(sourced_update_schema_path().read_text(encoding="utf-8"))
    required = document["required"]
    if not isinstance(required, list) or not all(isinstance(name, str) for name in required):
        raise ValueError("sourced update schema required list is not a list of names")
    return tuple(required)


class SourcedUpdate(BaseModel):
    """One append-only sourced item. A correction is a new row with correction_of set."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    update_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    canonical_url: str = Field(pattern=r"^https://\S+$")
    published_at: datetime | None = None
    retrieved_at: datetime
    retrieval_id: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    correction_of: str | None = None
    status: Literal["sourced"] = "sourced"

    @model_validator(mode="after")
    def publication_not_after_retrieval(self) -> SourcedUpdate:
        if self.published_at is not None and self.published_at > self.retrieved_at:
            raise ValueError("published_at cannot be after retrieved_at")
        if self.correction_of is not None and self.correction_of == self.update_id:
            raise ValueError("a sourced update cannot correct itself")
        return self
