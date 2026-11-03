"""Write the dossier notes from a stored summary. Numbers come from the runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _line(label: str, value: object) -> str:
    return f"- {label}: {value}"


def _dossier_page(name: str, row: dict[str, Any]) -> str:
    classes = row.get("class_counts") or {}
    class_lines = "\n".join(_line(str(key), value) for key, value in sorted(classes.items()))
    if not class_lines:
        class_lines = "- none"
    return "\n".join(
        [
            f"# {name}",
            "",
            f"Dossier `{row['execution_id']}`, hypothesis `{row['hypothesis_id']}`.",
            f"Status `{row['status']}`. Registry result `{row['policy']}`.",
            "",
            row["prose"],
            "",
            "## Counts",
            "",
            _line("Trials", row["trial_count"]),
            _line("Refused trials", row["refused_count"]),
            _line("Trials with an effect", row["effect_count"]),
            _line("Primary-horizon Spearman tests in the diagnostic", row["bh_tested"]),
            _line("Diagnostic flags", row["bh_flagged"]),
            _line("Eligible conjunction month-ends", row.get("eligible")),
            "",
            "## Primary-horizon classes",
            "",
            class_lines,
            "",
            "The Benjamini-Hochberg flags do not change the status.",
            "Logistic, probit, and regularized searches are refusal rows.",
            "Method rows have no effect. Publication stays false.",
            "",
        ]
    )


def write_documents(root: Path, summary: dict[str, Any]) -> None:
    folder = root / "docs" / "research" / "etf-protocol"
    folder.mkdir(parents=True, exist_ok=True)
    pages = {
        "VWRA.md": _dossier_page("VWRA", summary["dossiers"]["VWRA"]),
        "EIMI.md": _dossier_page("EIMI", summary["dossiers"]["EIMI"]),
        "PAIR.md": _dossier_page("EIMI relative to VWRA", summary["dossiers"]["EIMI-VWRA"]),
    }
    overview = "\n".join(
        [
            "# ETF protocol",
            "",
            "Protocol `ETF-PROT-001` version 1 and event definition `EVT-DEF-002` version 1.",
            f"Specification commit `{summary['git_commit']}`.",
            f"Protocol hash `{summary['protocol_hash']}`.",
            f"`EVT-DEF-001` hash `{summary['evt_def_001_hash']}` is unchanged.",
            f"`EVT-DEF-002` hash `{summary['evt_def_002_hash']}`.",
            "",
            f"Catalogued listings: {summary['catalogue_symbols']}.",
            f"New events: {summary['event_count']}.",
            f"Trials: {summary['trial_count']}. Declared grid: {summary['declared_count']}.",
            f"Registry result: `{summary['policy']}`.",
            "",
            "EIMI is an emerging-market overweight relative to VWRA, not a separate diversifier.",
            "Relative outperformance is not treated as a positive absolute return.",
            "INRG has no stored prices. EUNA stays blocked for a US-dollar "
            "relative result until foreign exchange exists.",
            "Static mixes, periodic rebalancing, and contribution-matched "
            "wealth are not simulated.",
            "The portfolio path was not built. The 618 catalogue scenarios were not executed.",
            "The immediate VWRA contribution path remains the untested default.",
            "",
            "Latest-revised macro trials are category B and are not decision inputs.",
            "`bea.vintage.real_gdp.pct_preceding` stays a point-in-time "
            "indicator and is not a method replay.",
            "`publication_allowed` stays false. This note is not Verified.",
            "",
            "Detail is in `VWRA.md`, `EIMI.md`, and `PAIR.md`.",
            "",
        ]
    )
    review = "\n".join(
        [
            "# Review checklist",
            "",
            "- The specification commit precedes the stored scores.",
            "- `EVT-DEF-001` was not edited and its hash is unchanged.",
            "- `LH-H-001` through `LH-H-004` were not rescored.",
            "- `LH-H-003` was not estimated.",
            "- Logistic, probit, and regularized searches are refusal rows.",
            "- Method rows have null effects.",
            "- The stored trial count equals the declared grid.",
            "- A second protocol run inserts nothing.",
            "- No allocation policy was registered.",
            "- The portfolio path was not built.",
            "- The 618 catalogue scenarios were not executed.",
            "- `publication_allowed` is false.",
            "- The migration was not applied to hosted Supabase.",
            "- This checklist is not Verified.",
            "",
        ]
    )
    (folder / "README.md").write_text(overview, encoding="utf-8")
    (folder / "REVIEW.md").write_text(review, encoding="utf-8")
    for name, body in pages.items():
        (folder / name).write_text(body, encoding="utf-8")
