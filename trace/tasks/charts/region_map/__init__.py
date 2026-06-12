"""Chart scene package tasks."""

from .adjacent_category_count import ChartsMapAdjacentCategoryCountTask
from .adjacent_numeric_threshold_count import ChartsMapAdjacentNumericThresholdCountTask
from .adjacent_same_category_count import ChartsMapAdjacentSameCategoryCountTask
from .categorical_region_count import ChartsMapCategoricalRegionCountTask
from .continent_category_region_count import ChartsMapContinentCategoryRegionCountTask
from .continent_region_count import ChartsMapContinentRegionCountTask
from .continent_threshold_region_count import ChartsMapContinentThresholdRegionCountTask
from .group_filtered_region_value import ChartsMapGroupFilteredRegionValueTask
from .named_region_set_total_value import ChartsMapNamedRegionSetTotalValueTask
from .numeric_interval_region_count import ChartsMapNumericIntervalRegionCountTask
from .numeric_threshold_region_count import ChartsMapNumericThresholdRegionCountTask

__all__ = [
    "ChartsMapAdjacentCategoryCountTask",
    "ChartsMapAdjacentNumericThresholdCountTask",
    "ChartsMapAdjacentSameCategoryCountTask",
    "ChartsMapCategoricalRegionCountTask",
    "ChartsMapContinentCategoryRegionCountTask",
    "ChartsMapContinentRegionCountTask",
    "ChartsMapContinentThresholdRegionCountTask",
    "ChartsMapGroupFilteredRegionValueTask",
    "ChartsMapNamedRegionSetTotalValueTask",
    "ChartsMapNumericIntervalRegionCountTask",
    "ChartsMapNumericThresholdRegionCountTask",
]
