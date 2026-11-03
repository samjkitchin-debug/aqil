"""Readable records of the frozen result. Wording is fixed before the scan is stored."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from aqil_research.long_horizon.events.availability import AvailabilityRow
from aqil_research.long_horizon.events.compute import Analysis, CataloguedEvent
from aqil_research.long_horizon.money import canonical_json


def inventory_markdown(analysis: Analysis) -> str:
    artifact = analysis.artifact
    lines = [
        "# Price-event inventory",
        "",
        "**Status:** research record. This is not an investment claim and it is not Verified.",
        "",
        (
            f"Definition `{artifact['definition_id']}` version {artifact['definition_version']}. "
            f"Hash `{artifact['definition_hash']}`."
        ),
        "",
        (
            "Counts use the frozen rules in `EVENT_IDENTIFICATION.md`. "
            "A blocked family is a completed result. Total-return events are blocked "
            "and are not relabelled from split-adjusted closes."
        ),
        "",
        f"Catalogued price events: {artifact['event_count']}.",
        "",
        "| Family | Horizon | Status | Events | Censored | Qualifying windows | Listings |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    families = artifact["families"]
    assert isinstance(families, list)
    for row in families:
        assert isinstance(row, dict)
        qualifier = row["qualifier_window_count"]
        qualifier_text = "" if qualifier is None else str(qualifier)
        cells = [
            str(row["family"]),
            str(row["horizon_label"]),
            str(row["status"]),
            str(row["event_count"]),
            str(row["censored_count"]),
            qualifier_text,
            str(row["symbols"]),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            (
                "Qualifying windows for a sustained advance include overlapping windows. "
                "The event count keeps the earliest window only."
            ),
            "",
            (
                "Cross-currency rows stay blocked. No foreign-exchange rate was applied. "
                f"Stored foreign-exchange rows: {artifact['fx_observation_count']}."
            ),
            "",
            (
                "A rally despite deteriorating macroeconomic conditions was not labelled. "
                "Latest-revised series were not used as an event rule."
            ),
            "",
            f"Event-identity hash `{artifact['event_identity_sha256']}`.",
            "",
            "Publication remains closed.",
            "",
        ]
    )
    return "\n".join(lines)


def pilot_markdown(analysis: Analysis) -> str:
    artifact = analysis.artifact
    medians = artifact["medians"]
    pooled = artifact["pooled"]
    reasons = artifact["reasons"]
    assert isinstance(medians, dict)
    assert isinstance(pooled, dict)
    assert isinstance(reasons, list)
    lines = [
        "# Pilot intersection result",
        "",
        "**Status:** research record. This is not an investment claim and it is not Verified.",
        "",
        (
            f"Hypothesis `LH-H-002`, experiment `LH-E-002`, execution `LH-X-002`. "
            f"The predetermined status is `{artifact['status']}`."
        ),
        "",
        "Reasons:",
        "",
    ]
    for reason in reasons:
        lines.append(f"- {reason}")
    lines.extend(
        [
            "",
            (
                f"Median lift {medians['lift']}. "
                f"Median condition frequency {medians['condition_frequency']}. "
                f"Median event share {medians['event_share']}. "
                f"Qualifying listings: {artifact['qualifying_symbols']}."
            ),
            "",
            ("The eligible month-ends are the only sample. It is not an untouched holdout."),
            "",
            "| Quantity | Count |",
            "| --- | ---: |",
            f"| Eligible month-ends | {pooled['eligible']} |",
            f"| Condition true | {pooled['condition']} |",
            f"| Labelled advances | {pooled['event']} |",
            f"| Condition and labelled advance | {pooled['condition_and_event']} |",
            f"| False positives | {pooled['false_positives']} |",
            f"| False negatives | {pooled['false_negatives']} |",
            f"| Condition false | {pooled['condition_false']} |",
            f"| Outcome false | {pooled['outcome_false']} |",
            "",
            (
                "False positives are eligible months where the conjunction was true "
                "and the labelled advance did not follow. Condition-false months are "
                "the controls. They were not chosen for their later returns."
            ),
            "",
            "| Listing | Eligible | Condition | Events | Both | "
            "False positives | Qualifies | Lift |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    symbols = artifact["symbols"]
    assert isinstance(symbols, list)
    for row in symbols:
        assert isinstance(row, dict)
        qualifies = "yes" if row["qualifies"] else "no"
        cells = [
            str(row["symbol"]),
            str(row["eligible"]),
            str(row["condition"]),
            str(row["event"]),
            str(row["condition_and_event"]),
            str(row["false_positives"]),
            qualifies,
            str(row["lift"]),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            (
                "The portfolio comparison was not run. A larger terminal wealth would "
                "remain inconclusive, and this specification does not authorise an allocation. "
                "`LH-X-001` was not reopened."
            ),
            "",
            (
                "The macro example, hypothesis `LH-H-003` and experiment `LH-E-003`, "
                "was not estimated. No macro observation value was read for it. "
                "`bea.vintage.real_gdp.pct_preceding` was not an input."
            ),
            "",
            (
                f"Comparison-identity hash `{artifact['comparison_identity_sha256']}`. "
                f"Specification hash `{artifact['pilot_specification_hash']}`."
            ),
            "",
            "Publication remains closed. This result is not forward-validated.",
            "",
        ]
    )
    return "\n".join(lines)


def write_result_files(root: Path, analysis: Analysis) -> None:
    folder = root / "docs" / "research" / "events"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "INVENTORY.md").write_text(
        inventory_markdown(analysis), encoding="utf-8", newline="\n"
    )
    (folder / "PILOT_RESULT.md").write_text(
        pilot_markdown(analysis), encoding="utf-8", newline="\n"
    )
    (folder / "inventory-summary.json").write_text(
        json.dumps(analysis.artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_events(folder / "inventory-events.jsonl", analysis.events)
    _write_availability(folder / "FEATURE_AVAILABILITY.csv", analysis.availability)


def _write_events(path: Path, events: tuple[CataloguedEvent, ...]) -> None:
    lines = [
        canonical_json(
            {
                "event_id": event.event_id,
                "symbol": event.symbol,
                "family": event.family,
                "horizon_label": event.horizon_label,
                "start_date": event.start_date.isoformat(),
                "end_date": event.end_date.isoformat(),
                "price_return": event.price_return,
                "label_uses_later_prices": event.label_uses_later_prices,
                "usable_as_investment_signal": False,
            }
        )
        for event in events
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")


def _write_availability(path: Path, rows: tuple[AvailabilityRow, ...]) -> None:
    fieldnames = [
        "symbol",
        "feature_id",
        "lookback_label",
        "clock",
        "availability",
        "covered_event_count",
        "catalogued_event_count",
        "seasonal_adjustment",
        "detail",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "symbol": row.symbol,
                    "feature_id": row.feature_id,
                    "lookback_label": row.lookback_label,
                    "clock": row.clock,
                    "availability": row.availability,
                    "covered_event_count": row.covered_event_count,
                    "catalogued_event_count": row.catalogued_event_count,
                    "seasonal_adjustment": row.seasonal_adjustment or "",
                    "detail": row.detail,
                }
            )
