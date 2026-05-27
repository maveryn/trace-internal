# task_illustrations__construction_site__material_stack_count

Status: pending fresh v0 task review and solve-rate calibration.

## Identity
- domain: `illustrations`
- scene_id: `construction_site`
- task_group: `counting`
- task: `material_stack_type_count`
- module: `trace/tasks/illustrations/counting/material_stack_type_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a synthetic construction site with labeled zones, workers,
vehicles/equipment, and multiple visible material stacks or bundles.

Query ids:

- `brick_stack_count`
- `pipe_bundle_count`
- `lumber_stack_count`
- `cement_bag_stack_count`

Each variant asks for the count of one material type.

Default sampling uses target answer support `2..6`, with `8..14` visible
material stacks/bundles in the scene.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of rendered material stacks or bundles whose material
  type matches the query

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox around each counted material stack or
  bundle

## Trace Contract
- `render_map.material_bboxes_px` stores final material bboxes by material id.
- `execution_trace.material_type_counts` records the count for every rendered
  material type.
- `render_map.counted_material_ids`,
  `witness_symbolic.counted_material_ids`, and
  `projected_evidence.bbox_set` are derived from the same rendered material
  records.

## Prompt Contract
- `scene_key = construction_site_canvas`
- `task_key = material_stack_type_count_task`
- `query_id` is one of the four material-count branches above
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
