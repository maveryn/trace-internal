# `task_three_d__warehouse__nearest_candidate_to_reference_label`

## Summary
- Domain: `three_d`
- Scene id: `warehouse`
- Public task id: `task_three_d__warehouse__nearest_candidate_to_reference_label`
- Supported `query_id`: `closest_robot_to_reference`, `closest_object_to_robot`
- Answer schema: `option_letter`
- Annotation schema: `bbox`

## Program Contract
- Program schema: `select(label(candidate_items, argmin(ground_plane_surface_gap_to_reference))); scene=warehouse; scope=nearest_candidate_to_reference_label`
- Scene: `warehouse`
- Scope: `nearest_candidate_to_reference_label`

Render one perspective warehouse aisle with shelf racks, warehouse equipment, one reference item, five candidate items, and a text option panel below the scene.

For `closest_robot_to_reference`, the reference is a red sphere and the candidates are five robots. The answer is the option label for the robot with the smallest finalized ground-plane surface gap to the red sphere.

For `closest_object_to_robot`, the reference is one robot and the candidates are five warehouse objects. The answer is the option label for the object with the smallest finalized ground-plane surface gap to the robot.

Both query ids use the same program contract: identify the nearest candidate to the visible reference by metadata-grounded floor-plane distance. The generator enforces a unique nearest margin. Annotation is the scalar bounding box `[x0, y0, x1, y1]` of the selected candidate in the scene. The reference object, shelf racks, context objects, option panel, and option text are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_warehouse_v1` under `prompts/three_d/warehouse/`. The trace records camera pose, projection frame, scene variant, aisle heading, reference metadata, candidate labels/types, robot designs/headings/colors where applicable, nearest-distance order, per-label distances to the reference, selected object id, projected bboxes, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answer and annotation come from the same finalized 3D warehouse scene trace.
