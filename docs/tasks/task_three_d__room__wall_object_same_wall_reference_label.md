# `task_three_d__room__wall_object_same_wall_reference_label`

## Summary
- Domain: `three_d`
- Scene id: `room`
- Task group: `room`
- Query id: `same_wall_as_reference`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: reviewed pending probe

## Contract
The image shows a synthetic perspective 3D indoor room with a floor, back/side walls, furniture, unlettered room context, one unlettered named wall reference object, and lettered wall-mounted objects. The prompt asks which lettered wall-mounted object is on the same wall as the named reference object.

Each instance renders `6` lettered answer candidates across the left, back, and right walls. Exactly one lettered candidate is on the reference object's wall. Candidate object types exclude the sampled reference object type, and generation requires the reference prompt name to appear exactly once in finalized scene metadata.

The reference object is sampled from recognizable wall-mounted categories such as TV, clock, mirror, fan, air conditioner, hanging plant, and coat. Extra wall and floor objects provide room context but are excluded from answer options.

The renderer uses a lower interior camera, extends the open/front floor toward the camera, keeps side-wall continuation capped to avoid cutaway wall panels, and includes foreground floor context so the scene reads from inside the room. Reference/candidate placement, wall assignments, same-wall flags, and verifier geometry still use the semantic room coordinates recorded in trace metadata.

## Evidence Contract
Evidence is the bounding box of the selected lettered wall-mounted object. The bbox includes the option letter when rendered. The named reference object is not evidence.

## Prompt And Trace
The prompt bundle is `three_d_room_v0` under `prompts/three_d/room/`. The trace records camera pose, projection frame, room scene variant, render-only floor front (`render_front_y`), render-only side-wall front (`render_side_wall_front_y`), bounded semantic room front (`semantic_front_y`), reference object id/type/name/wall, per-label same-wall flags, candidate wall assignments, selected object id/type/wall, and projected object bboxes.

## Calibration
The manual review workbook and combined room scene review have been regenerated after the render-only open-front room expansion. The exact calibration distribution passed with `6` unique answers and max answer frequency `0.220`. The current qwen25vl7b `100x24` solve-rate probe on seed `20260523` accepted the task with `hard=0.110`, `easy=0.030`, `band=0.860`, `mean=0.274`, response cap `0.000`, and prompt max `139`.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D room scene trace.
