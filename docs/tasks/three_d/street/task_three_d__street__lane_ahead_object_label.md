# `task_three_d__street__lane_ahead_object_label`

## Summary
- Domain: `three_d`
- Scene id: `street`
- Scene package: `street`
- Supported `query_id`: `single`
- Answer type: `option_letter`
- Annotation schema: `bbox`

## Program Contract
`select(label(candidate_street_objects, predicate=same_lane_and_ahead_of_reference)); scene=street; scope=lane_ahead_object_label`

The public query id is `single`; ahead-along-lane selection is the fixed objective contract.

## Contract
The image shows a synthetic perspective 3D street intersection or T intersection with roads, sidewalks, crosswalk markings, unlettered street context, one red-boxed reference street object with a red travel-direction arrow, unlettered street-object candidates, and a below-scene text option panel.

Each instance renders `5` unlettered candidate street objects plus unlettered street context. The reference object is an unlettered car marked with a red bounding box and red direction arrow. Exactly one candidate is ahead of the reference along the same finalized lane corridor and travel direction. Distractors include objects behind the reference, objects ahead in an adjacent lane, objects off the lane, and objects on other present road arms.

The verifier uses finalized metadata, not pixels: reference road arm, lane id, travel direction vector, candidate forward distance from the reference, candidate lateral distance from the reference lane, and candidate road arm.

## Annotation Contract
Annotation is the bounding box of the selected street object in the scene. The red reference box, red arrow, road markings, context objects, option panel, and option text are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_street_v1` under `prompts/three_d/street/`. The trace records camera pose, projection frame, scene variant, intersection layout, present/missing road arms, travel mode, reference road arm/lane/direction, candidate road arms by label, forward and lateral lane distances by label, ahead flags by label, selected object id/type, projected object bboxes, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D street scene trace.
