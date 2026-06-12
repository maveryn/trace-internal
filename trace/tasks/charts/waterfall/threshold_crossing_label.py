"""Scene-package public task for `task_charts__waterfall__threshold_crossing_label`."""

from __future__ import annotations

from ...registry import register_task
from .shared.panel_query import ChartsWaterfallThresholdCrossingLabelTask as _SourceTask


@register_task
class ChartsWaterfallThresholdCrossingLabelTask(_SourceTask):
    """Public scene-package entry point for `threshold_crossing_label`."""

    task_id = "task_charts__waterfall__threshold_crossing_label"
    domain = "charts"
    scene_id = "waterfall"
    objective_contract = "threshold_crossing_label"


__all__ = ["ChartsWaterfallThresholdCrossingLabelTask"]
