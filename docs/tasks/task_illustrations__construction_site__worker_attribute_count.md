# task_illustrations__construction_site__worker_attribute_count

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Identity
- domain: `illustrations`
- scene_id: `construction_site`
- task_group: `counting`
- task: `worker_safety_gear_count`
- module: `trace/tasks/illustrations/counting/worker_safety_gear_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a varied synthetic construction site with workers, labeled
zones, material stacks, construction equipment, scaffold/crane/roadwork decor,
and one of the active illustration styles.

Query ids:

- `hard_hat_color_worker_count`
- `vest_color_worker_count`
- `tool_holding_worker_count`

Each variant asks for the count of workers matching one visible safety-gear or
tool condition.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of rendered workers matching the queried condition

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox around each counted worker

## Trace Contract
- `scene_ir.entities` contains `construction_worker`,
  `construction_material`, `construction_equipment`, `construction_zone`, and
  construction decor records.
- `render_map.worker_bboxes_px` stores final worker bboxes by worker id.
- `render_map.counted_worker_ids`, `witness_symbolic.counted_worker_ids`, and
  `projected_evidence.bbox_set` are derived from the same rendered worker
  records.
- `render_spec.style.layout.zone_label_font` records the single global-pool
  font family used consistently for all visible construction-zone labels.

## Prompt Contract
- `scene_key = construction_site_canvas`
- `task_key = worker_safety_gear_count_task`
- `query_id` is one of the three worker-safety branches above
- color query prompts use color names with hex codes, for example
  `orange [#E87E36]`
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
