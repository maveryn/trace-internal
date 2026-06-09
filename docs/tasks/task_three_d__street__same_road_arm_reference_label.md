# `task_three_d__street__same_road_arm_reference_label`

## Summary
- Domain: `three_d`
- Scene id: `street`
- Task group: `street`
- Query id: `same_road_arm_as_reference`
- Answer type: `option_letter`
- Annotation type: one-box `bbox_set`
- Status: pending_v0_review

## Contract
The image shows a synthetic perspective 3D street intersection or T intersection with roads, sidewalks, crosswalk markings, unlettered street context, one red-boxed reference street object, unlettered street-object candidates, and a below-scene text option panel. The street surface renders full-bleed: sidewalk ground fills the canvas and road strips are clipped to the visible floor-plane polygon, so the roads continue to the image edges rather than ending at a finite stage boundary. The prompt asks which option describes the street object on the same road arm as the red-boxed object.

Each instance renders `6` unlettered candidate street objects. The reference object is unlettered and marked with a red bounding box; its prompt-facing type name is recorded in metadata but not required in the question. Candidate object types exclude the reference type. Exactly one candidate has the same finalized `road_arm` metadata as the reference. Distractor candidates are placed on other present road arms, and T-intersection layouts remove candidates from the missing road arm.

The street context reuses the shared street renderer: buildings, storefronts, trees, shrubs, traffic lights, street signs, and benches can appear as unlettered context. The sampler reserves more slots for large buildings/storefronts, including shopfront facades with awnings, and adds off-road greenery slots while keeping those objects out of answer and annotation semantics. Road layout, sampled intersection-center offset, camera pose, candidate ground positions, and reference/candidate road-arm assignments are recorded in the trace.

## Annotation Contract
Annotation is the bounding box of the selected street object in the scene. The red reference box, road markings, other unlettered context objects, option panel, and option text are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_street_v0` under `prompts/three_d/street/`. The trace records camera pose, projection frame, scene variant, intersection layout, full-bleed floor polygon mode/bounds, present/missing road arms, reference object id/type/name/road arm, candidate road arms by label, same-road-arm flags by label, selected object id/type, projected object bboxes, and option-panel descriptors/bboxes.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D street scene trace.
