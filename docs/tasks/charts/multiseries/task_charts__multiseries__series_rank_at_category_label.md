# task_charts__multiseries__series_rank_at_category_label

## Overview

- Domain: `charts`
- Scene id: `multiseries`
- Source group: `charts/multiseries`
- Query id: `series_rank_at_category_label`
- Implementation: `trace.tasks.charts.multiseries.comparison_query.ChartsMultiseriesSeriesRankAtCategoryLabelTask`

## Contracts

- Answer schema: `string_label`
- Annotation schema: `keyed_point_map`
- Annotation witnesses: every series mark at the queried category.

## Query Details

| Query id | Program contract | Answer | Annotation |
| --- | --- | --- | --- |
| `series_rank_at_category_label` | `selection.ranked_item_within_group` | `string_label` | `keyed_point_map` |
