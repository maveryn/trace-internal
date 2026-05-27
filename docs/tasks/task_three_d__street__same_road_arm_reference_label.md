# `task_three_d__street__same_road_arm_reference_label`

## Summary
- Domain: `three_d`
- Scene id: `street`
- Task group: `street`
- Query id: `same_road_arm_as_reference`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: reviewed_pending_probe

## Contract
The image shows a synthetic perspective 3D street intersection or T intersection with roads, sidewalks, crosswalk markings, unlettered street context, one red-boxed reference street object, and lettered street objects. The street surface renders full-bleed: sidewalk ground fills the canvas and road strips are clipped to the visible floor-plane polygon, so the roads continue to the image edges rather than ending at a finite stage boundary. The prompt asks which lettered street object is on the same road arm as the red-boxed object.

Each instance renders `6` lettered candidate street objects. The reference object is unlettered and marked with a red bounding box; its prompt-facing type name is recorded in metadata but not required in the question. Candidate object types exclude the reference type. Exactly one lettered candidate has the same finalized `road_arm` metadata as the reference. Distractor candidates are placed on other present road arms, and T-intersection layouts remove candidates from the missing road arm.

The street context reuses the shared street renderer: buildings, storefronts, trees, shrubs, traffic lights, street signs, and benches can appear as unlettered context. The sampler reserves more slots for large buildings/storefronts, including shopfront facades with awnings, and adds off-road greenery slots while keeping those objects out of answer and evidence semantics. Road layout, sampled intersection-center offset, camera pose, candidate ground positions, and reference/candidate road-arm assignments are recorded in the trace.

## Evidence Contract
Evidence is the bounding box of the selected lettered street object. The bbox includes the option letter when rendered. The red reference box, road markings, and other unlettered context objects are not evidence.

## Prompt And Trace
The prompt bundle is `three_d_street_v0` under `prompts/three_d/street/`. The trace records camera pose, projection frame, scene variant, intersection layout, full-bleed floor polygon mode/bounds, present/missing road arms, reference object id/type/name/road arm, candidate road arms by label, same-road-arm flags by label, selected object id/type, and projected object bboxes.

## Calibration
The red-box reference-marker update has focused unit coverage. The refreshed manual review workbook, distribution report, and combined street scene review have been regenerated. Distribution review passed with `6` unique answers and max answer frequency `0.220`; solve-rate calibration for the red-box version is pending.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D street scene trace.
