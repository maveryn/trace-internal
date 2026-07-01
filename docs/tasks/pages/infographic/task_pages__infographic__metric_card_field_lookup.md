# `task_pages__infographic__metric_card_field_lookup`

## Identity
1. Domain: `pages`
2. Scene id: `infographic`
3. Source path: `trace/tasks/pages/infographic/metric_card_field_lookup.py`
4. Task id: `task_pages__infographic__metric_card_field_lookup`

## Program Contract
1. Program schema: `lookup.metric_card_field(field=value|label|reference_code); scene=infographic; scope=one multi-section metric-card infographic`
2. Contract: find the unique metric card in a named section using the prompt's resolved label or value, then return the requested visible field from that same card.
3. Public query ids: `value_for_named_item`, `item_for_named_value`, `detail_for_named_item`
4. Answer schema: `string`
5. Annotation schema: scalar `bbox` around the supporting metric card.
6. Query argument axes: requested field/direction, target section, target card label or visible value.
7. scalar_annotation_checked=true

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v1`
2. Scene key: `infographic_metric_arithmetic`
3. Task key: `metric_arithmetic_query`
4. Trace records the source query id, target card, target section, visible value/detail text, answer string, and supporting card bbox.
5. Generation guarantees a unique card for the requested lookup.
6. Numeric reference captions (`Ref ##`) are rendered only for the `detail_for_named_item` query branch. Other infographic branches use non-numeric card tags so reference captions are not confused with metric values.
