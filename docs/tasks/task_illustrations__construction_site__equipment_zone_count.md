# task_illustrations__construction_site__equipment_zone_count

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Identity
- domain: `illustrations`
- scene_id: `construction_site`
- task_group: `counting`
- task: `equipment_in_zone_count`
- module: `trace/tasks/illustrations/counting/equipment_in_zone_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a synthetic construction site with visible labeled zones:
Excavation Zone, Loading Zone, and Roadwork Zone. Construction equipment items
are placed by semantic zone before rendering.

Query ids:

- `vehicle_in_excavation_zone_count`
- `vehicle_in_loading_zone_count`
- `vehicle_in_roadwork_zone_count`

Each variant asks how many construction vehicles or equipment items are in the
named zone.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of rendered equipment items assigned to the queried zone

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox around each counted construction vehicle
  or equipment item

## Trace Contract
- `render_map.equipment_bboxes_px` stores final equipment bboxes by equipment
  id.
- `execution_trace.equipment_zone_counts` records counts by semantic zone.
- `render_map.counted_equipment_ids`,
  `witness_symbolic.counted_equipment_ids`, and
  `projected_evidence.bbox_set` are derived from the same rendered equipment
  records.
- `render_spec.style.layout.zone_label_font` records the single global-pool
  font family used consistently for all visible construction-zone labels.

## Prompt Contract
- `scene_key = construction_site_canvas`
- `task_key = equipment_in_zone_count_task`
- `query_id` is one of the three zone-count branches above
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
