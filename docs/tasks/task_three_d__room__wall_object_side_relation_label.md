# `task_three_d__room__wall_object_side_relation_label`

## Summary
- Domain: `three_d`
- Scene id: `room`
- Task group: `room`
- Query id: `left_of_reference_on_wall|right_of_reference_on_wall`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: accepted

## Contract
The image shows a synthetic perspective 3D indoor room with a floor, back/side walls, furniture, unlettered room context, one unlettered TV mounted on a wall, and lettered wall-mounted candidate objects on that same wall. The prompt asks which lettered wall-mounted object is to the left or right of the TV along the wall plane.

Each instance renders `5` lettered answer candidates on the TV's wall. Exactly one candidate satisfies the sampled side relation: greater wall-plane left coordinate for `left_of_reference_on_wall`, or smaller wall-plane left coordinate for `right_of_reference_on_wall`. Candidate object types exclude TVs so the named reference remains unique.

The TV reference may appear on the back, left, or right wall. The verifier uses the finalized wall coordinate system rather than raw image x-position, so side-wall examples can require reasoning about the room wall plane instead of screen-left.

The renderer uses a lower interior camera, extends the open/front floor toward the camera, keeps side-wall continuation capped to avoid cutaway wall panels, and includes foreground floor context so the scene reads from inside the room. Reference/candidate placement, wall coordinates, side-relation flags, and verifier geometry still use the semantic room coordinates recorded in trace metadata.

## Evidence Contract
Evidence is the bounding box of the selected lettered wall-mounted object. The bbox includes the option letter when rendered. The unlettered TV reference is not evidence.

## Prompt And Trace
The prompt bundle is `three_d_room_v0` under `prompts/three_d/room/`. The trace records camera pose, projection frame, room scene variant, render-only floor front (`render_front_y`), render-only side-wall front (`render_side_wall_front_y`), bounded semantic room front (`semantic_front_y`), TV reference id/type/name/wall, reference wall coordinate, per-label wall-plane left coordinates, per-label left/right side-relation flags, candidate wall assignments, selected object id/type/wall, and projected/visible object bboxes.

## Calibration
The manual review workbook and combined room scene review have been regenerated after the render-only open-front room expansion with both side-relation query variants. The exact calibration distribution passed with `5` unique answers and max answer frequency `0.270`. The current qwen25vl7b `100x24` solve-rate probe on seed `20260523` accepted the task with `hard=0.020`, `easy=0.170`, `band=0.810`, `mean=0.518`, response cap `0.000`, and prompt max `142`.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D room scene trace.
