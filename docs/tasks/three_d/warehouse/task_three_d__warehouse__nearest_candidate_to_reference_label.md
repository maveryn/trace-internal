# `task_three_d__warehouse__nearest_candidate_to_reference_label`

## Summary
- Domain: `three_d`
- Scene id: `warehouse`
- Scene: `warehouse`
- Query ids: `closest_robot_to_reference`, `closest_object_to_robot`
- Answer type: `option_letter`
- Annotation type: one-box `bbox_set`

## Contract
The image shows a synthetic perspective 3D warehouse aisle with a gridded full-bleed floor, far-side shelf racks, lower warehouse equipment nearer the camera, one unlettered reference item, `5` unlettered candidates, and a below-scene text option panel.

For `closest_robot_to_reference`, the reference is an unlettered red sphere and the candidates are `5` unlettered robots described in the option panel. The prompt asks which option describes the robot closest to the red sphere. The verifier uses finalized metadata, not pixels: the red sphere world position, each robot's finalized floor-plane footprint, the surface gap from each robot to the reference object, and a unique nearest margin.

For `closest_object_to_robot`, the reference is one unlettered robot and the candidates are `5` unlettered warehouse objects described in the option panel. The prompt asks which option describes the warehouse object closest to the robot. The verifier uses the robot's finalized floor-plane footprint, each candidate object's finalized footprint, the candidate-to-robot surface gap, and a unique nearest margin.

## Annotation Contract
Annotation is the bounding box of the selected candidate in the scene: a robot for `closest_robot_to_reference`, or a warehouse object for `closest_object_to_robot`. The red sphere, reference robot, shelf racks, unlettered warehouse context, option panel, and option text are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_warehouse_v0` under `prompts/three_d/warehouse/`. The trace records camera pose, projection frame, scene variant, aisle heading, reference metadata, candidate labels/types, robot designs/headings/colors where applicable, nearest-distance order, per-label distances to the reference, selected object id, projected object bboxes, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D warehouse scene trace.
