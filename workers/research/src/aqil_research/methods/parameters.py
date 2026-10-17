"""Versioned method parameters — scalars and validated matrices.

Boundary (documented):
- **Parameter change**: same method_id + method_version; new config_id / config_hash only.
- **Methodological change**: new method_version when formula, windows or input contract change.
- **New methodology**: new method_id and separate MethodCard.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MethodParameterDocument(BaseModel):
    """Optional validated matrices for future methods; not a factor-weighting engine."""

    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    scalars: dict[str, str] = Field(default_factory=dict)
    matrices: dict[str, list[list[str]]] = Field(default_factory=dict)

    @field_validator("matrices")
    @classmethod
    def rectangular_matrices(cls, value: dict[str, list[list[str]]]) -> dict[str, list[list[str]]]:
        for name, matrix in value.items():
            if not matrix:
                raise ValueError(f"matrix {name} must not be empty")
            width = len(matrix[0])
            if width == 0:
                raise ValueError(f"matrix {name} must have at least one column")
            for row in matrix:
                if len(row) != width:
                    raise ValueError(f"matrix {name} must be rectangular")
        return value

    def config_hash(self) -> str:
        payload = {
            "config_id": self.config_id,
            "label": self.label,
            "scalars": self.scalars,
            "matrices": self.matrices,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
