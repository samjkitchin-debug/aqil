"""Sentence-case reports. Figures come from the ledger and are not rewritten by hand."""

from __future__ import annotations

from collections import Counter
from typing import Any


def results_markdown(records: list[dict[str, Any]], state: dict[str, Any]) -> str:
    pilot = _one(records, "pilot")
    inferential = [record for record in records if record["gate"] == "1-inferential"]
    descriptive = [record for record in records if record["gate"] == "1"]
    supported = [
        record for record in records if record["evidence_class"] == "statistically_supported"
    ]
    useful = [record for record in records if record["evidence_class"] == "economically_useful"]
    lines = [
        "# Macro-to-ETF results",
        "",
        "These figures were computed from the frozen catalogue and the local databases. "
        "They are retrospective. They are not point-in-time, "
        "not a forecast, and not an allocation.",
        "",
        _lead(supported, useful),
        "",
        "## Pilot",
        "",
        _pilot_paragraph(pilot),
        "",
        "## What ran",
        "",
        f"Gate 1 described {len(descriptive)} full-sample cells that met the exploratory floor. "
        f"The inferential family held {len(inferential)} training-window cells. "
        f"{_gate_sentence(records, '2', 'Gate 2')} "
        f"{_gate_sentence(records, '3', 'Gate 3')} "
        f"{_gate_sentence(records, '4', 'Gate 4')} "
        f"{_gate_sentence(records, '5', 'Gate 5')} "
        f"{_gate_sentence(records, '6', 'Gate 6')}",
        "",
        "## Evidence classes",
        "",
        _class_table(records),
        "",
        "## Audit",
        "",
        "The inputs are latest-revised series with an assumed one-month lag, "
        "so a cell cannot be point-in-time. "
        "The ETF list was selected in 2026, "
        "and several equity listings share the same retrieved start, "
        "so agreement among them is one piece of evidence about a survivor set. "
        "Overlapping monthly returns are not treated as independent: "
        "the non-overlapping count and the "
        "block-bootstrap interval are part of the record. "
        "A bootstrap interval that contains zero withdraws a claim to inconclusive. "
        "The price ratio is a split-adjusted listing close, "
        "not an issuer total-return index and not NAV. "
        "No foreign-exchange series was used. EUNA stays in euros. "
        "Costs of zero and 10 basis points were assumptions "
        "and were applied only if a cell reached Gate 5. "
        "Nothing in this run was frozen before the outcome, "
        "so the forward-validated class is empty. "
        f"The input hash is `{state.get('input_hash', '')}`.",
        "",
        f"Live latest-revised observations were {state.get('live_latest_revised')}. "
        f"Adjusted closes were {state.get('adjusted_close')}. "
        f"`publication_allowed` true-count was {state.get('publication_allowed_true')}.",
        "",
    ]
    return "\n".join(lines)


def negative_markdown(records: list[dict[str, Any]]) -> str:
    blocked = [record for record in records if record["status"] == "blocked"]
    reasons = Counter(str(record["payload"].get("reason", record["cell_id"])) for record in blocked)
    lines = [
        "# Negative results",
        "",
        "A blocked cell and a null association are completed results. "
        "They are not a reason to choose another transformation.",
        "",
        f"Blocked trial rows: {len(blocked)}.",
        "",
    ]
    for reason, count in reasons.most_common(12):
        lines.append(f"- {count} rows: {reason}")
    lines.extend(["", "## Cells that were estimated and not supported", ""])
    for record in records:
        if record["evidence_class"] in {"statistically_supported", "economically_useful"}:
            continue
        if record["gate"] not in {"pilot", "1", "1-inferential", "2", "3"}:
            continue
        if not record["payload"].get("estimated"):
            continue
        slope = record["payload"].get("slope")
        p_value = record["payload"].get("slope_p")
        lines.append(
            f"- {record['cell_id']}: evidence {record['evidence_class']}, "
            f"slope {slope}, Newey–West p {p_value}."
        )
    if lines[-1].startswith("##"):
        lines.append(
            "No estimated cell was left outside the supported classes, or no cell was estimated."
        )
    lines.append("")
    return "\n".join(lines)


def _lead(supported: list[dict[str, Any]], useful: list[dict[str, Any]]) -> str:
    if useful:
        names = ", ".join(record["cell_id"] for record in useful)
        return (
            f"The economically useful class contains {names}. "
            "That claim is retrospective and is not forward-validated."
        )
    if supported:
        names = ", ".join(record["cell_id"] for record in supported)
        return (
            f"The statistically supported class contains {names}. "
            "No cell cleared the economic comparison. The forward-validated class is empty."
        )
    return (
        "No cell is statistically supported or economically useful on this evidence. "
        "The forward-validated class is empty."
    )


def _pilot_paragraph(record: dict[str, Any] | None) -> str:
    if record is None:
        return "The pilot record is missing."
    payload = record["payload"]
    if not payload.get("estimated"):
        return (
            "The preregistered 12-month unemployment change against VWRA was not estimated. "
            f"Reason: {payload.get('reason')}."
        )
    floor = "It is below the exploratory floor, so the figures are not an exploratory finding."
    if not payload.get("below_exploratory_floor"):
        floor = "It meets the exploratory floor and stays outside the search family."
    return (
        "The preregistered cell is the 12-month change in unemployment, "
        "with an assumed one-month lag, "
        f"against the 12-month VWRA listing-currency price return. "
        f"Pearson r is {payload['pearson_r']}. Spearman r is {payload['spearman_r']}. "
        f"The Newey–West slope is {payload['slope']} with p {payload['slope_p']}. "
        f"Decision points are {payload.get('decision_points')} and non-overlapping windows are "
        f"{payload.get('non_overlapping')}. {floor}"
    )


def _gate_sentence(records: list[dict[str, Any]], gate: str, label: str) -> str:
    rows = [record for record in records if record["gate"] == gate]
    if not rows:
        return f"{label} has no row."
    blocked = sum(1 for record in rows if record["status"] == "blocked")
    if blocked == len(rows):
        reason = rows[0]["payload"].get("reason", "every row is blocked")
        return f"{label} stopped: {reason}."
    return f"{label} recorded {len(rows)} rows, of which {blocked} are blocked."


def _class_table(records: list[dict[str, Any]]) -> str:
    counts = Counter(record["evidence_class"] for record in records)
    lines = ["| Evidence class | Rows |", "| --- | --- |"]
    for name in ("not_claimed", "exploratory", "statistically_supported", "economically_useful"):
        lines.append(f"| {name} | {counts.get(name, 0)} |")
    lines.append("| forward_validated | 0 |")
    return "\n".join(lines)


def _one(records: list[dict[str, Any]], gate: str) -> dict[str, Any] | None:
    for record in records:
        if record["gate"] == gate:
            return record
    return None
