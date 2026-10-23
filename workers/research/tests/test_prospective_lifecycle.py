"""Lifecycle rules for a prospective assessment. No database is opened."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from aqil_research.methods.industrial_production_activity import (
    INDUSTRIAL_PRODUCTION_METHOD_ID,
    INDUSTRIAL_PRODUCTION_METHOD_VERSION,
)
from aqil_research.methods.labour_market import (
    LABOUR_MARKET_METHOD_ID,
    LABOUR_MARKET_METHOD_VERSION,
)
from aqil_research.methods.prices_and_policy import (
    PRICES_AND_POLICY_METHOD_ID,
    PRICES_AND_POLICY_METHOD_VERSION,
)
from aqil_research.prospective.lifecycle import (
    ASSESSMENT_FIELDS,
    CAPTURE_NOTE_PHRASE,
    NOT_QUALIFIED_REASONS,
    LifecycleError,
    evaluation_refusal,
    not_qualified_assessment,
    refusal_before_due_date,
    refusal_missing_outcome,
    refusal_snapshot_observations_only,
    supersede_proposed_internal,
    supersession_refusal,
)

_CREATED = datetime(2026, 10, 23, 1, 50, tzinfo=UTC)
_CAPTURED = datetime(2026, 10, 23, 1, 40, tzinfo=UTC)
_DUE = date(2027, 10, 23)


def _assessment(**overrides: object) -> dict:
    payload = not_qualified_assessment(
        assessment_id="assessment-live-1",
        created_at=_CREATED,
        captured_at=_CAPTURED,
        run_ids=("run-1",),
        observation_ids=("obs-1",),
        retrieval_timestamps=("2026-10-23T01:40:00+00:00",),
        publication_timestamps=("2026-10-14T12:30:00+00:00",),
    )
    payload.update(overrides)
    return payload


def _proposed(assessment_id: str = "assessment-proposed-1") -> dict:
    return {
        "assessment_id": assessment_id,
        "lifecycle_status": "proposed_internal",
        "publication_allowed": False,
    }


def _revision(earlier_id: str, **overrides: object) -> dict:
    payload = {
        "assessment_id": "assessment-proposed-2",
        "lifecycle_status": "proposed_internal",
        "publication_allowed": False,
        "revision_class": "latest_revised",
        "horizon_months": None,
        "supersedes_assessment_id": earlier_id,
        "capture_note": f"A later row. {CAPTURE_NOTE_PHRASE}",
    }
    payload.update(overrides)
    return payload


def test_live_decision_is_not_qualified() -> None:
    payload = _assessment()
    assert tuple(payload["captured_values"]["reasons"]) == NOT_QUALIFIED_REASONS
    assert payload["lifecycle_status"] == "not_qualified"
    assert payload["horizon_months"] is None
    assert payload["publication_allowed"] is False
    assert payload["revision_class"] == "latest_revised"
    assert payload["evaluation_due"] is None
    assert payload["supersedes_assessment_id"] is None
    assert payload["completeness"] == "insufficient"
    assert CAPTURE_NOTE_PHRASE in payload["capture_note"]
    assert "No 6- or 12-month hypothesis qualifies" in payload["support_text"]
    for reason in NOT_QUALIFIED_REASONS:
        assert reason in payload["support_text"]
    assert payload["captured_values"]["series_values"] is None
    assert set(payload) == set(ASSESSMENT_FIELDS)
    assert payload["method_versions"] == {
        LABOUR_MARKET_METHOD_ID: LABOUR_MARKET_METHOD_VERSION,
        PRICES_AND_POLICY_METHOD_ID: PRICES_AND_POLICY_METHOD_VERSION,
        INDUSTRIAL_PRODUCTION_METHOD_ID: INDUSTRIAL_PRODUCTION_METHOD_VERSION,
    }
    assert payload["created_at"] == _CREATED.isoformat()
    assert payload["captured_at"] == _CAPTURED.isoformat()
    assert len(payload["input_hash"]) == 64
    assert len(payload["output_hash"]) == 64
    again = _assessment()
    assert again["input_hash"] == payload["input_hash"]
    assert again["output_hash"] == payload["output_hash"]


def test_cited_ids_do_not_qualify_a_hypothesis() -> None:
    bare = not_qualified_assessment(
        assessment_id="assessment-live-1",
        created_at=_CREATED,
        captured_at=_CAPTURED,
    )
    cited = _assessment()
    assert bare["lifecycle_status"] == "not_qualified"
    assert cited["lifecycle_status"] == "not_qualified"
    assert bare["horizon_months"] is None
    assert cited["observation_ids"] == ["obs-1"]
    assert bare["input_hash"] != cited["input_hash"]


def test_payload_does_not_record_a_direction_probability_return_or_recommendation() -> None:
    payload = _assessment()
    forbidden = {
        "direction",
        "probability",
        "return",
        "recommendation",
        "expected_return",
        "calibrated_probability",
    }

    def keys(value: object) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            found.update(str(key) for key in value)
            for item in value.values():
                found.update(keys(item))
        elif isinstance(value, list):
            for item in value:
                found.update(keys(item))
        return found

    assert keys(payload).isdisjoint(forbidden)
    assert payload["uncertainty_text"] == (
        "No direction, probability, return, or recommendation is stated."
    )


def test_naive_timestamp_is_refused() -> None:
    with pytest.raises(LifecycleError, match="timezone-aware"):
        not_qualified_assessment(
            assessment_id="assessment-live-1",
            created_at=datetime(2026, 10, 23, 1, 50),
            captured_at=_CAPTURED,
        )


def test_evaluation_is_refused_before_the_due_date() -> None:
    refusal = refusal_before_due_date(as_of=date(2027, 10, 22), evaluation_due=_DUE)
    assert refusal is not None
    assert refusal.reason == "evaluation is refused before the due date"
    assert refusal_before_due_date(as_of=_DUE, evaluation_due=_DUE) is None
    assert refusal_before_due_date(as_of=date(2027, 10, 24), evaluation_due=_DUE) is None


def test_evaluation_is_refused_when_the_outcome_is_missing() -> None:
    for outcome in (None, "", "   "):
        refusal = refusal_missing_outcome(outcome_observation_id=outcome)
        assert refusal is not None
        assert refusal.reason == (
            "evaluation is refused because the outcome observation is missing"
        )
    assert refusal_missing_outcome(outcome_observation_id="obs-new") is None


def test_evaluation_is_refused_when_every_observation_was_already_in_the_snapshot() -> None:
    snapshot = {"obs-1", "obs-2"}
    refusal = refusal_snapshot_observations_only(
        snapshot_observation_ids=snapshot,
        available_observation_ids={"obs-1"},
    )
    assert refusal is not None
    assert "already inside the original snapshot" in refusal.reason
    empty = refusal_snapshot_observations_only(
        snapshot_observation_ids=snapshot,
        available_observation_ids=set(),
    )
    assert empty is not None
    assert (
        refusal_snapshot_observations_only(
            snapshot_observation_ids=snapshot,
            available_observation_ids={"obs-1", "obs-new"},
        )
        is None
    )


def test_evaluation_refusal_returns_the_first_matching_rule() -> None:
    before = evaluation_refusal(
        as_of=date(2027, 10, 22),
        evaluation_due=_DUE,
        outcome_observation_id=None,
        snapshot_observation_ids={"obs-1"},
        available_observation_ids={"obs-1"},
    )
    assert before is not None
    assert before.rule == "before_due_date"

    missing = evaluation_refusal(
        as_of=_DUE,
        evaluation_due=_DUE,
        outcome_observation_id=None,
        snapshot_observation_ids={"obs-1"},
        available_observation_ids={"obs-new"},
    )
    assert missing is not None
    assert missing.rule == "missing_outcome"

    already_stored = evaluation_refusal(
        as_of=_DUE,
        evaluation_due=_DUE,
        outcome_observation_id="obs-1",
        snapshot_observation_ids={"obs-1"},
        available_observation_ids={"obs-1"},
    )
    assert already_stored is not None
    assert already_stored.rule == "snapshot_observations_only"

    assert (
        evaluation_refusal(
            as_of=_DUE,
            evaluation_due=_DUE,
            outcome_observation_id="obs-new",
            snapshot_observation_ids={"obs-1"},
            available_observation_ids={"obs-new"},
        )
        is None
    )


def test_proposed_internal_is_superseded_only_by_a_payload_pointing_at_it() -> None:
    earlier = _proposed()
    original = dict(earlier)
    new_payload = _revision(earlier["assessment_id"])
    refusal = supersession_refusal(earlier, new_payload)
    assert refusal is None
    stored = supersede_proposed_internal(earlier, new_payload)
    assert stored["supersedes_assessment_id"] == earlier["assessment_id"]
    assert stored is not new_payload
    assert earlier == original
    stored["lifecycle_status"] = "evaluated"
    assert earlier["lifecycle_status"] == "proposed_internal"

    missing = _revision(earlier["assessment_id"], supersedes_assessment_id=None)
    refused = supersession_refusal(earlier, missing)
    assert refused is not None
    assert "points at the earlier assessment id" in refused.reason
    with pytest.raises(LifecycleError, match="earlier assessment id"):
        supersede_proposed_internal(earlier, missing)

    wrong = _revision("assessment-other")
    assert supersession_refusal(earlier, wrong) is not None
    assert earlier == original


def test_other_statuses_cannot_be_superseded_and_the_earlier_row_is_not_rewritten() -> None:
    for status in ("not_qualified", "evaluated", "superseded"):
        earlier = _proposed()
        earlier["lifecycle_status"] = status
        refusal = supersession_refusal(earlier, _revision(earlier["assessment_id"]))
        assert refusal is not None
        assert refusal.rule == "not_proposed_internal"
        with pytest.raises(LifecycleError, match="proposed_internal"):
            supersede_proposed_internal(earlier, _revision(earlier["assessment_id"]))

    earlier = _proposed()
    with pytest.raises(LifecycleError, match="not rewritten"):
        supersede_proposed_internal(earlier, earlier)


def test_superseding_payload_cannot_open_publication_or_invent_a_claim() -> None:
    earlier = _proposed()
    published = _revision(earlier["assessment_id"], publication_allowed=True)
    refusal = supersession_refusal(earlier, published)
    assert refusal is not None
    assert refusal.reason == "publication_allowed stays false"

    invented = _revision(earlier["assessment_id"], direction="up")
    claim = supersession_refusal(earlier, invented)
    assert claim is not None
    assert claim.rule == "forbidden_claim"
    assert earlier["lifecycle_status"] == "proposed_internal"


def test_lifecycle_module_does_not_open_a_database() -> None:
    source = Path(not_qualified_assessment.__code__.co_filename).read_text(encoding="utf-8")
    lowered = source.lower()
    assert "psycopg" not in lowered
    assert "sqlalchemy" not in lowered
    assert "55432" not in source
    assert "postgres" not in lowered
