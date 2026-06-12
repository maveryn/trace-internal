# `task_three_d__room__wall_object_same_wall_reference_label`

## Summary
- Domain: `three_d`
- Scene id: `room`
- Scene: `room`
- Query id: `same_wall_as_reference`
- Answer type: `option_letter`
- Annotation type: one-box `bbox_set`
- Status: pending_v0_review

## Contract
The image shows a synthetic perspective 3D indoor room with a floor, back/side walls, furniture, unlettered room context, one unlettered named wall reference object, unlettered wall-mounted candidate objects, and a below-scene text option panel. The prompt asks which option describes the wall-mounted object on the same wall as the named reference object.

Each instance renders `6` unlettered answer candidates across the left, back, and right walls. Exactly one candidate is on the reference object's wall. Candidate object types exclude the sampled reference object type, and generation requires the reference prompt name to appear exactly once in finalized scene metadata.

The reference object is sampled from recognizable wall-mounted categories such as TV, clock, mirror, fan, air conditioner, and coat. Extra wall and floor objects provide room context but are excluded from answer options.

The renderer uses a lower interior camera, extends the open/front floor toward the camera, keeps side-wall continuation capped to avoid cutaway wall panels, and includes foreground floor context so the scene reads from inside the room. Reference/candidate placement, wall assignments, same-wall flags, and verifier geometry still use the semantic room coordinates recorded in trace metadata.

## Annotation Contract
Annotation is the bounding box of the selected wall-mounted object in the room scene. The option panel, option text, and named reference object are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_room_v0` under `prompts/three_d/room/`. The trace records camera pose, projection frame, room scene variant, render-only floor front (`render_front_y`), render-only side-wall front (`render_side_wall_front_y`), bounded semantic room front (`semantic_front_y`), reference object id/type/name/wall, per-label same-wall flags, candidate wall assignments, selected object id/type/wall, projected object bboxes, and option-panel descriptors/bboxes.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D room scene trace.
