"""Public exports for annotated-series chart tasks."""

from __future__ import annotations

from ...registry import register_task
from .event_window_common import TASK_ID
from .event_window_task import ChartsAnnotatedSeriesBaseTask as _ChartsAnnotatedSeriesBaseTask


class ChartsAnnotatedSeriesBaseTask(_ChartsAnnotatedSeriesBaseTask):
    """Shared implementation for annotated single-series chart public tasks."""

    task_id = TASK_ID


@register_task
class ChartsAnnotatedSeriesEventWindowExtremumLabelTask(ChartsAnnotatedSeriesBaseTask):
    """Identify an extremum label inside the highlighted event window."""

    task_id = "task_charts__annotated_series__event_window_extremum_label"
    query_id = "event_window_extremum_label"


@register_task
class ChartsAnnotatedSeriesEventWindowThresholdCountTask(ChartsAnnotatedSeriesBaseTask):
    """Count highlighted-window marks satisfying a threshold."""

    task_id = "task_charts__annotated_series__event_window_threshold_count"
    query_id = "event_window_threshold_count"


@register_task
class ChartsAnnotatedSeriesCalloutEndpointChangeValueTask(ChartsAnnotatedSeriesBaseTask):
    """Compute endpoint change from a callout-anchored mark."""

    task_id = "task_charts__annotated_series__callout_endpoint_change_value"
    query_id = "callout_endpoint_change_value"


__all__ = [
    "ChartsAnnotatedSeriesBaseTask",
    "ChartsAnnotatedSeriesCalloutEndpointChangeValueTask",
    "ChartsAnnotatedSeriesEventWindowExtremumLabelTask",
    "ChartsAnnotatedSeriesEventWindowThresholdCountTask",
]
