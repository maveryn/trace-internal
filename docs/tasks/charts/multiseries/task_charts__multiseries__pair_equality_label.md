# task_charts__multiseries__pair_equality_label

## Overview

- Domain: `charts`
- Scene id: `multiseries`
- Source group: `charts/multiseries`
- Query id: `pair_equality_label`
- Implementation: `trace.tasks.charts.multiseries.comparison_query.ChartsMultiseriesPairEqualityLabelTask`

## Contracts

- Answer schema: `string_label`
- Annotation schema: `keyed_point_map`
- Annotation witnesses: the two queried series marks in the answer category.

## Query Details

| Query id | Program contract | Answer | Annotation |
| --- | --- | --- | --- |
| `pair_equality_label` | `selection.exact_pair_equality_label` | `string_label` | `keyed_point_map` |
