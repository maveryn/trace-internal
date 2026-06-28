# `task_three_d__warehouse__robot_forward_path_label`

## Summary
- Domain: `three_d`
- Scene id: `warehouse`
- Public task id: `task_three_d__warehouse__robot_forward_path_label`
- Supported `query_id`: `single`
- Answer schema: `option_letter`
- Annotation schema: `bbox`

## Program Contract
- Program schema: `select(label(candidate_objects, argmin(positive_forward_distance_in_robot_path_corridor))); scene=warehouse; scope=robot_forward_path_label`
- Scene: `warehouse`
- Scope: `robot_forward_path_label`

Render one perspective warehouse aisle with shelf racks, warehouse equipment, one red-boxed robot, a red travel-direction arrow, candidate warehouse objects, and a text option panel below the scene. The robot body may vary across low-cart, sensor-tower, and stacker-like designs while remaining the red-boxed reference.

The prompt asks which option describes the object the robot reaches first if it continues straight along the red arrow. The generator places four small candidate objects, with at least two candidates in the finalized forward path corridor. The answer is the candidate with the smallest positive forward distance from the robot within the corridor. Distractors may be behind the robot, beside the path, in adjacent aisle context, or farther along the path.

Annotation is the scalar bounding box `[x0, y0, x1, y1]` of the selected warehouse object in the scene. The red robot box, red arrow, highlighted path corridor, shelf racks, context objects, option panel, and option text are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_warehouse_v1` under `prompts/three_d/warehouse/`. The trace records camera pose, projection frame, scene variant, robot heading/design/color metadata, travel direction vector, path corridor polygon, candidate object types by label, forward/lateral path coordinates by label, first-reached flags by label, selected object id/type, projected bboxes, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answer and annotation come from the same finalized 3D warehouse scene trace.
