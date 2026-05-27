# `task_three_d__warehouse__robot_nearest_object_label`

## Summary
- Domain: `three_d`
- Scene id: `warehouse`
- Task group: `warehouse`
- Query ids: `closest_robot_to_reference`, `closest_object_to_robot`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: reviewed_pending_probe

## Contract
The image shows a synthetic perspective 3D warehouse aisle with a gridded full-bleed floor, far-side shelf racks, lower warehouse equipment nearer the camera, one unlettered reference item, and `5` lettered candidates.

For `closest_robot_to_reference`, the reference is an unlettered red sphere and the candidates are `5` lettered robots. The prompt asks which lettered robot is closest to the red sphere. The verifier uses finalized metadata, not pixels: the red sphere world position, each robot's finalized floor-plane footprint, the surface gap from each robot to the reference object, and a unique nearest margin.

For `closest_object_to_robot`, the reference is one unlettered robot and the candidates are `5` lettered warehouse objects. The prompt asks which lettered warehouse object is closest to the robot. The verifier uses the robot's finalized floor-plane footprint, each candidate object's finalized footprint, the candidate-to-robot surface gap, and a unique nearest margin.

## Evidence Contract
Evidence is the bounding box of the selected lettered candidate: a robot for `closest_robot_to_reference`, or a warehouse object for `closest_object_to_robot`. The bbox includes the option letter when rendered. The red sphere, reference robot, shelf racks, and unlettered warehouse context are not evidence.

## Prompt And Trace
The prompt bundle is `three_d_warehouse_v0` under `prompts/three_d/warehouse/`. The trace records camera pose, projection frame, scene variant, aisle heading, reference metadata, candidate labels/types, robot designs/headings/colors where applicable, nearest-distance order, per-label distances to the reference, selected object id, and projected object bboxes.

## Calibration
The manual review workbook, distribution report, and combined warehouse scene review have been regenerated. Distribution passed with `100` samples per query variant, `5` unique answers per variant, max per-variant answer frequency `0.270`, and overall max answer frequency `0.235`. Solve-rate calibration is pending.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D warehouse scene trace.
