# `task_three_d__room__wall_object_side_relation_label`

## Summary
- Domain: `three_d`
- Scene id: `room`
- Scene: `room`
- Supported `query_id` values: `left_of_reference_on_wall`, `right_of_reference_on_wall`
- Answer type: `option_letter`
- Annotation schema: `bbox`

## Contract
The image shows a synthetic perspective 3D indoor room with a floor, back/side walls, furniture, unlettered room context, one unlettered TV mounted on a wall, unlettered wall-mounted candidate objects on that same wall, and a below-scene text option panel. The prompt asks which option describes the wall-mounted object to the left or right of the TV along the wall plane.

Each instance renders `5` unlettered answer candidates on the TV's wall. Exactly one candidate satisfies the sampled side relation: greater wall-plane left coordinate for `left_of_reference_on_wall`, or smaller wall-plane left coordinate for `right_of_reference_on_wall`. Candidate object types exclude TVs so the named reference remains unique.

The TV reference may appear on the back, left, or right wall. The verifier uses the finalized wall coordinate system rather than raw image x-position, so side-wall examples can require reasoning about the room wall plane instead of screen-left.

The renderer uses a lower interior camera, extends the open/front floor toward the camera, keeps side-wall continuation capped to avoid cutaway wall panels, and includes foreground floor context so the scene reads from inside the room. Reference/candidate placement, wall coordinates, side-relation flags, and verifier geometry still use the semantic room coordinates recorded in trace metadata.

## Program Contract
`select(label(candidate_wall_objects, wall_id == reference.wall_id and wall_plane_side(candidate, reference) == requested_side)); scene=room; scope=wall_object_side_relation_label`

The public query id selects `requested_side`: `left_of_reference_on_wall` or `right_of_reference_on_wall`.

## Annotation Contract
Annotation is the bounding box of the selected wall-mounted object in the room scene. The option panel, option text, and unlettered TV reference are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_room_v1` under `prompts/three_d/room/`. The trace records camera pose, projection frame, room scene variant, render-only floor front (`render_front_y`), render-only side-wall front (`render_side_wall_front_y`), bounded semantic room front (`semantic_front_y`), TV reference id/type/name/wall, reference wall coordinate, per-label wall-plane left coordinates, per-label left/right side-relation flags, candidate wall assignments, selected object id/type/wall, projected/visible object bboxes, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D room scene trace.
