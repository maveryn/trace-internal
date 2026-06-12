"""Chart scene package tasks."""

from .cross_panel_delta_extremum_label import ChartsScientificCrossPanelDeltaExtremumLabelTask
from .cross_panel_threshold_earliest_label import ChartsScientificCrossPanelThresholdEarliestLabelTask
from .curve_at_x_extremum_label import ChartsScientificCurveAtXExtremumLabelTask
from .curve_intersection_count import ChartsScientificCurveIntersectionCountTask
from .earliest_maximum_panel_label import ChartsScientificEarliestMaximumPanelLabelTask
from .panel_curve_threshold_crossing_count import ChartsScientificPanelCurveThresholdCrossingCountTask
from .panel_point_threshold_count import ChartsScientificPanelPointThresholdCountTask
from .threshold_series_count import ChartsScientificThresholdSeriesCountTask

__all__ = [
    "ChartsScientificCrossPanelDeltaExtremumLabelTask",
    "ChartsScientificCrossPanelThresholdEarliestLabelTask",
    "ChartsScientificCurveAtXExtremumLabelTask",
    "ChartsScientificCurveIntersectionCountTask",
    "ChartsScientificEarliestMaximumPanelLabelTask",
    "ChartsScientificPanelCurveThresholdCrossingCountTask",
    "ChartsScientificPanelPointThresholdCountTask",
    "ChartsScientificThresholdSeriesCountTask",
]
