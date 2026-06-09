# `task_physics__motion_graph__interval_displacement_value`

## Summary
- Domain: `physics`
- Scene id: `motion_graph`
- Implementation task group: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/motion_graph.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__motion_graph__interval_displacement_value` -> `task_physics__motion_graph__interval_displacement_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes the integer displacement over a marked interval on a velocity-time graph.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids vary only whether the velocity segment is constant or linearly changing over the marked interval.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `constant_velocity_interval_displacement` | `integer(area_under_velocity_time_curve(marked_interval, segment_mode=constant_velocity)); scene=motion_graph; scope=interval_displacement_value` |
| `constant_acceleration_interval_displacement` | `integer(area_under_velocity_time_curve(marked_interval, segment_mode=constant_acceleration)); scene=motion_graph; scope=interval_displacement_value` |

## Program Metadata
- Program signatures: `physics.motion_graph_interval_displacement`
- Base program contract: `integer(area_under_velocity_time_curve(marked_interval, segment_mode=constant_velocity_or_constant_acceleration)); scene=motion_graph; scope=interval_displacement_value`
- Parameter axes: `query_id`, `scene_variant`, `interval_width`, `velocity_endpoints`
- Arguments:
  - `marked_interval`: semantic_role; allowed `highlighted_time_interval_on_velocity_time_graph`; source `program_schema_concrete`
  - `velocity_segment`: semantic_role; allowed `constant_or_linearly_changing_velocity_segment`; source `program_schema_concrete`
  - `axis_scale`: semantic_role; allowed `visible_integer_time_and_velocity_axis_scale`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `constant_velocity_interval_displacement`, `constant_acceleration_interval_displacement`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the displacement in meters over the marked interval.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys are `marked_interval`, `velocity_segment`, and `axis_scale`.
- Annotation must mark minimal visual witnesses from the final rendered graph, not a derived displacement annotation, prompt-only formula, decorative panel chrome, or unrelated graph segments.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Rendered graphs must be velocity-time graphs with nonnegative velocities over the marked interval.
- Constant-velocity intervals use rectangle area `v * delta_t`; constant-acceleration intervals use trapezoid area `((v_start + v_end) / 2) * delta_t`.
- Endpoint values and interval widths must be sampled so the answer is integer-valued.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/motion_graph/task_physics__motion_graph__interval_displacement_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
