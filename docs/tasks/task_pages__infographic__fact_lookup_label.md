# `task_pages__infographic__fact_lookup_label`

## Taxonomy
1. Domain: `pages`
2. Scene id: `infographic`
3. Task id: `task_pages__infographic__fact_lookup_label`
4. Implementation group: `pages/infographic`

## Contract
Looks up one exact visible fact from a dense multi-section infographic of metric cards.

Query ids: `value_for_named_item|item_for_named_value|detail_for_named_item`.

Answers are exact visible strings: a printed value, a metric-card label, or a `Ref NN` code. Evidence is a `keyed_bbox_map` containing the supporting metric-card box keyed by the visible metric-card label.
