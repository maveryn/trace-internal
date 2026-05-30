# `task_pages__infographic__metric_arithmetic_value`

## Taxonomy
1. Domain: `pages`
2. Scene id: `infographic`
3. Task id: `task_pages__infographic__metric_arithmetic_value`
4. Implementation group: `pages/infographic`

## Contract
Samples one arithmetic query over a multi-section infographic of metric cards.

Query ids: `sum_named_metrics|section_extrema_arithmetic|section_total_extrema_difference|section_total_except_named|section_icon_total_value|section_icon_total_difference_value`.

Answers are integers. Evidence is a `keyed_bbox_map` over the supporting metric-card boxes, keyed by the visible metric-card labels used by the computation.
