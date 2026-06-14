# `task_three_d__room__wall_object_camera_distance_label`

## Summary
- Domain: `three_d`
- Scene id: `room`
- Scene: `room`
- Query id: `closest_to_camera`
- Answer type: `option_letter`
- Annotation type: one-box `bbox_set`

## Contract
The image shows a synthetic perspective 3D indoor room with a floor, back/side walls, furniture, unlettered room context, unlettered wall-mounted candidate objects, and a below-scene text option panel. The prompt asks which option describes the wall-mounted object closest to the camera.

Each instance renders `6` unlettered answer candidates spread across the left, back, and right walls. Candidate object types come from TVs, clocks, picture frames, mirrors, wall fans, air conditioners, and hanging coats. Unlettered wall objects and floor/furniture props provide room context but are excluded from the answer options.

The task uses a narrower front-oblique camera band and keeps side-wall candidates away from the open front edge of the room, so wall-mounted objects remain visibly hanging on the wall rather than collapsing into edge-on slivers. Generation rejects side-wall candidates whose projected wall face is too skinny.

The renderer uses a lower interior camera, extends the open/front floor toward the camera, keeps side-wall continuation capped to avoid cutaway wall panels, and includes foreground floor context so the scene reads from inside the room. Candidate placement, wall assignments, camera distances, and verifier geometry still use the semantic room coordinates recorded in trace metadata.

The answer is computed from finalized metadata using the minimum `camera_distance` among candidate wall-mounted objects. Generation enforces a unique nearest candidate and records the full near-to-far option-label order, per-label camera distances, candidate walls, and nearest margin.

## Annotation Contract
Annotation is the bounding box of the selected wall-mounted object in the room scene. The option panel and option text are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_room_v0` under `prompts/three_d/room/`. The trace records camera pose, projection frame, room scene variant, render-only floor front (`render_front_y`), render-only side-wall front (`render_side_wall_front_y`), bounded semantic room front (`semantic_front_y`), wall and floor object specs, per-label camera distances, candidate wall assignments, candidate projected bboxes, near-to-far order, selected object id/type/wall, projected object bboxes, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D room scene trace.
