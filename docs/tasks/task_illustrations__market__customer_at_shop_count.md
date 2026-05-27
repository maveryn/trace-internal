# task_illustrations__market__customer_at_shop_count

Status: pending fresh v0 task review and solve-rate calibration.

## Identity
- domain: `illustrations`
- scene_id: `market`
- task_group: `counting`
- task: `customer_at_shop_type_count`
- module: `trace/tasks/illustrations/counting/customer_at_shop_type_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a synthetic urban market with shop or stall fronts, category
signs, awnings, counters, street/plaza backgrounds, dirt pedestrian paths, and
semantic customer figures placed near specific shops. It uses the
customer-plaza market layout with `8..12` shops or stalls and `6..12` customer
figures on a `1280x960` canvas. Customers are placed close to their associated
shop fronts rather than in the middle of the path.

The task records
`query_id=customer_at_shop_type_count`. The query asks how many customers are
standing at shops or stalls with a named sign label.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of customer figures whose nearby shop/stall type matches
  the queried label

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted customer figure
- evidence boxes are sorted deterministically by rendered position

## Trace Contract
- `scene_ir.entities` contains `market_shop`, optional `market_item`, and
  `market_decor` entities.
- customer figures are represented as `market_decor` entities with
  `decor_type=customer`.
- each customer records `near_shop_id`, `near_shop_type`, `near_shop_label`,
  and `customer_object_type`.
- `render_map.customer_bboxes_px` stores customer bboxes by customer id.
- `render_map.counted_customer_ids`, `witness_symbolic.counted_customer_ids`,
  and `projected_evidence.bbox_set` are derived from the same rendered customer
  records.

## Prompt Contract
- `scene_key = urban_market_canvas`
- `task_key = customer_at_shop_type_count_task`
- `query_id = customer_at_shop_type_count`
- prompts ask for customers at shops or stalls labeled with a named sign
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
