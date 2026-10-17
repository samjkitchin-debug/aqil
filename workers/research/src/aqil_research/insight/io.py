"""Read/write research insight JSON for the web preview bridge."""

from __future__ import annotations

import json
from pathlib import Path

from aqil_research.insight.models import ResearchInsight

_REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_WEB_INSIGHT_PATH = _REPO_ROOT / "apps" / "web" / ".local" / "research-insight.v1.json"


def write_insight(path: Path, insight: ResearchInsight) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(insight.model_dump(mode="json"), indent=2, default=str),
        encoding="utf-8",
    )


def read_insight(path: Path) -> ResearchInsight:
    data = json.loads(path.read_text(encoding="utf-8"))
    return ResearchInsight.model_validate(data)
