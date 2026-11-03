"""Append-only writes for the long-horizon registry.

Re-runs do not update an existing row. publication_allowed is always false.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Json

from aqil_research.long_horizon.catalogue import CatalogueReport
from aqil_research.long_horizon.families import FAMILY_GATES
from aqil_research.long_horizon.spec import (
    CLAIM_ID,
    EVIDENCE_ID,
    EXECUTION_ID,
    EXPERIMENT_ID,
    HYPOTHESIS_ID,
    REGISTER_ID,
    REGISTER_VERSION,
)

REVIEWER_NOTE = (
    "Deterministic criteria in the frozen specification assigned this status. "
    "No separate human scientific review is recorded. Publication is not eligible."
)


class RegistryError(RuntimeError):
    """The registry refused a write that would overwrite evidence."""


def _comparison_note(report: CatalogueReport) -> str:
    disagreed = any(
        (
            report.json_csv_field_mismatches,
            report.xlsx_scenario_cell_mismatches,
            report.xlsx_mechanism_mismatches,
            report.scenario_ids_only_in_json_versus_csv,
            report.scenario_ids_only_in_csv_versus_json,
            report.scenario_ids_only_in_json_versus_xlsx,
            report.scenario_ids_only_in_xlsx_versus_json,
            report.signal_ids_only_in_json,
            report.signal_ids_only_in_xlsx,
        )
    )
    if disagreed:
        return (
            "The founding files disagree. Both sides are retained and nothing "
            "was dropped to force a match."
        )
    return (
        "Parsed scenario fields agree across the JSON, CSV, and workbook. "
        "The files are not byte-identical and were not deduplicated."
    )


def candidate_parameters(
    report: CatalogueReport,
    imported_at: datetime,
) -> list[tuple[Any, ...]]:
    files = {item.filename: item for item in report.files}
    rows: list[tuple[Any, ...]] = []
    for item in report.files:
        rows.append(
            _candidate(
                item.filename,
                item.sha256,
                item.byte_count,
                "file",
                item.filename,
                {"sha256": item.sha256, "bytes": item.byte_count},
                None,
                imported_at,
            )
        )
    for filename, scenarios in report.scenarios_by_source.items():
        source = files[filename]
        for scenario in scenarios:
            rows.append(
                _candidate(
                    source.filename,
                    source.sha256,
                    source.byte_count,
                    "scenario",
                    scenario["Scenario ID"],
                    scenario,
                    None,
                    imported_at,
                )
            )
    for filename, signals in report.signals_by_source.items():
        source = files[filename]
        for signal in signals:
            rows.append(
                _candidate(
                    source.filename,
                    source.sha256,
                    source.byte_count,
                    "signal",
                    signal["Signal ID"],
                    signal,
                    None,
                    imported_at,
                )
            )
    workbook = files["aqil_long_horizon_strategy_research_matrix_v1.xlsx"]
    for sheet_name, row_count in report.sheet_rows:
        rows.append(
            _candidate(
                workbook.filename,
                workbook.sha256,
                workbook.byte_count,
                "sheet",
                sheet_name,
                {"rows_including_header": row_count},
                None,
                imported_at,
            )
        )
    anchor = files["aqil_long_horizon_scenarios_v1.json"]
    rows.append(
        _candidate(
            anchor.filename,
            anchor.sha256,
            anchor.byte_count,
            "comparison",
            "founding-file-comparison",
            {
                "json_csv_field_mismatches": report.json_csv_field_mismatches,
                "xlsx_scenario_cell_mismatches": report.xlsx_scenario_cell_mismatches,
                "xlsx_mechanism_mismatches": report.xlsx_mechanism_mismatches,
                "scenario_ids_only_in_json_versus_csv": list(
                    report.scenario_ids_only_in_json_versus_csv
                ),
                "scenario_ids_only_in_csv_versus_json": list(
                    report.scenario_ids_only_in_csv_versus_json
                ),
                "scenario_ids_only_in_json_versus_xlsx": list(
                    report.scenario_ids_only_in_json_versus_xlsx
                ),
                "scenario_ids_only_in_xlsx_versus_json": list(
                    report.scenario_ids_only_in_xlsx_versus_json
                ),
                "signal_ids_only_in_json": list(report.signal_ids_only_in_json),
                "signal_ids_only_in_xlsx": list(report.signal_ids_only_in_xlsx),
                "file_sha256": {item.filename: item.sha256 for item in report.files},
            },
            _comparison_note(report),
            imported_at,
        )
    )
    return rows


def _candidate(
    filename: str,
    digest: str,
    size: int,
    kind: str,
    original_id: str,
    payload: dict[str, Any],
    note: str | None,
    imported_at: datetime,
) -> tuple[Any, ...]:
    return (
        REGISTER_ID,
        REGISTER_VERSION,
        filename,
        digest,
        size,
        kind,
        original_id,
        Json(payload),
        False,
        note,
        imported_at,
        False,
    )


def import_candidate_register(
    connection: psycopg.Connection,
    report: CatalogueReport,
    imported_at: datetime,
) -> int:
    rows = candidate_parameters(report, imported_at)
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into research.candidate_design_rows (
              register_id, register_version, source_filename, source_sha256,
              source_bytes, row_kind, original_id, payload, empirical_result,
              disagreement_note, imported_at, publication_allowed
            ) values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            on conflict do nothing
            """,
            rows,
        )
        for gate in FAMILY_GATES:
            cursor.execute(
                """
                insert into research.research_family_gates (
                  register_id, family_name, gate, reason, recorded_at,
                  publication_allowed
                ) values (%s, %s, %s, %s, %s, false)
                on conflict do nothing
                """,
                (REGISTER_ID, gate.family_name, gate.gate, gate.reason, imported_at),
            )
    return len(rows)


def store_frozen_specification(
    connection: psycopg.Connection,
    *,
    hypothesis: dict[str, Any],
    specification: dict[str, Any],
    specification_hash: str,
    frozen_at: datetime,
) -> str:
    """Insert version 1, or return unchanged when the same hash is already stored."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select specification_hash
            from research.experiment_specifications
            where experiment_id = %s and version = 1
            """,
            (EXPERIMENT_ID,),
        )
        found = cursor.fetchone()
        if found is not None:
            if found[0] != specification_hash:
                raise RegistryError("the frozen specification hash differs and was not overwritten")
            return "unchanged"
        cursor.execute(
            """
            insert into research.hypotheses (
              hypothesis_id, version, proposition, economic_rationale,
              expected_mechanism, expected_direction, horizon, falsification_criteria,
              alternative_explanations, relevant_indicators, relevant_methodologies,
              target_instruments, initial_status, amendment_rationale, registered_at,
              registered_by, catalogue_signal_id, publication_allowed
            ) values (
              %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, null, %s,
              'long-horizon-programme', null, false
            )
            """,
            (
                hypothesis["hypothesis_id"],
                hypothesis["proposition"],
                hypothesis["economic_rationale"],
                hypothesis["expected_mechanism"],
                hypothesis["expected_direction"],
                hypothesis["horizon"],
                hypothesis["falsification_criteria"],
                Json(hypothesis["alternative_explanations"]),
                Json(hypothesis["relevant_indicators"]),
                Json(hypothesis["relevant_methodologies"]),
                Json(hypothesis["target_instruments"]),
                hypothesis["initial_status"],
                frozen_at,
            ),
        )
        cursor.execute(
            """
            insert into research.experiment_specifications (
              experiment_id, version, category, category_label, specification,
              specification_hash, frozen_at, publication_allowed
            ) values (%s, 1, 'C', 'price_only_simulator_research', %s, %s, %s, false)
            """,
            (EXPERIMENT_ID, Json(specification), specification_hash, frozen_at),
        )
        cursor.execute(
            """
            insert into research.hypothesis_experiment_links (
              hypothesis_id, hypothesis_version, experiment_id, experiment_version,
              recorded_at
            ) values (%s, 1, %s, 1, %s)
            """,
            (HYPOTHESIS_ID, EXPERIMENT_ID, frozen_at),
        )
        _status_event(
            cursor,
            "LH-S-H-001-proposed",
            "hypothesis",
            HYPOTHESIS_ID,
            1,
            "proposed",
            "Registered before the historical path was scored.",
            frozen_at,
        )
        _status_event(
            cursor,
            "LH-S-E-001-proposed",
            "experiment",
            EXPERIMENT_ID,
            1,
            "proposed",
            "Specification frozen before execution.",
            frozen_at,
        )
    return "inserted"


def store_pilot_execution(
    connection: psycopg.Connection,
    *,
    artifact: dict[str, Any],
    artifact_sha256: str,
    status: str,
    proposition: str,
    recorded_at: datetime,
    availability_cutoff: datetime,
    git_commit: str,
    code_hash: str,
    input_manifest: dict[str, Any],
    price_series_versions: list[dict[str, str]],
    library_versions: dict[str, str],
    configuration: dict[str, Any],
    simulation_start: object,
    simulation_end: object,
    relation: str,
) -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            "select artifact_sha256 from research.experiment_executions where execution_id = %s",
            (EXECUTION_ID,),
        )
        found = cursor.fetchone()
        if found is not None:
            if found[0] != artifact_sha256:
                raise RegistryError("an execution with a different artifact was not overwritten")
            return "unchanged"
        cursor.execute(
            """
            insert into research.experiment_executions (
              execution_id, experiment_id, experiment_version, state, git_commit,
              code_hash, parameter_version_id, input_manifest, macro_vintage_ids,
              price_series_versions, library_versions, random_seed, executed_at,
              availability_cutoff, simulation_start, simulation_end, artifact_sha256,
              reproduction_command, validation_status, configuration,
              supersedes_execution_id, research_run_id, publication_allowed
            ) values (
              %s, %s, 1, 'succeeded', %s, %s, null, %s, '[]'::jsonb, %s, %s,
              'not_applicable_no_randomness', %s, %s, %s, %s, %s,
              'uv run python -m aqil_research.long_horizon.reproduce',
              %s, %s, null, null, false
            )
            """,
            (
                EXECUTION_ID,
                EXPERIMENT_ID,
                git_commit,
                code_hash,
                Json(input_manifest),
                Json(price_series_versions),
                Json(library_versions),
                recorded_at,
                availability_cutoff,
                simulation_start,
                simulation_end,
                artifact_sha256,
                status,
                Json(configuration),
            ),
        )
        cursor.execute(
            """
            insert into research.evidence_records (
              evidence_id, execution_id, evidence_kind, content_sha256, body,
              recorded_at, publication_allowed
            ) values (%s, %s, 'wealth_path', %s, %s, %s, false)
            """,
            (EVIDENCE_ID, EXECUTION_ID, artifact_sha256, Json(artifact), recorded_at),
        )
        cursor.execute(
            """
            insert into research.scientific_claims (
              claim_id, version, proposition, status_at_claim, eligibility_class,
              statistical_validity, economic_usefulness, independent_validation,
              remaining_uncertainty, publication_eligible, publication_allowed,
              derivation, reviewer_note, recorded_at
            ) values (
              %s, 1, %s, %s, 'category_c_price_only',
              'not assessed; one shared path is not a sample',
              'not established',
              'not recorded',
              'Category C uses split-adjusted listing prices, one window, and no holdout.',
              false, false, 'deterministic_criteria', %s, %s
            )
            """,
            (CLAIM_ID, proposition, status, REVIEWER_NOTE, recorded_at),
        )
        cursor.execute(
            """
            insert into research.claim_evidence_links (
              claim_id, claim_version, evidence_id, relation, recorded_at
            ) values (%s, 1, %s, %s, %s)
            """,
            (CLAIM_ID, EVIDENCE_ID, relation, recorded_at),
        )
        cursor.execute(
            """
            insert into research.claim_execution_links (
              claim_id, claim_version, execution_id, relation, recorded_at
            ) values (%s, 1, %s, %s, %s)
            """,
            (CLAIM_ID, EXECUTION_ID, relation, recorded_at),
        )
        _status_event(
            cursor,
            "LH-S-H-001-result",
            "hypothesis",
            HYPOTHESIS_ID,
            1,
            status,
            (
                "Current status after the frozen category C rule. The original proposition remains "
                "version 1."
            ),
            recorded_at,
        )
        _status_event(
            cursor,
            "LH-S-E-001-result",
            "experiment",
            EXPERIMENT_ID,
            1,
            status,
            "Execution reconciled. The status is not an investment claim.",
            recorded_at,
        )
        _status_event(
            cursor,
            "LH-S-C-001-result",
            "claim",
            CLAIM_ID,
            1,
            status,
            "Claim version 1 records the deterministic status.",
            recorded_at,
        )
        _dependencies(cursor, input_manifest, recorded_at)
    return "inserted"


def _status_event(
    cursor: psycopg.Cursor,
    event_id: str,
    kind: str,
    subject_id: str,
    version: int,
    status: str,
    rationale: str,
    recorded_at: datetime,
) -> None:
    cursor.execute(
        """
        insert into research.scientific_status_events (
          status_event_id, subject_kind, subject_id, subject_version, status,
          rationale, derivation, recorded_at, publication_allowed
        ) values (%s, %s, %s, %s, %s, %s, 'deterministic_criteria', %s, false)
        """,
        (event_id, kind, subject_id, version, status, rationale, recorded_at),
    )


def _dependencies(
    cursor: psycopg.Cursor,
    manifest: dict[str, Any],
    recorded_at: datetime,
) -> None:
    start = manifest["simulation_start"]
    end = manifest["simulation_end"]
    rows = [
        (
            "LH-D-001",
            "policy",
            "immediate_vwra",
            "policy",
            "odd_month_vwra_even_month_cspx_january_equal_value_rebalance",
            "matched_control",
            None,
            None,
            "The passive path is the matched control. It is not a second confirmation.",
        ),
        (
            "LH-D-002",
            "policy",
            "immediate_vwra",
            "policy",
            "odd_month_vwra_even_month_cspx_january_equal_value_rebalance",
            "shares_dataset",
            "aqil_etf.adjusted_close",
            None,
            "Both paths use the same stored adjusted closes.",
        ),
        (
            "LH-D-003",
            "policy",
            "immediate_vwra",
            "instrument",
            "VWRA",
            "shares_instrument",
            None,
            "VWRA",
            "VWRA is in both policies.",
        ),
        (
            "LH-D-004",
            "policy",
            "odd_month_vwra_even_month_cspx_january_equal_value_rebalance",
            "instrument",
            "CSPX",
            "shares_instrument",
            None,
            "CSPX",
            (
                "CSPX is used only by the alternative. The listing is shared with the price store, "
                "not with the passive policy."
            ),
        ),
        (
            "LH-D-005",
            "policy",
            "immediate_vwra",
            "policy",
            "odd_month_vwra_even_month_cspx_january_equal_value_rebalance",
            "same_contribution_schedule",
            None,
            None,
            "Contribution dates and amounts match.",
        ),
        (
            "LH-D-006",
            "policy",
            "immediate_vwra",
            "policy",
            "odd_month_vwra_even_month_cspx_january_equal_value_rebalance",
            "overlaps_period",
            None,
            None,
            "The paths cover the same stored sessions.",
        ),
    ]
    for (
        dependency_id,
        left_kind,
        left_id,
        right_kind,
        right_id,
        relation,
        dataset_id,
        instrument_id,
        detail,
    ) in rows:
        cursor.execute(
            """
            insert into research.research_dependencies (
              dependency_id, left_kind, left_id, right_kind, right_id, relation,
              dataset_id, indicator_id, instrument_id, methodology_id,
              period_start, period_end, independent_confirmation, detail, recorded_at
            ) values (
              %s, %s, %s, %s, %s, %s, %s, null, %s, null, %s, %s, false, %s, %s
            )
            """,
            (
                dependency_id,
                left_kind,
                left_id,
                right_kind,
                right_id,
                relation,
                dataset_id,
                instrument_id,
                start,
                end,
                detail,
                recorded_at,
            ),
        )
