"""Compatibility exports for infographic metric-card page tasks."""

from __future__ import annotations

from .metric_common import (
    ALL_QUERY_IDS,
    COLUMN_PROFILE_COMPARISON_VARIANTS,
    FACT_LOOKUP_VARIANTS,
    FILTERED_METRIC_TOTAL_VARIANTS,
    FILTERED_SECTION_EXTREMUM_VARIANTS,
    METRIC_RANKED_ITEM_VARIANTS,
    SECTION_RANKED_TOTAL_VARIANTS,
    SUPPORTED_QUERY_IDS,
)
from .metric_task import (
    PagesInfographicDetailForNamedItemTask,
    PagesInfographicItemForNamedValueTask,
    PagesInfographicMetricArithmeticValueTask,
    PagesInfographicMetricRankedItemLabelTask,
    PagesInfographicSectionExtremaArithmeticValueTask,
    PagesInfographicSectionIconExtremumLabelTask,
    PagesInfographicSectionIconTotalDifferenceValueTask,
    PagesInfographicSectionIconTotalValueTask,
    PagesInfographicSectionRankedTotalLabelTask,
    PagesInfographicSectionTotalExceptNamedValueTask,
    PagesInfographicSectionTotalExtremaDifferenceValueTask,
    PagesInfographicSumNamedMetricsValueTask,
    PagesInfographicValueForNamedItemTask,
)

__all__ = [
    "ALL_QUERY_IDS",
    "COLUMN_PROFILE_COMPARISON_VARIANTS",
    "FACT_LOOKUP_VARIANTS",
    "FILTERED_SECTION_EXTREMUM_VARIANTS",
    "FILTERED_METRIC_TOTAL_VARIANTS",
    "METRIC_RANKED_ITEM_VARIANTS",
    "PagesInfographicDetailForNamedItemTask",
    "PagesInfographicItemForNamedValueTask",
    "PagesInfographicMetricArithmeticValueTask",
    "PagesInfographicMetricRankedItemLabelTask",
    "PagesInfographicSectionExtremaArithmeticValueTask",
    "PagesInfographicSectionIconExtremumLabelTask",
    "PagesInfographicSectionIconTotalDifferenceValueTask",
    "PagesInfographicSectionIconTotalValueTask",
    "PagesInfographicSectionRankedTotalLabelTask",
    "PagesInfographicSectionTotalExceptNamedValueTask",
    "PagesInfographicSectionTotalExtremaDifferenceValueTask",
    "PagesInfographicSumNamedMetricsValueTask",
    "PagesInfographicValueForNamedItemTask",
    "SECTION_RANKED_TOTAL_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
