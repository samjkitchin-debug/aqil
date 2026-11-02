"""Registry binding for Bai–Perron.

The estimator module hashes its own bytes. This subclass adds the execution
contract without changing that file, so the stored implementation hash can
still be compared with the estimator that produced the run.
"""

from __future__ import annotations

from aqil_research.methods.bai_perron_mean_shifts import (
    PUBLISHED_CONFIG,
    SEGMENT_FLOOR,
    TRIM_DENOMINATOR,
    TRIM_NUMERATOR,
    BaiPerronMeanShiftsMethod,
)
from aqil_research.methods.protocol import MethodDependency, bind_dependency


class RegisteredBaiPerronMeanShiftsMethod(BaiPerronMeanShiftsMethod):
    def dependency(self) -> MethodDependency:
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history=(
                "2 monthly log-growth observations; the trim is "
                f"max({SEGMENT_FLOOR}, floor({TRIM_NUMERATOR}/{TRIM_DENOMINATOR} of the sample)) "
                "and a shorter sample selects no break"
            ),
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(PUBLISHED_CONFIG)
