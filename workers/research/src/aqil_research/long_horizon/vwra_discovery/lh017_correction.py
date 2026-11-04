"""Wording correction for LH-E-017. The stored evidence row is not rewritten.

The original sentence counted trials and said there was no stored result.
The casebook already held the class counts. Claim version 2 quotes those counts.
"""

from __future__ import annotations

from datetime import UTC, datetime

import psycopg

from aqil_research.long_horizon.registry import REVIEWER_NOTE
from aqil_research.long_horizon.vwra_discovery.dossier import CaseRow

STORED_CASEBOOK_COUNTS = {
    "eimi_ahead": 5,
    "vwra_ahead": 4,
    "both_advance": 25,
    "both_decline": 7,
    "leadership_reversal": 0,
    "approximately_neutral": 73,
}
ORIGINAL_SENTENCE = "LH-E-017 has no stored result."
LABELS = (
    ("eimi_ahead", "EIMI ahead"),
    ("vwra_ahead", "VWRA ahead"),
    ("both_advance", "both advance"),
    ("both_decline", "both decline"),
    ("leadership_reversal", "leadership reversal"),
    ("approximately_neutral", "approximately neutral"),
)


def sentence_from_counts(counts: dict[str, int]) -> str:
    """The generated sentence. Every class is named with its count."""
    parts = [f"{label} {counts[key]}" for key, label in LABELS]
    return "LH-E-017 casebook counts, which may overlap: " + ", ".join(parts) + "."


def sentence_from_cases(cases: list[CaseRow]) -> str:
    counts: dict[str, int] = {}
    for case in cases:
        if case.family != "anchor_count":
            continue
        if case.sample_count is None:
            raise ValueError(f"{case.episode_group} has no count")
        counts[case.episode_group] = case.sample_count
    missing = [key for key, _label in LABELS if key not in counts]
    if missing:
        raise ValueError("casebook sentence is missing " + ", ".join(missing))
    return sentence_from_counts(counts)


def stored_sentence() -> str:
    return sentence_from_counts(STORED_CASEBOOK_COUNTS)


def apply_correction(connection: psycopg.Connection) -> int:
    """Insert claim version 2 once. Version 1, the finding, and the evidence stay."""
    recorded_at = datetime.now(UTC)
    proposition = stored_sentence()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select episode_group, sample_count
            from research.discovery_v2_casebook
            where specification_id = 'EIMI-VWRA-COMPARISON-001'
              and family = 'anchor_count'
            """
        )
        found = {str(group): int(count) for group, count in cursor.fetchall()}
        if found != STORED_CASEBOOK_COUNTS:
            raise RuntimeError("the stored casebook counts differ and were not rewritten")
        cursor.execute(
            """
            select proposition
            from research.scientific_claims
            where claim_id = 'LH-C-017' and version = 1
            """
        )
        original = cursor.fetchone()
        if original is None or original[0] != ORIGINAL_SENTENCE:
            raise RuntimeError("LH-C-017 version 1 is not the stored sentence")
        cursor.execute(
            """
            select statement
            from research.discovery_v2_findings
            where finding_id = 'CMP-F-017'
            """
        )
        finding = cursor.fetchone()
        if finding is None or finding[0] != ORIGINAL_SENTENCE:
            raise RuntimeError("CMP-F-017 is not the stored sentence")
        cursor.execute(
            """
            select proposition
            from research.scientific_claims
            where claim_id = 'LH-C-017' and version = 2
            """
        )
        current = cursor.fetchone()
        if current is not None:
            if current[0] != proposition:
                raise RuntimeError("LH-C-017 version 2 differs and was not overwritten")
            return 0
        cursor.execute(
            """
            select content_sha256
            from research.evidence_records
            where evidence_id = 'LH-V-017'
            """
        )
        evidence = cursor.fetchone()
        if evidence is None:
            raise RuntimeError("LH-V-017 is missing")
        before_hash = evidence[0]
        cursor.execute(
            """
            insert into research.scientific_claims (
              claim_id, version, proposition, status_at_claim, eligibility_class,
              statistical_validity, economic_usefulness, independent_validation,
              remaining_uncertainty, publication_eligible, publication_allowed,
              derivation, reviewer_note, recorded_at
            ) values (
              'LH-C-017', 2, %s, 'insufficient_sample', 'category_b_retrospective',
              'not_assessed_overlapping_months', 'not_assessed', 'not_forward_validated',
              %s, false, false, 'deterministic_criteria', %s, %s
            )
            """,
            (
                proposition,
                (
                    "Wording correction. Version 1 counted trials and said there was no "
                    "stored result. The casebook counts were already stored. Classes may "
                    "overlap. The evidence row and its hash are unchanged."
                ),
                REVIEWER_NOTE,
                recorded_at,
            ),
        )
        cursor.execute(
            """
            insert into research.claim_evidence_links (
              claim_id, claim_version, evidence_id, relation, recorded_at
            ) values ('LH-C-017', 2, 'LH-V-017', 'qualifies', %s)
            """,
            (recorded_at,),
        )
        cursor.execute(
            """
            insert into research.claim_execution_links (
              claim_id, claim_version, execution_id, relation, recorded_at
            ) values ('LH-C-017', 2, 'LH-X-017', 'qualifies', %s)
            """,
            (recorded_at,),
        )
        cursor.execute(
            """
            insert into research.scientific_status_events (
              status_event_id, subject_kind, subject_id, subject_version, status,
              rationale, derivation, recorded_at, publication_allowed
            ) values (
              'LH-S-C-017-wording', 'claim', 'LH-C-017', 2, 'insufficient_sample',
              %s, 'deterministic_criteria', %s, false
            )
            """,
            (
                (
                    "The finding sentence now quotes the stored casebook counts. "
                    "Version 1 is unchanged. The class is not a promotion."
                ),
                recorded_at,
            ),
        )
        cursor.execute(
            """
            select content_sha256, body->>'statement'
            from research.evidence_records
            where evidence_id = 'LH-V-017'
            """
        )
        after = cursor.fetchone()
        if after is None or after[0] != before_hash or after[1] != ORIGINAL_SENTENCE:
            raise RuntimeError("LH-V-017 changed and the correction was refused")
    return 1
