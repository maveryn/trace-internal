# Three-D Task Setup

Use this document for the active `three_d` domain contract.

## 1) Domain Scope
1. `three_d` contains synthetic perspective scenes with explicit 3D world coordinates, a camera model, projected pixel geometry, and metadata-grounded spatial verifiers.
2. The domain owns synthetic 3D spatial reasoning; new 3D point-cloud tasks should be added here rather than under puzzle scenes.
3. Answers and evidence must be derived from the same finalized 3D scene trace. Pixels are render output, not the verifier source of truth.
4. Keep visual variation semantic-free: open floor/table/platform styling can change, but object positions, camera, projection, and evidence bboxes must stay traceable.
5. Canonical object ids, prompt names, dimensions, and scene-role profiles live in `trace/tasks/three_d/shared/object_resources.py`. Scenes should select from this shared catalog instead of inventing local object pools.
6. Inventory inspection previews use `trace/tasks/three_d/shared/object_inventory_preview.py`, which dispatches each profile to a valid native preview adapter by `profile.renderer`: `object_scene_shape`, `room_wall_object`, `room_floor_object`, `street_object`, or `warehouse_object`. Do not preview non-object-scene resources through the object-scene renderer fallback, because street, room, and warehouse objects depend on different support planes and draw helpers.
7. Regenerate the object inventory sheets with `python scripts/generate_three_d_object_inventory.py --columns 8 --fail-on-render-error`; the output manifest records preview adapter metadata for each rendered profile.

## 2) Active Families
### `spatial`
1. Active tasks:
   - `task_three_d__object_scene__camera_distance_extremum_label`
   - `task_three_d__object_scene__counterfactual_attribute_count`
   - `task_three_d__object_scene__object_relation_label`
   - `task_three_d__object_scene__reference_nearest_label`
   - `task_three_d__object_scene__between_references_label`
   - `task_three_d__object_scene__occlusion_order_label`
   - `task_three_d__object_scene__height_extremum_label`
   - `task_three_d__object_scene__multiview_object_match_label`
   - `task_three_d__object_scene__named_object_count`
   - `task_three_d__object_scene__spatial_relation_count`
   - `task_three_d__object_scene__view_relation_count`
2. `object_scene` scene/query surface:
   - `scene_variant`: `floor_grid_room|tabletop_room|studio_platform`
   - public task ids: `task_three_d__object_scene__camera_distance_extremum_label`, `task_three_d__object_scene__counterfactual_attribute_count`, `task_three_d__object_scene__object_relation_label`, `task_three_d__object_scene__reference_nearest_label`, `task_three_d__object_scene__between_references_label`, `task_three_d__object_scene__occlusion_order_label`, `task_three_d__object_scene__height_extremum_label`, `task_three_d__object_scene__multiview_object_match_label`, `task_three_d__object_scene__named_object_count`, `task_three_d__object_scene__spatial_relation_count`, `task_three_d__object_scene__view_relation_count`
   - camera-distance `query_id`: `closest_to_camera|farthest_from_camera`
   - counterfactual-attribute-count `query_id`: `attribute_count_after_edits`
   - object-relation `query_id`: `on_top_of_prop|under_prop|inside_prop`
   - reference-nearest `query_id`: `closest_to_reference`
   - between-references `query_id`: `between_references`
   - occlusion-order `query_id`: `in_front_of_reference`
   - height-extremum `query_id`: `highest_above_floor|lowest_above_floor`
   - multiview-object-match `query_id`: `same_object_in_second_view`
   - view-relation-count `query_id`: `left_of_reference_in_view_count|right_of_reference_in_view_count`
   - camera yaw samples from front, side, and rear oblique orbit bands rather than a single front-right/front-left viewpoint family.
   - camera-distance instances currently use a `full_bleed_floor` renderer mode so the gridded floor/tabletop fills the full canvas instead of appearing as a bounded floating platform; grid lines are clipped to the visible floor plane computed from screen-ray intersections with `z=0`, so the grid reaches the canvas bounds without using a finite platform edge.
   - counterfactual-attribute-count prompts ask for the final count of a color-only, object-only, or color+object predicate after one to three textual add/remove edits. Edit predicates can also be color-only, object-only, or color+object, but generation keeps only predicates whose effect on the final counted predicate is unambiguous: definite target-affecting subset edits or definite non-target disjoint edits. The visible scene uses a narrow color-safe small-shape pool and controlled prompt colors; evidence marks the initial visible objects matching the final counted predicate, while the answer is the final symbolic count after edits.
   - each instance renders `6` lettered answer-candidate objects plus one or more unlettered context/reference props on an open gridded 3D floor/platform.
   - object dimensions are sampled from deterministic per-role ranges: small candidates vary around compact object proportions, while context props use larger furniture/fixture-scale proportions.
   - supported small candidate geometry/object types are `sphere`, `cube`, `cylinder`, `cone`, `arrow`, `sword`, `shield`, `diamond`, `heart`, `key`, `crown`, `anchor`, `horseshoe`, `hammer`, `gear`, `bell`, `trophy`, `open_book`, `mushroom`, `lantern`, `candle`, `goblet`, `mail_envelope`, `compass`, `flask`, `clock`, `apple`, `carrot`, `fish`, `leaf`, `glove`, `hat`, `helmet`, `cup`, `bottle`, `umbrella`, `calculator`, `dice`, `kite`, `cactus`, `drum`, `ruler`, `remote_control`, `plug`, `torus`, `pyramid`, `wedge`, `star_prism`, `hexagonal_prism`, and `half_cylinder`.
   - prompt-facing object names are recorded separately as `object_name` / `prompt_name`; safe small names are `ball`, `cube`, `cylinder`, `cone`, `arrow`, `sword`, `shield`, `diamond`, `heart`, `key`, `crown`, `anchor`, `horseshoe`, `hammer`, `gear`, `bell`, `trophy`, `book`, `mushroom`, `lantern`, `candle`, `goblet`, `envelope`, `compass`, `flask`, `clock`, `apple`, `carrot`, `fish`, `leaf`, `glove`, `hat`, `helmet`, `cup`, `bottle`, `umbrella`, `calculator`, `dice`, `kite`, `cactus`, `drum`, `ruler`, `remote control`, `plug`, `ring`, `pyramid`, `ramp`, `star`, `hexagon`, and `half cylinder`.
   - supported large context prop names are `arch`, `table`, `shelf`, `open box`, `refrigerator`, `washing machine`, `vending machine`, `trash bin`, `bench`, `piano`, `locker`, `cabinet`, `sofa`, `barrel`, and `chair`; these may appear as context props or, for reference-nearest, as larger lettered answer candidates.
   - `open box` props are drawn as low trays; `inside_prop` answer candidates are lifted onto the box floor and rendered in a contained-object foreground layer so the contained letter remains visible.
   - relation prompts may name safe larger props as references; the answer is still the small object letter.
   - reference-nearest prompts name one unlettered small or large reference object and ask for the closest lettered candidate; the reference is excluded from the options and has a unique prompt-facing name in the scene.
   - between-references prompts name two unlettered reference props and ask which lettered candidate lies in the floor-plane corridor between them; non-answer candidates are constrained outside that corridor and away from heavy reference overlap.
   - occlusion-order prompts name one unlettered reference prop and ask which lettered object appears in front of it; open boxes are excluded as occlusion references, non-answer candidates are constrained away from meaningful reference overlap, and the verifier uses projected overlap plus camera-distance ordering.
   - height-extremum prompts ask which lettered object is sitting highest or lowest above the floor; candidates are placed on the floor or visible support props and the verifier uses metadata vertical base height.
   - multiview-object-match prompts render two side-by-side camera views of the same finalized object scene; the left view hides option letters and marks one source object with a red box, while the right view shows the same candidate objects with letters. The answer is the right-view letter whose stable `canonical_object_id` matches the red-boxed left-view object. The first version omits large context props by default so every candidate remains visible from both cameras.
   - view-relation-count prompts name one unique unlettered small reference object and ask how many other small objects appear left or right of it in the image; all objects use prompt-name-safe small-object classes, and the verifier uses projected screen-center x coordinates from finalized camera metadata with a minimum x-margin around the reference.
   - future name-based tasks should filter on `nameable_for_prompt=true` and avoid formal or arbitrary construction names.
3. Evidence contract:
   - one-box `bbox_set` around the selected lettered 3D object.
   - multiview-object-match uses role-keyed `keyed_bbox_map` with `reference_view_object` around the red-boxed left-view object and `second_view_match` around the matched right-view lettered object.
   - count tasks use a `bbox_set` around all counted target objects; named references are excluded from evidence.
4. Prompt policy:
   - label tasks ask for a single option letter; count tasks ask for one integer,
   - keep the task grounded in perspective depth cues,
   - keep closest/farthest as internal query ids rather than separate public task ids,
   - keep prompt-facing evidence on the selected object, not on the floor grid or open stage.
   - for multiview matching, evidence should bind the source and target roles with keyed boxes rather than an unordered box set.
   - view-relation-count prompts must say `in the image` so left/right is image-view relative, not object-perspective or world-axis relative.

### `room`
1. Active tasks:
   - `task_three_d__room__wall_mounted_object_count`
   - `task_three_d__room__wall_object_camera_distance_label`
   - `task_three_d__room__wall_object_same_wall_reference_label`
   - `task_three_d__room__wall_object_side_relation_label`
2. `room` scene/query surface:
   - `scene_variant`: `living_room|office_room|studio_room`
   - public task ids: `task_three_d__room__wall_mounted_object_count`, `task_three_d__room__wall_object_camera_distance_label`, `task_three_d__room__wall_object_same_wall_reference_label`, `task_three_d__room__wall_object_side_relation_label`
   - wall-mounted count `query_id`: `tv_wall_mounted_count|clock_wall_mounted_count|picture_frame_wall_mounted_count|mirror_wall_mounted_count|wall_shelf_wall_mounted_count|wall_fan_wall_mounted_count|air_conditioner_wall_mounted_count|hanging_coat_wall_mounted_count`
   - wall-object camera-distance `query_id`: `closest_to_camera`
   - wall-object same-wall-reference `query_id`: `same_wall_as_reference`
   - wall-object side-relation `query_id`: `left_of_reference_on_wall|right_of_reference_on_wall`
   - each instance renders a perspective indoor room with floor, back/side walls, wall-mounted objects, furniture, and non-wall objects on furniture or the floor.
   - the room renderer uses a lower interior camera, extends the open/front floor toward the camera, and uses a capped render-only side-wall continuation (`render_front_y` / `render_side_wall_front_y`) so the scene reads from inside the room without exposing large cutaway wall panels; semantic placement/verifier geometry still use `ROOM_FRONT_Y` recorded as `semantic_front_y`.
   - target wall objects are mounted on the back wall for readability, while same-type non-wall distractors are included so the task requires the wall-mounted relation rather than plain object-type counting.
   - camera-distance candidates are lettered wall-mounted objects spread across left, back, and right walls, and the answer is the nearest candidate by finalized camera distance.
   - camera-distance generation uses narrower front-oblique camera bands and side-wall visibility checks so side-wall candidates remain visibly attached to the wall instead of becoming edge-on slivers.
   - same-wall-reference prompts name one unlettered wall-mounted reference object whose prompt name is unique in the finalized scene; the answer is the only lettered wall-mounted candidate with the same `wall` metadata as that reference.
   - side-relation prompts name one unlettered TV mounted on a wall; all lettered candidates are on that same wall, and the answer is the only candidate left or right of the TV in wall-plane coordinates rather than raw screen x-position.
   - TVs, clocks, and picture frames can appear as same-type distractors on tables, desks, beds, or media consoles with explicit `mounting=on_furniture` and `support_object_id` metadata.
   - supported target object categories are TVs, clocks, picture frames, mirrors, wall shelves, wall fans, air conditioners, and hanging coats; picture frames show simple scenery paintings but remain prompt-facing picture frames.
   - extra wall/floor context can include posters, wall lamps, speakers, wall cabinets, sofas, armchairs, media consoles, side tables, desks, beds, plants, floor lamps, boxes, and balls.
   - the verifier counts objects with matching `object_type` and `is_wall_mounted=true` from finalized scene metadata.
3. Evidence contract:
   - `bbox_set` around the counted wall-mounted target objects in deterministic scene order.
   - zero-count instances use an empty `bbox_set`.
   - camera-distance instances use one `bbox_set` box around the selected lettered wall-mounted object.
   - same-wall-reference instances use one `bbox_set` box around the selected lettered wall-mounted object; the named reference object is excluded from evidence.
   - side-relation instances use one `bbox_set` box around the selected lettered wall-mounted object; the TV reference is excluded from evidence.
4. Prompt policy:
   - ask for one integer count,
   - camera-distance, same-wall-reference, and side-relation prompts ask for one option letter,
   - keep wall-mounted/hanging relation explicit,
   - keep same-type non-wall distractors out of evidence.

### `street`
1. Active tasks:
   - `task_three_d__street__intersection_nearest_label`
   - `task_three_d__street__lane_ahead_object_label`
   - `task_three_d__street__same_road_arm_reference_label`
2. `street` scene/query surface:
   - `scene_variant`: `downtown_intersection|neighborhood_intersection|transit_intersection`
   - public task ids: `task_three_d__street__intersection_nearest_label`, `task_three_d__street__lane_ahead_object_label`, `task_three_d__street__same_road_arm_reference_label`
   - nearest-intersection `query_id`: `closest_to_intersection`
   - lane-ahead `query_id`: `ahead_along_lane`
   - same-road-arm-reference `query_id`: `same_road_arm_as_reference`
   - each instance renders a perspective 3D street intersection with sidewalks, crosswalk markings, road-lane depth cues, unlettered street context, and lettered street-object answer candidates; nearest-intersection and same-road-arm-reference use `6` candidates, while lane-ahead uses `5` candidates plus `8` unlettered context objects.
   - the street surface is rendered full-bleed: sidewalk ground fills the canvas and road strips are clipped to the visible floor-plane polygon computed from screen-ray intersections, so roads continue to the image edges instead of ending at a projected finite square.
   - street generators reject camera/frame samples where the canvas corners do not intersect the floor plane, avoiding fallback road-surface artifacts while preserving the full-bleed street look.
   - road layout is a recorded non-semantic visual axis: `intersection_layout=four_way|t_missing_north|t_missing_south|t_missing_east|t_missing_west`.
   - the intersection center is sampled within a small recorded world-coordinate offset rather than fixed at the stage center.
   - candidate object types include cars, taxis, vans, buses, delivery trucks, pickup trucks, scooters, motorcycles, male pedestrians, female pedestrians, bicycles, traffic cones, fire hydrants, trash bins, mailboxes, construction barriers, and road barrels.
   - male and female pedestrians are explicit street object types; the female variant uses a skirt and longer hair, while the male variant uses pants and short hair.
   - unlettered context can include buildings, explicit store/office-building profiles, storefronts, trees, shrubs, traffic lights, street signs, and benches; context placement is jittered around the finalized intersection layout instead of fixed to one repeated corner pattern.
   - buildings carry recorded non-semantic style attrs such as `office_glass`, `apartment_brick`, `glass_tower`, `retail_corner`, `cafe_shop`, `market_shop`, `bookstore_shop`, `concrete_midrise`, and `stucco_walkup`; rendering uses style-specific colors, proportions, windows, roof caps, storefronts, awnings, and glass/brick facade details.
   - the context sampler now reserves more of the context budget for large buildings/storefronts so full-bleed sidewalk regions do not read as empty plane around the roads.
   - camera yaw samples from multiple oblique orbit bands so the street scene is not locked to a single right-side viewpoint.
   - the answer is the candidate with the smallest finalized ground-plane distance from its object center to the intersection center, with a unique margin by construction.
   - lane-ahead instances add one red-boxed unlettered reference car with a red travel-direction arrow; exactly one lettered candidate is ahead in the same finalized lane corridor, while distractors can be behind, in an adjacent lane, off lane, or on other road arms.
   - same-road-arm-reference instances add one red-boxed unlettered reference street object; exactly one lettered candidate shares the reference's finalized `road_arm`, and distractors are constrained to other present road arms.
3. Evidence contract:
   - one-box `bbox_set` around the selected lettered street object.
4. Prompt policy:
   - ask for a single option letter only,
   - keep prompt-facing evidence on the selected street object, not on the intersection center, road markings, or unlettered context.

### `warehouse`
1. Active tasks:
   - `task_three_d__warehouse__robot_forward_path_label`
   - `task_three_d__warehouse__robot_nearest_object_label`
2. `warehouse` scene/query surface:
   - `scene_variant`: `storage_aisle|loading_zone|packing_floor`
   - public task ids: `task_three_d__warehouse__robot_forward_path_label`, `task_three_d__warehouse__robot_nearest_object_label`
   - robot-forward-path `query_id`: `first_object_ahead`
   - robot-nearest-reference query ids: `closest_robot_to_reference`, `closest_object_to_robot`
   - each instance renders a perspective 3D warehouse aisle with a full-bleed gridded floor, shelf racks, equipment, one red-boxed robot reference, a red travel-direction arrow, and `5` lettered candidate warehouse objects.
   - exactly two candidates lie in the robot's finalized forward path corridor; the answer is the nearest one by positive forward distance from the robot. Distractors can sit behind the robot, beside the robot, in an adjacent aisle, or off the forward path.
   - nearest-reference instances either render one unlettered red sphere with `5` lettered robots or one unlettered robot with `5` lettered warehouse objects; the answer is the candidate with the smallest finalized floor-plane surface gap to the reference.
   - the renderer frames the camera around the robot, candidates, path corridor, and main aisle while letting shelf racks sit wider and sometimes extend partly out of frame; the screen-ray floor-plane grid still reaches the canvas bounds.
   - shelf rack style is a recorded internal visual axis with `open_frame|loaded_bins|mixed_crates|tall_sparse|heavy_low`; shelf levels, beam/post thickness, frame color, height scale, and small stored-bin/crate slots vary per rack.
   - robot body design is a recorded internal visual axis with `low_cart|sensor_tower|stacker_bot`; robot base/accent colors vary, all designs include a small gripper arm, and the same visual robot family is reused for red-boxed references and lettered robot candidates.
   - supported warehouse object/context types include shelf racks, crate stacks, loaded pallets, barrels, traffic cones, floor signs, tool carts, pallet jacks, forklifts, box stacks, tire stacks, safety barriers, storage bins, ladders, charging docks, conveyors, workbenches, rolling bins, trash cans, warning bollards, wrapped bundles, fire extinguishers, hand trucks, and stacked pipes.
   - shelf racks are far-side context structure and are not answer candidates; lower warehouse props fill more near-side context so candidates stay visible. Path candidates are sampled from larger, readable object types so the first reached object is visually legible.
   - robot headings sample across `east|north|west|south`, with camera yaw sampled from multiple oblique orbit bands.
3. Evidence contract:
   - one-box `bbox_set` around the selected lettered warehouse object or selected lettered robot, depending on the task.
4. Prompt policy:
   - ask for a single option letter only,
   - refer to the red-boxed robot and red arrow,
   - for nearest-reference prompts, refer either to the red sphere and lettered robots or to the unlettered robot and lettered warehouse objects,
   - keep evidence on the selected warehouse object or robot, not on arrows, path corridors, shelves, or unlettered references.

## 3) Shared Helper Direction
1. `trace/tasks/three_d/shared/color_variation.py` owns deterministic non-semantic fill-color variation for synthetic 3D objects. Renderers should record resolved object colors in scene-entity attrs as `fill_rgb`.
2. `trace/tasks/three_d/shared/object_resources.py` owns the canonical named 3D object resource layer. It defines object pools, prompt-facing names, scene-role profiles, base dimensions, color defaults, render-attribute pools, resource kinds, support/mounting annotations, and task-specific allowed-subset pools for object-scene, room, street, and warehouse renderers.
3. Scene/task modules should select from `object_resources.py` instead of inventing local object identities. A scene may keep task-local layout slots, camera constraints, visibility thresholds, and verifier-specific filters, but reusable object type, name, dimension, color, render-style, or allowed-subset entries should be promoted to the shared resource registry.
4. `ThreeDObjectProfile.resource_kind` separates standalone objects from mounted wall objects, supported/composite tabletop objects, floor variants, and semantic reference resources. Inventory/review sheets should keep standalone small/large resources separate from mounted/composite/variant/reference resources so tabletop picture frames, wall speakers, and similar supported objects do not look like free-floating small object classes.
5. The registry intentionally permits one canonical object to have multiple scene profiles, for example `ball` as an object-scene small shape and as a room floor prop. Future renderer consolidation should prefer canonical ids plus profile-specific scale/render metadata over unrelated scene-local names.
6. The initial object-scene renderer is task-local in `trace/tasks/three_d/spatial/camera_distance.py`.
7. `task_three_d__object_scene__object_relation_label`, `task_three_d__object_scene__reference_nearest_label`, `task_three_d__object_scene__between_references_label`, `task_three_d__object_scene__occlusion_order_label`, `task_three_d__object_scene__height_extremum_label`, `task_three_d__object_scene__multiview_object_match_label`, `task_three_d__object_scene__named_object_count`, `task_three_d__object_scene__spatial_relation_count`, `task_three_d__object_scene__view_relation_count`, and `task_three_d__object_scene__counterfactual_attribute_count` currently reuse that renderer surface from the same task-group module. A future cleanup should promote the camera model and object-scene drawing helpers to `trace/tasks/three_d/shared/` before broadening the scene API further.
8. `task_three_d__room__wall_mounted_object_count` introduced a room-scene renderer under `trace/tasks/three_d/room/`; `task_three_d__room__wall_object_camera_distance_label`, `task_three_d__room__wall_object_same_wall_reference_label`, and `task_three_d__room__wall_object_side_relation_label` reuse that renderer and the same object-scene projection/camera primitives. The room floor uses render-only open-front continuation, while side walls use a shorter capped continuation to avoid large artificial cutaway panels; bounded semantic room coordinates are preserved. A future cleanup should promote the shared room scene, camera, and projection helpers before broadening the room scene family further.
9. `task_three_d__street__intersection_nearest_label` introduced a street-scene renderer under `trace/tasks/three_d/street/`; `task_three_d__street__same_road_arm_reference_label` and `task_three_d__street__lane_ahead_object_label` reuse that renderer and the existing 3D projection/camera primitives. Promote shared street scene, camera, and projection helpers before broadening the street scene family further.
10. `task_three_d__warehouse__robot_forward_path_label` introduces a warehouse-scene renderer under `trace/tasks/three_d/warehouse/` and reuses the existing object-scene projection/camera primitives. `task_three_d__warehouse__robot_nearest_object_label` broadens that scene to reference-distance variants with either multiple lettered robots or multiple lettered warehouse objects. Promote shared warehouse scene, camera, and projection helpers before the next substantial warehouse-scene expansion.
