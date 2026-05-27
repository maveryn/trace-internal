# task_illustrations__market__shop_attribute_count

Status: pending fresh v0 task review and solve-rate calibration.

## Identity
- domain: `illustrations`
- scene_id: `market`
- task_group: `counting`
- task: `market_shop_attribute_count`
- module: `trace/tasks/illustrations/counting/market_shop_attribute_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a synthetic urban market with shops or stalls, signs,
awnings, facades, and visible merchandise.

Query ids:

- `shop_category_count`
- `signboard_color_count`
- `awning_color_count`
- `facade_color_count`
- `shop_selling_object_count`

## Answer Contract
- `answer_gt.type = integer`
- value is the count requested by the selected `query_id`

## Evidence Contract
- `evidence_gt.type = bbox_set`
- category and selling-object queries return shop/stall bboxes
- color queries return the queried surface bboxes

## Trace Contract
- `query_spec.task_id` is this public task id.
- `query_spec.branch_id` records the private branch generator used for the
  selected query.
- `query_spec.params.merged_query_probabilities` records query
  sampling support.
- Branch-specific render maps and witness fields are preserved.

## Prompt Contract
- `scene_key = urban_market_canvas`
- `query_id` is the selected branch
- branch-specific task keys from `illustrations_counting_v0` are reused
