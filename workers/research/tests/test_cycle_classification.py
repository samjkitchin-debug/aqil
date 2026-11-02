"""Cycle labels from the 2 November partial record. History is not rewritten."""

from aqil_research.workflow.daily_cycle import _refresh_event
from aqil_research.workflow.refresh import SourceRefreshResult


def _event(outcome: str, detail: str = ""):
    return _refresh_event(
        SourceRefreshResult("example", outcome, detail=detail),
        lambda _source_id: ("example.series",),
    )


def test_absent_parameter_version_is_blocked() -> None:
    outcome, detail, datasets = _event("absent", "no stored 1988 refit")
    assert outcome == "blocked"
    assert detail == "no stored 1988 refit"
    assert datasets == set()


def test_unchanged_monthly_series_is_not_a_failure() -> None:
    outcome, _detail, datasets = _event("unchanged")
    assert outcome == "unchanged"
    assert datasets == set()


def test_rights_block_stays_out_of_the_failure_label() -> None:
    outcome, _detail, _datasets = _event("failed_rights")
    assert outcome == "rights_blocked"


def test_a_new_filtered_path_is_success_without_a_refit() -> None:
    outcome, _detail, datasets = _event("filter_update")
    assert outcome == "success"
    assert datasets == {"example.series"}
