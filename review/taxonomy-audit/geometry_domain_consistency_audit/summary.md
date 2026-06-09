# Geometry Domain Consistency Audit

Date: 2026-06-05

## Scope

- Active geometry inventory: 170 public tasks across 39 scenes.
- Review root: `review/task-reviews`.
- This pass did not change task ids, task count, scene count, answer contracts, or annotation ground-truth geometry.
- Solve-rate calibration was not run in this pass.

## Fixes Applied

- Corrected stale bbox notation in geometry measurement prompt hints from `[x1,y1,x2,y2]` to `[x0,y0,x1,y1]` for:
  - `task_geometry__container_volume_transfer__fill_count_value`
  - `task_geometry__container_volume_transfer__resulting_height_value`
  - `task_geometry__container_volume_transfer__target_capacity_value`
  - `task_geometry__rectangular_solid__cube_edge_from_frame_length_value`
  - `task_geometry__rectangular_solid__open_box_net_dimension_value`
- Added a shared geometry measurement helper for non-semantic readout label backplates.
- Applied backed readout labels to the geometry scenes that failed runtime text-legibility coverage:
  - `circle_pair_tangents`
  - `circle_polygon_composite`
  - `rectangular_solid`
  - `survey_traverse`
- Added explicit backed-label contrast metadata so the runtime audit checks the intended rendered label surface instead of sampling nearby geometry strokes for very small labels.
- Routed survey required readout text away from low-contrast accent ink when needed.

## Review Artifacts Regenerated

Regenerated full task reviews and scene workbooks under `review/task-reviews` for:

- `circle_pair_tangents` tasks: 2
- `circle_polygon_composite` tasks: 2
- `container_volume_transfer` tasks: 3
- `rectangular_solid` tasks: 4
- `survey_traverse` tasks: 3

The review app index was reloaded successfully. The affected scene pages returned HTTP 200 after reload.

## Checks Run

- `python -m py_compile` on changed geometry modules.
- `PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py --tasks <all geometry tasks> ...`
  - Result: 170 tasks, 238 query ids, 238 samples, 0 issues.
- `PYTHONPATH=. python scripts/audit_text_legibility.py --root . --scan-root trace/tasks/geometry --strict-renderer-migration --strict-role-metadata --strict-font-routing --max-renderer-findings 120`
  - Result: passed.
- `PYTHONPATH=. python scripts/audit_text_legibility.py --root . --runtime-coverage --runtime-domain geometry --runtime-sample-count 1 --runtime-max-attempts 3 --fail-generation-errors`
  - Result: passed.
- `PYTHONPATH=. python scripts/audit_marker_legibility.py --root . --runtime-coverage --runtime-domain geometry --runtime-sample-count 1 --runtime-max-attempts 3 --max-findings 120`
  - Result: passed.
- `PYTHONPATH=. python scripts/check_active_inventory_integrity.py`
  - Result: passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_geometry_circle_pair_tangents_tasks.py tests/test_geometry_circle_polygon_composite_tasks.py tests/test_geometry_rectangular_solid_tasks.py tests/test_geometry_survey_traverse_tasks.py tests/test_geometry_container_volume_transfer_tasks.py`
  - Result: 63 passed.

## Open Reviewer Issues

Two geometry issues remain open in `review/feedback/review_feedback.sqlite`. Both point at retired public task ids and already have prior agent repair notes. They were not marked resolved in this pass because reviewer issue resolution is human-owned.
