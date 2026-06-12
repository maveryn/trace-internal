# `task_three_d__room__multi_attribute_and_count`

## Summary
- Domain: `three_d`
- Scene id: `room`
- Scene: `room`
- Query ids: `tv_wall_mounted_count`, `clock_wall_mounted_count`, `picture_frame_wall_mounted_count`, `mirror_wall_mounted_count`, `wall_shelf_wall_mounted_count`, `wall_fan_wall_mounted_count`, `air_conditioner_wall_mounted_count`, `hanging_coat_wall_mounted_count`
- Answer type: `integer`
- Annotation type: `bbox_set`
- Status: pending_v0_review

## Contract
The image shows a synthetic perspective 3D indoor room with a floor, back/side walls, furniture, wall-mounted objects, and same-type non-wall distractors on furniture or the floor. Query ids ask how many target objects of one type are mounted or hanging on the walls.

Generation samples a target object type from TVs, clocks, picture frames, mirrors, wall shelves, wall fans, air conditioners, and hanging coats, then constructs a target count from the configured support. Same-type non-wall distractors are always included so the task requires the wall-mounted relation, not just object-type counting. TVs, clocks, and picture frames can appear on tables, desks, beds, or media consoles with `mounting=on_furniture` and support metadata; picture frames render one of a small set of simple scenery paintings while still being prompt-facing picture frames.

The renderer uses a lower interior camera, extends the open/front floor toward the camera, keeps side-wall continuation capped to avoid cutaway wall panels, and includes at least one foreground floor prop so the scene reads from inside the room. Object placement, wall assignments, counts, and verifier geometry still use the semantic room coordinates recorded in trace metadata.

## Annotation Contract
Annotation is the ordered set of bounding boxes around the wall-mounted target objects only. If the target count is zero, annotation is an empty `bbox_set`.

## Prompt And Trace
The prompt bundle is `three_d_room_v0` under `prompts/three_d/room/`. The trace records camera pose, projection frame, room scene variant, render-only floor front (`render_front_y`), render-only side-wall front (`render_side_wall_front_y`), bounded semantic room front (`semantic_front_y`), wall/floor object specs, wall mounting metadata, furniture support metadata for on-furniture distractors, picture-frame scenery metadata, object-type counts split by wall versus floor objects, and the target object ids used by the verifier.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D room scene trace.
