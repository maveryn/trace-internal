# `task_three_d__warehouse__robot_forward_path_label`

## Summary
- Domain: `three_d`
- Scene id: `warehouse`
- Scene: `warehouse`
- Query id: `first_object_ahead`
- Answer type: `option_letter`
- Annotation type: one-box `bbox_set`
- Status: pending_v0_review

## Contract
The image shows a synthetic perspective 3D warehouse aisle with a gridded full-bleed floor, shelf racks, warehouse equipment, one red-boxed robot with a red travel-direction arrow, unlettered warehouse-object candidates, and a below-scene text option panel. The robot body varies across low-cart, sensor-tower, and stacker-like designs with sampled base/accent colors while remaining the red-boxed reference object. The prompt asks which option describes the object the robot will reach first if it moves straight along the arrow.

Each instance renders `5` unlettered answer candidates plus unlettered warehouse context. Exactly two candidates lie in the robot's finalized forward path corridor; the answer is the nearest one by positive forward distance from the robot. Distractors can be behind the robot, beside the robot, in an adjacent aisle, or farther off the path. Shelf racks are spaced wider than the center aisle and may extend partly out of frame as render-only warehouse context; rack style is randomized across open frames, loaded bin racks, mixed-crate racks, tall sparse racks, and heavier low racks. Rack frame colors, stored-load colors, and rack heights vary by sampled metadata. The scene includes diverse warehouse object types such as shelf racks, loaded pallets, crate stacks, barrels, carts, pallet jacks, forklifts, cable spools, tire stacks, barriers, bins, ladders, workbenches, rolling bins, trash cans, bollards, wrapped bundles, fire extinguishers, hand trucks, and stacked pipes.

The verifier uses finalized metadata, not pixels: robot world position, travel direction vector, path corridor half-width, candidate forward distance from the robot, candidate lateral offset from the robot, and the unique first-reached candidate flag.

## Annotation Contract
Annotation is the bounding box of the selected warehouse object in the scene. The red robot box, red arrow, highlighted path corridor, shelf racks, unlettered context, option panel, and option text are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_warehouse_v0` under `prompts/three_d/warehouse/`. The trace records camera pose, projection frame, scene variant, robot heading/design/color metadata, shelf rack styles/frame colors/heights/load slots, travel direction vector, path corridor polygon, candidate object types by label, forward and lateral path coordinates by label, first-reached flags by label, selected object id/type, projected object bboxes, and option-panel descriptors/bboxes.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D warehouse scene trace.
