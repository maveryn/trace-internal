"""Public registration facade for single-series trend chart tasks."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from .value_task import ChartsTrendValueTask as _ChartsTrendValueTask


class ChartsTrendValueTask(_ChartsTrendValueTask):
    """Answer ordered-sequence trend values in one labeled chart."""


@register_task
class ChartsTrendTurningPointCountTask(FixedChartQueryVariantTaskMixin, ChartsTrendValueTask):
    """Count peaks or troughs in an ordered single-series chart."""

    task_id = "task_charts__single_series__turning_point_count"
    fixed_query_id = "turning_point_count"


@register_task
class ChartsTrendMonotoneStreakLengthTask(FixedChartQueryVariantTaskMixin, ChartsTrendValueTask):
    """Return the longest increasing or decreasing streak length."""

    task_id = "task_charts__single_series__monotone_streak_length"
    fixed_query_id = "longest_monotone_streak"


@register_task
class ChartsTrendEndpointChangeValueTask(MergedChartQueryVariantTaskMixin, ChartsTrendValueTask):
    """Compute the endpoint-to-endpoint change over an ordered chart interval."""

    task_id = "task_charts__single_series__endpoint_change_value"
    allowed_query_ids = ("endpoint_change_value",)


@register_task
class ChartsTrendIntervalRateValueTask(MergedChartQueryVariantTaskMixin, ChartsTrendValueTask):
    """Compute the average rate of change over an ordered chart interval."""

    task_id = "task_charts__single_series__interval_rate_value"
    allowed_query_ids = ("interval_rate_value",)


class _ThresholdCrossingModeTaskMixin(FixedChartQueryVariantTaskMixin):
    """Force one threshold-crossing reasoning mode for a public task id."""

    fixed_query_id = "threshold_crossing"
    fixed_crossing_mode: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        requested_mode = params.get("crossing_mode")
        if requested_mode is not None and str(requested_mode) != str(self.fixed_crossing_mode):
            raise ValueError(
                "public threshold-crossing task crossing_mode must match "
                f"'{self.fixed_crossing_mode}' (got: {requested_mode})"
            )
        forced_params = dict(params)
        forced_params["crossing_mode"] = str(self.fixed_crossing_mode)
        forced_params["crossing_mode_weights"] = {
            "observed": 1.0 if str(self.fixed_crossing_mode) == "observed" else 0.0,
            "linear_projection": 1.0 if str(self.fixed_crossing_mode) == "linear_projection" else 0.0,
        }
        return super().generate(
            int(instance_seed),
            params=forced_params,
            max_attempts=int(max_attempts),
        )


@register_task
class ChartsTrendObservedThresholdCrossingLabelTask(_ThresholdCrossingModeTaskMixin, ChartsTrendValueTask):
    """Return the first observed label crossing a threshold."""

    task_id = "task_charts__single_series__observed_threshold_crossing_label"
    fixed_crossing_mode = "observed"
    supports_unanswerable = True


@register_task
class ChartsTrendProjectedThresholdCrossingLabelTask(_ThresholdCrossingModeTaskMixin, ChartsTrendValueTask):
    """Return the first extrapolated future label crossing a threshold."""

    task_id = "task_charts__single_series__projected_threshold_crossing_label"
    fixed_crossing_mode = "linear_projection"
    supports_unanswerable = True


__all__ = [
    "ChartsTrendEndpointChangeValueTask",
    "ChartsTrendIntervalRateValueTask",
    "ChartsTrendMonotoneStreakLengthTask",
    "ChartsTrendObservedThresholdCrossingLabelTask",
    "ChartsTrendProjectedThresholdCrossingLabelTask",
    "ChartsTrendTurningPointCountTask",
    "ChartsTrendValueTask",
]
