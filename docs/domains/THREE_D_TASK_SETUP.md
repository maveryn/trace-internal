# Three-D Task Setup

Use this document for the active `three_d` domain contract.

## 1) Domain Scope
1. `three_d` contains synthetic perspective scenes with explicit 3D world coordinates, a camera model, projected pixel geometry, and metadata-grounded spatial verifiers.
2. The domain owns synthetic 3D spatial reasoning; new 3D point-cloud tasks should be added here rather than under puzzle scenes.
3. Answers and annotation must be derived from the same finalized 3D scene trace. Pixels are render output, not the verifier source of truth.
4. Keep visual variation semantic-free: open floor/table/platform styling can change, but object positions, camera, projection, and annotation bboxes must stay traceable.
5. Canonical object ids, prompt names, dimensions, and scene-role profiles live in `trace/tasks/three_d/shared/object_resources.py`. Scenes should select from this shared catalog instead of inventing local object pools.
6. Reusable object placement should flow through `trace/tasks/three_d/shared/scene_schema.py` (`ThreeDPlacementSpec`) plus `trace/tasks/three_d/shared/object_rendering.py` (`ThreeDObjectSpec`). Scene modules own where objects go; shared modules own what the objects are and how reusable objects render.
7. Inventory inspection previews use `trace/tasks/three_d/shared/object_inventory_preview.py`, which dispatches each profile to a valid native preview adapter by `profile.renderer`: `object_scene_shape`, `room_wall_object`, `room_floor_object`, `street_object`, or `warehouse_object`. Profiles with `resource_kind=scene_support` are routed through their scene-support adapters, not the loose-object renderer fallback.
8. The review app's `/three-d/objects` page renders the same native profile previews and persists per-profile decisions keyed by `profile_id`: approve, remove, or improve rendering with notes. Use that page for object-fidelity audits before turning notes into renderer changes.
9. Regenerate the object inventory sheets with `python scripts/generate_three_d_object_inventory.py --columns 8 --fail-on-render-error`; the output manifest records preview adapter metadata for each rendered profile.
10. CountQA-aligned object renderer additions should record the online 2D/3D reference sources used for silhouette choices. The current expansion notes live in `docs/domains/THREE_D_COUNTQA_OBJECT_REFERENCES.md`.
11. Non-semantic visual attributes must not encode the answer. Candidate colors, style variants, object scale jitter, or marker styling may vary for readability, but must not be assigned from answer-defining slots such as height support placement, depth rank, relation truth, lane/road arm membership, or fixed construction order. Color may be semantic only in tasks that explicitly query color/count predicates, and those predicates must be recorded in verifier metadata.

## 2) Active Families
### `spatial`
1. Active tasks:
   - `task_three_d__object_scene__camera_distance_extremum_label`
   - `task_three_d__object_scene__counterfactual_count`
   - `task_three_d__object_scene__object_relation_label`
   - `task_three_d__object_scene__reference_nearest_label`
   - `task_three_d__object_scene__between_references_label`
   - `task_three_d__object_scene__occlusion_order_label`
   - `task_three_d__object_scene__height_extremum_label`
   - `task_three_d__object_scene__landmark_correspondence_label`
   - `task_three_d__object_scene__single_attribute_membership_count`
   - `task_three_d__object_scene__multi_attribute_and_count`
   - `task_three_d__object_scene__multi_attribute_or_count`
   - `task_three_d__object_scene__multi_attribute_xor_count`
   - `task_three_d__object_scene__multi_attribute_exclusion_count`
   - `task_three_d__object_scene__marked_point_depth_extremum_label`
   - `task_three_d__object_scene__marked_point_vertical_relation_label`
   - `task_three_d__object_scene__multiview_object_match_label`
   - `task_three_d__object_cluster__total_object_count`
   - `task_three_d__object_cluster__single_attribute_membership_count`
   - `task_three_d__object_cluster__multi_attribute_and_count`
   - `task_three_d__surface_fixture__repeated_element_count`
   - `task_three_d__object_scene__relation_attribute_count`
   - `task_three_d__object_scene__image_plane_lateral_relation_count`
   - `task_three_d__object_scene__camera_depth_relation_count`
2. `object_scene` scene/query surface:
   - `scene_variant`: `floor_grid_room|tabletop_room|studio_platform`
   - public task ids: `task_three_d__object_scene__camera_distance_extremum_label`, `task_three_d__object_scene__counterfactual_count`, `task_three_d__object_scene__object_relation_label`, `task_three_d__object_scene__reference_nearest_label`, `task_three_d__object_scene__between_references_label`, `task_three_d__object_scene__occlusion_order_label`, `task_three_d__object_scene__height_extremum_label`, `task_three_d__object_scene__landmark_correspondence_label`, `task_three_d__object_scene__single_attribute_membership_count`, `task_three_d__object_scene__multi_attribute_and_count`, `task_three_d__object_scene__multi_attribute_or_count`, `task_three_d__object_scene__multi_attribute_xor_count`, `task_three_d__object_scene__multi_attribute_exclusion_count`, `task_three_d__object_scene__marked_point_depth_extremum_label`, `task_three_d__object_scene__marked_point_vertical_relation_label`, `task_three_d__object_scene__multiview_object_match_label`, `task_three_d__object_scene__relation_attribute_count`, `task_three_d__object_scene__image_plane_lateral_relation_count`, `task_three_d__object_scene__camera_depth_relation_count`
   - camera-distance `query_id`: `closest_to_camera|farthest_from_camera`
   - counterfactual-count `query_id`: `attribute_count_after_edits`
   - object-relation `query_id`: `on_top_of_prop|under_prop|inside_prop`
   - reference-nearest `query_id`: `closest_to_reference`
   - between-references `query_id`: `between_references`
   - occlusion-order `query_id`: `in_front_of_reference`
   - height-extremum `query_id`: `highest_above_floor|lowest_above_floor`
   - landmark-correspondence `query_id`: `landmark_correspondence`
   - single-attribute-membership-count `query_id`: `object_type_count|object_type_union_count|color_union_count`
   - multi-attribute-and-count `query_id`: `object_type_and_color_count`
   - multi-attribute-or-count `query_id`: `object_type_or_color_count`
   - multi-attribute-xor-count `query_id`: `exactly_one_object_type_or_color_count`
   - multi-attribute-exclusion-count `query_id`: `object_type_and_not_color_count|color_and_not_object_type_count`
   - marked-point-depth `query_id`: `closest_marked_point|farthest_marked_point`
   - marked-point-vertical-relation `query_id`: `directly_above_reference`
   - multiview-object-match `query_id`: `same_object_in_second_view`
   - image-plane-lateral-relation-count `query_id`: `left_of_reference_in_view_count|right_of_reference_in_view_count`
   - camera-depth-relation-count `query_id`: `closer_to_camera_than_reference_count|farther_from_camera_than_reference_count`
   - camera yaw samples from front, side, and rear oblique orbit bands rather than a single front-right/front-left viewpoint family.
   - camera-distance instances currently use a `full_bleed_floor` renderer mode so the gridded floor/tabletop fills the full canvas instead of appearing as a bounded floating platform; grid lines are clipped to the visible floor plane computed from screen-ray intersections with `z=0`, so the grid reaches the canvas bounds without using a finite platform edge.
   - counterfactual-count prompts ask for the final count of a color-only, object-only, or color+object predicate after one to three textual add/remove edits. Edit predicates can also be color-only, object-only, or color+object, but generation keeps only predicates whose effect on the final counted predicate is unambiguous: definite target-affecting subset edits or definite non-target disjoint edits. The visible scene uses a narrow color-safe small-shape pool and controlled prompt colors; annotation marks the initial visible objects matching the final counted predicate, while the answer is the final symbolic count after edits.
   - single-attribute-membership-count and multi-attribute count prompts ask for the static visual count of objects satisfying type/color predicates: object-type membership, multi-type union, multi-color union, color+type conjunction, inclusive OR, exact-one/XOR, type-and-not-color, and color-and-not-type. Generation uses the same narrow color-safe small-shape pool and controlled prompt colors as the counterfactual task, but there are no textual edits; the answer and annotation both refer to the finalized visible object set satisfying the requested predicate.
   - single-view label tasks render answer-candidate objects without in-scene option letters and append a text option panel below the scene image; count tasks render only countable scene objects, while multiview matching still renders right-view option letters inside the second view.
   - object-scene single-view option tasks assign candidate prompt colors with `apply_independent_prompt_colors_to_dataset()` after option labels are finalized, using a separate per-instance prompt-color RNG namespace and label-order assignment. Do not assign colors from support placement, distance rank, relation status, or candidate construction order.
   - object dimensions are sampled from deterministic per-role ranges: small candidates vary around compact object proportions, while context props use larger furniture/fixture-scale proportions.
   - supported small candidate geometry/object types are `sphere`, `cube`, `cylinder`, `cone`, `arrow`, `sword`, `shield`, `diamond`, `heart`, `key`, `crown`, `anchor`, `horseshoe`, `hammer`, `gear`, `bell`, `trophy`, `open_book`, `mushroom`, `lantern`, `candle`, `goblet`, `mail_envelope`, `compass`, `flask`, `clock`, `apple`, `carrot`, `fish`, `leaf`, `glove`, `hat`, `helmet`, `cup`, `bottle`, `umbrella`, `calculator`, `dice`, `kite`, `cactus`, `drum`, `ruler`, `remote_control`, `plug`, `torus`, `pyramid`, `wedge`, `star_prism`, `hexagonal_prism`, and `half_cylinder`.
   - prompt-facing object names are recorded separately as `object_name` / `prompt_name`; safe small names are `ball`, `cube`, `cylinder`, `cone`, `arrow`, `sword`, `shield`, `diamond`, `heart`, `key`, `crown`, `anchor`, `horseshoe`, `hammer`, `gear`, `bell`, `trophy`, `book`, `mushroom`, `lantern`, `candle`, `goblet`, `envelope`, `compass`, `flask`, `clock`, `apple`, `carrot`, `fish`, `leaf`, `glove`, `hat`, `helmet`, `cup`, `bottle`, `umbrella`, `calculator`, `dice`, `kite`, `cactus`, `drum`, `ruler`, `remote control`, `plug`, `ring`, `pyramid`, `ramp`, `star`, `hexagon`, and `half cylinder`.
   - supported large context prop names are `arch`, `table`, `shelf`, `open box`, `refrigerator`, `washing machine`, `vending machine`, `trash bin`, `bench`, `piano`, `locker`, `cabinet`, `sofa`, `barrel`, and `chair`; these may appear as context props or, for reference-nearest, as larger answer candidates described in the below-scene option panel.
   - `open box` props are drawn as low trays; `inside_prop` answer candidates are lifted onto the box floor and rendered in a contained-object foreground layer so the contained object remains visible.
   - relation prompts may name safe larger props as references; the answer is still the option letter for the matching small object.
   - reference-nearest prompts name one small or large reference object and ask for the closest candidate described in the option panel; the reference is excluded from the options and has a unique prompt-facing name in the scene.
   - between-references prompts name two reference props and ask which option describes the candidate lying in the floor-plane corridor between them; non-answer candidates are constrained outside that corridor and away from heavy reference overlap.
   - occlusion-order prompts name one reference prop and ask which option describes the object appearing in front of it; open boxes are excluded as occlusion references, non-answer candidates are constrained away from meaningful reference overlap, and the verifier uses projected overlap plus camera-distance ordering.
   - height-extremum prompts ask which option describes the object sitting highest or lowest above the floor; candidates are placed on the floor or visible support props and the verifier uses metadata vertical base height. Candidate prompt colors follow the object-scene independent prompt-color policy rather than support placement, and the small-object pool includes a broader set of stable floor/support objects rather than only cubes/cylinders.
   - landmark-correspondence prompts render two side-by-side camera views of the same kind of feature-rich object; the left view marks one source landmark with a red `REF` point and the right view shows four red-circled candidate points labeled `A-D`. The answer is the right-view label whose recorded landmark id matches the source landmark. The supported object pool is restricted to asymmetric or feature-rich shapes: `fish`, `key`, `hammer`, `sword`, `glove`, `leaf`, `plug`, and `open_book`.
   - marked-point-depth prompts render one object scene with context objects and six letter-only point markers on floor/object surfaces. The answer is the marker label whose recorded 3D point has the minimum or maximum camera distance for the query. Object labels/options are not used; the marked letters themselves are the answer candidates.
   - marked-point-vertical-relation prompts render one object scene with uniquely named small objects and six letter-only floating point markers. The prompt names one reference object from the restricted stable-reference small-object pool and asks which marker is directly above it in 3D space. The verifier uses world vertical `z` alignment over the reference object's floor-plane center; distractor markers have a recorded minimum floor-plane offset from the reference.
   - multiview-object-match prompts render two side-by-side camera views of the same finalized object scene; the left view hides option letters and marks one source object with a red box, while the right view shows the same candidate objects with letters. The answer is the right-view letter whose stable `canonical_object_id` matches the red-boxed left-view object. The first version omits large context props by default so every candidate remains visible from both cameras.
   - image-plane-lateral-relation-count prompts name one unique small reference object and ask how many other small objects appear left/right of it in the image; all objects use prompt-name-safe small-object classes. The verifier uses projected screen-center x coordinates with minimum margins around the reference to reject borderline cases.
   - camera-depth-relation-count prompts name one unique small reference object and ask how many other small objects are closer/farther from the camera than it is; all objects use prompt-name-safe small-object classes. The verifier uses camera-distance metadata with minimum margins around the reference to reject borderline cases.
   - the color/type predicate count tasks are among the few object-scene tasks where color is semantic. The renderer must use the recorded `color_name` / `prompt_color_name` / `fill_rgb` fields from the verifier trace and must not derive semantic color from candidate order, placement, or relation status.
   - future name-based tasks should filter on `nameable_for_prompt=true` and avoid formal or arbitrary construction names.
3. `object_cluster` scene/query surface:
   - `scene_variant`: `tabletop_pile|shallow_tray|cluster_mat`
   - public task ids: `task_three_d__object_cluster__total_object_count`, `task_three_d__object_cluster__single_attribute_membership_count`, `task_three_d__object_cluster__multi_attribute_and_count`
   - total-object-count `query_id`: `total_object_count`
   - single-attribute-membership-count `query_id`: `type_count`
   - multi-attribute-and-count `query_id`: `type_and_color_count`
   - `cluster_composition_mode`: `single_type_cluster|near_homogeneous_cluster|mixed_type_cluster`; default weights are `0.6`, `0.3`, and `0.1`.
   - each instance renders a dense cluster of small standalone 3D objects on a plain full-bleed surface. Grid lines are disabled for this scene because the task is pure instance counting and does not ask depth, distance, or coordinate questions.
   - the object pool currently uses the `50` prompt-safe object-scene small shapes plus `76` cluster-only additions: `pen`, `pencil`, `highlighter`, `card`, `bookmark`, `sachet`, `packet`, `candy`, `CD`, `berry`, `button`, `screw`, `washer`, `paper clip`, `hex nut`, `plate`, `fork`, `spoon`, `knife`, `bowl`, `basket`, `puzzle piece`, `small box`, `dumbbell`, `chair`, `table`, `heater`, `flower`, `plant pot`, `towel`, `glass`, `jar`, `can`, `lid`, `U-bolt`, `nail`, `rod`, `tube`, `clip`, `socket`, `magnet`, `chess piece`, `marker`, `thumb pin`, `hanger`, `light bulb`, `egg`, `chili`, `paint brush`, `paint roller`, `stick`, `straw`, `ticket`, `tag`, `marble`, `bead`, `dot`, `bolt`, `pillow`, `cushion`, `stool`, `drawer`, `cap`, `bucket`, `tray`, `coaster`, `rose`, `banana`, `tomato`, `peanut`, `coffee bean`, `hook`, `bracket`, `battery`, `tape roll`, and `bag`.
   - target shape selection may use the full cluster pool. In `single_type_cluster`, all visible objects are target objects. In distractor modes, distractor sampling excludes visually confusable same-family objects for the selected target. For example, a pencil target does not use pens, markers, highlighters, or rulers as distractors in that instance.
   - default generation caps the target answer at `25`. The default answer bins are `6-10`, `11-17`, and `18-25`; larger texture/grid counts from external counting benchmarks should be handled by a separate fixture-pattern scene rather than this object-cluster scene.
   - `total_object_count` is the level-0 CountQA-style cluster task: every visible clustered object is counted, the cluster is homogeneous, and the sampled primary object type is render variety metadata rather than a prompt predicate.
   - for `single_attribute_membership_count`, object colors, dimensions, order jitter, cluster radius, camera pose, and background style are non-semantic. The verifier counts finalized metadata objects with `shape_type == target_shape_type`.
   - `multi_attribute_and_count` prompts ask for the count of clustered objects satisfying both object type and semantic color, for example red buttons. The semantic color is recorded as `color_name`, `prompt_color_name`, and `fill_rgb`; structured distractors include target-type objects with wrong colors, target-color objects with wrong types, and unrelated objects.
4. `surface_fixture` scene/query surface:
   - `scene_variant`: `wall_tile_panel|perforated_panel|slot_board|compartment_tray|vent_panel|window_grid|door_bank|drawer_pull_panel`
   - public task id: `task_three_d__surface_fixture__repeated_element_count`
   - repeated-element-count `query_id`: `element_type_count`
   - each instance renders one projected fixture surface with exactly one countable repeated element family: `tile`, `hole`, `slot`, `compartment`, `vent`, `window`, `door`, or `drawer_pull`. The scene variant determines the family, so the verifier never has to infer the count target from pixels.
   - the fixture renderer records a synthetic perspective panel projection, screen-space fixture corners, element ids, element centers, and one projected box per repeated element. This scene owns CountQA-style surface-pattern objects that are not loose standalone items.
   - target count defaults to `8-24`; larger texture counts should be introduced through dedicated high-density pattern configs rather than by overloading loose object-cluster tasks.
   - the answer is the integer count of finalized elements whose `element_type == target_element_type`.
5. Annotation contract:
   - single-view label tasks use one-box `bbox_set` around the selected scene object; the option panel text and option label badges are not annotation.
   - landmark-correspondence uses role-keyed `keyed_point_map` with `reference_landmark` at the red `REF` point in the left view and `matched_landmark` at the corresponding candidate point in the right view.
   - marked-point tasks use role-keyed `keyed_point_map` with `selected_point` at the center of the selected marker letter.
   - multiview-object-match uses role-keyed `keyed_bbox_map` with `reference_view_object` around the red-boxed left-view object and `second_view_match` around the matched right-view lettered object.
   - count tasks use a `bbox_set` around all counted target objects; named references are excluded from annotation. For `object_cluster__total_object_count`, annotation marks every visible clustered object. For color/type predicate count tasks, annotation marks every object satisfying the requested predicate and no distractor or option text. For `object_cluster__single_attribute_membership_count`, annotation marks each counted object in the dense cluster and no non-target objects. For `object_cluster__multi_attribute_and_count`, annotation marks each clustered object matching both the requested type and semantic color. For `surface_fixture__repeated_element_count`, annotation marks each counted tile, hole, slot, compartment, vent, window, door, or drawer pull on the fixture surface, not the fixture panel itself.
6. Prompt policy:
   - label tasks ask for a single option letter; count tasks ask for one integer,
   - keep the task grounded in perspective depth cues,
   - keep closest/farthest as internal query ids rather than separate public task ids,
   - prompt-facing annotation should mark the selected object or selected marker as the minimal visual witness.
   - for landmark correspondence, annotation should bind source and target roles with keyed points; option labels are allowed because they localize candidate points rather than object identity labels.
   - for marked-point depth, prompts ask for a marked-point letter and annotation should be the selected marker center, not the marker's text label or nearby object.
   - for multiview matching, annotation should bind the source and target roles with keyed boxes rather than an unordered box set.
   - image-plane-lateral-relation-count prompts must say `in the image` so left/right is image-view relative, not object-perspective or world-axis relative.
   - multi-attribute-or-count and multi-attribute-xor-count prompts must make inclusive OR and exact-one/XOR wording explicit enough that overlapping color+type cases are unambiguous.
   - object-cluster count prompts should ask only for the requested total, object type, or type+color count; do not mention internal distractor-family filtering, object pool details, absent labels, or other non-present features.
   - surface-fixture count prompts should ask only for the repeated surface element count and should not mention internal panel projection, screw heads, or decorative fixture context.

### `room`
1. Active tasks:
   - `task_three_d__room__multi_attribute_and_count`
   - `task_three_d__room__wall_object_camera_distance_label`
   - `task_three_d__room__wall_object_same_wall_reference_label`
   - `task_three_d__room__wall_object_side_relation_label`
2. `room` scene/query surface:
   - `scene_variant`: `living_room|office_room|studio_room`
   - public task ids: `task_three_d__room__multi_attribute_and_count`, `task_three_d__room__wall_object_camera_distance_label`, `task_three_d__room__wall_object_same_wall_reference_label`, `task_three_d__room__wall_object_side_relation_label`
   - multi-attribute-and count `query_id`: `tv_wall_mounted_count|clock_wall_mounted_count|picture_frame_wall_mounted_count|mirror_wall_mounted_count|wall_shelf_wall_mounted_count|wall_fan_wall_mounted_count|air_conditioner_wall_mounted_count|hanging_coat_wall_mounted_count`
   - wall-object camera-distance `query_id`: `closest_to_camera`
   - wall-object same-wall-reference `query_id`: `same_wall_as_reference`
   - wall-object side-relation `query_id`: `left_of_reference_on_wall|right_of_reference_on_wall`
   - each instance renders a perspective indoor room with floor, back/side walls, wall-mounted objects, furniture, and non-wall objects on furniture or the floor.
   - the room renderer uses a lower interior camera, extends the open/front floor toward the camera, and uses a capped render-only side-wall continuation (`render_front_y` / `render_side_wall_front_y`) so the scene reads from inside the room without exposing large cutaway wall panels; semantic placement/verifier geometry still use `ROOM_FRONT_Y` recorded as `semantic_front_y`.
   - target wall objects are mounted on the back wall for readability, while same-type non-wall distractors are included so the task requires the wall-mounted relation rather than plain object-type counting.
   - camera-distance candidates are wall-mounted objects spread across left, back, and right walls, with a below-scene text option panel; the answer is the nearest candidate by finalized camera distance.
   - camera-distance generation uses narrower front-oblique camera bands and side-wall visibility checks so side-wall candidates remain visibly attached to the wall instead of becoming edge-on slivers.
   - same-wall-reference prompts name one wall-mounted reference object whose prompt name is unique in the finalized scene; the answer is the only option-panel candidate with the same `wall` metadata as that reference.
   - side-relation prompts name one TV mounted on a wall; all answer candidates are on that same wall and described in the option panel, and the answer is the only candidate left or right of the TV in wall-plane coordinates rather than raw screen x-position.
   - TVs, clocks, and picture frames can appear as same-type distractors on tables, desks, beds, or media consoles with explicit `mounting=on_furniture` and `support_object_id` metadata.
   - supported target object categories are TVs, clocks, picture frames, mirrors, wall shelves, wall fans, air conditioners, and hanging coats; picture frames show simple scenery paintings but remain prompt-facing picture frames.
   - extra wall/floor context can include posters, wall lamps, speakers, wall cabinets, sofas, armchairs, media consoles, side tables, desks, beds, plants, floor lamps, boxes, and balls.
   - the verifier counts objects with matching `object_type` and `is_wall_mounted=true` from finalized scene metadata.
3. Annotation contract:
   - `bbox_set` around the counted wall-mounted target objects in deterministic scene order.
   - zero-count instances use an empty `bbox_set`.
   - camera-distance instances use one `bbox_set` box around the selected wall-mounted object in the room scene.
   - same-wall-reference instances use one `bbox_set` box around the selected wall-mounted object in the room scene; the named reference object is excluded from annotation.
   - side-relation instances use one `bbox_set` box around the selected wall-mounted object in the room scene; the TV reference is excluded from annotation.
4. Prompt policy:
   - ask for one integer count,
   - camera-distance, same-wall-reference, and side-relation prompts ask for one option letter,
   - keep wall-mounted/hanging relation explicit,
   - keep same-type non-wall distractors out of annotation.

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
   - each instance renders a perspective street intersection with sidewalks, crosswalk markings, road-lane depth cues, street context, street-object answer candidates, and a below-scene text option panel; nearest-intersection and same-road-arm-reference use `6` candidates, while lane-ahead uses `5` candidates plus `8` context objects.
   - the street surface is rendered full-bleed: sidewalk ground fills the canvas and road strips are clipped to the visible floor-plane polygon computed from screen-ray intersections, so roads continue to the image edges instead of ending at a projected finite square.
   - street generators reject camera/frame samples where the canvas corners do not intersect the floor plane, avoiding fallback road-surface artifacts while preserving the full-bleed street look.
   - road layout is a recorded non-semantic visual axis: `intersection_layout=four_way|t_missing_north|t_missing_south|t_missing_east|t_missing_west`.
   - the intersection center is sampled within a small recorded world-coordinate offset rather than fixed at the stage center.
   - candidate object types include cars, taxis, vans, buses, delivery trucks, pickup trucks, scooters, motorcycles, male pedestrians, female pedestrians, bicycles, traffic cones, fire hydrants, trash bins, mailboxes, construction barriers, and road barrels.
   - male and female pedestrians are explicit street object types; the female variant uses a skirt and longer hair, while the male variant uses pants and short hair.
   - context can include buildings, explicit store/office-building profiles, storefronts, trees, shrubs, traffic lights, street signs, and benches; context placement is jittered around the finalized intersection layout instead of fixed to one repeated corner pattern.
   - buildings carry recorded non-semantic style attrs such as `office_glass`, `apartment_brick`, `glass_tower`, `retail_corner`, `cafe_shop`, `market_shop`, `bookstore_shop`, `concrete_midrise`, and `stucco_walkup`; rendering uses style-specific colors, proportions, windows, roof caps, storefronts, awnings, and glass/brick facade details.
   - the context sampler now reserves more of the context budget for large buildings/storefronts so full-bleed sidewalk regions do not read as empty plane around the roads.
   - camera yaw samples from multiple oblique orbit bands so the street scene is not locked to a single right-side viewpoint.
   - the answer is the candidate with the smallest finalized ground-plane distance from its object center to the intersection center, with a unique margin by construction.
   - lane-ahead instances add one red-boxed reference car with a red travel-direction arrow; exactly one option-panel candidate is ahead in the same finalized lane corridor, while distractors can be behind, in an adjacent lane, off lane, or on other road arms.
   - same-road-arm-reference instances add one red-boxed reference street object; exactly one option-panel candidate shares the reference's finalized `road_arm`, and distractors are constrained to other present road arms.
3. Annotation contract:
   - one-box `bbox_set` around the selected street object in the scene.
4. Prompt policy:
   - ask for a single option letter only,
   - prompt-facing annotation should mark the selected street object as the minimal visual witness.

### `warehouse`
1. Active tasks:
   - `task_three_d__warehouse__robot_forward_path_label`
   - `task_three_d__warehouse__nearest_candidate_to_reference_label`
   - `task_three_d__warehouse__scoped_attribute_count`
2. `warehouse` scene/query surface:
   - `scene_variant`: `storage_aisle|loading_zone|packing_floor`
   - public task ids: `task_three_d__warehouse__robot_forward_path_label`, `task_three_d__warehouse__nearest_candidate_to_reference_label`, `task_three_d__warehouse__scoped_attribute_count`
   - robot-forward-path `query_id`: `first_object_ahead`
   - nearest-candidate-to-reference query ids: `closest_robot_to_reference`, `closest_object_to_robot`
   - scoped-attribute-count query ids: `top_shelf_item_count`, `middle_shelf_item_count`, `bottom_shelf_item_count`
   - each instance renders a perspective warehouse aisle with a full-bleed gridded floor, shelf racks, equipment, one red-boxed robot reference, a red travel-direction arrow, candidate warehouse objects, and a below-scene text option panel.
   - exactly two candidates lie in the robot's finalized forward path corridor; the answer is the nearest one by positive forward distance from the robot. Distractors can sit behind the robot, beside the robot, in an adjacent aisle, or off the forward path.
   - nearest-reference instances either render one red sphere with `5` candidate robots or one robot with `5` candidate warehouse objects; the answer is the option-panel candidate with the smallest finalized floor-plane surface gap to the reference.
   - scoped-attribute-count instances render a cleaner rack-only shelf scene with `2..4` distinctly colored racks, exactly three shelf levels per rack, and separate visible shelf items. The prompt names one rack by canonical color label, such as `blue [#2D75E6]`, and one shelf level; the integer answer is the number of items on that level of that rack, with answer range `0..5`.
   - the renderer frames the camera around the robot, candidates, path corridor, and main aisle while letting shelf racks sit wider and sometimes extend partly out of frame; the screen-ray floor-plane grid still reaches the canvas bounds.
   - shelf rack style is a recorded internal visual axis with `open_frame|loaded_bins|mixed_crates|tall_sparse|heavy_low`; shelf levels, beam/post thickness, frame color, height scale, and small stored-bin/crate slots vary per rack.
   - scoped-attribute-count uses a constrained `open_frame` rack style with no internal untracked shelf-load slots; all countable shelf items are standalone item specs so answer and annotation come from the same object set.
   - robot body design is a recorded internal visual axis with `low_cart|sensor_tower|stacker_bot`; robot base/accent colors vary, all designs include a small gripper arm, and the same visual robot family is reused for red-boxed references and robot candidates.
   - supported warehouse object/context types include shelf racks, crate stacks, loaded pallets, barrels, traffic cones, floor signs, tool carts, pallet jacks, forklifts, box stacks, tire stacks, safety barriers, storage bins, ladders, charging docks, conveyors, workbenches, rolling bins, trash cans, warning bollards, wrapped bundles, fire extinguishers, hand trucks, and stacked pipes.
   - shelf racks are far-side context structure and are not answer candidates; lower warehouse props fill more near-side context so candidates stay visible. Path candidates are sampled from larger, readable object types so the first reached object is visually legible.
   - robot headings sample across `east|north|west|south`, with camera yaw sampled from multiple oblique orbit bands.
3. Annotation contract:
   - one-box `bbox_set` around the selected warehouse object or selected robot in the scene, depending on the task; option-panel text is not annotation.
   - for scoped-attribute-count, `bbox_set` contains one bounding box per counted shelf item on the queried level of the queried colored rack, and is `[]` when the count is zero.
4. Prompt policy:
   - ask for a single option letter only for robot-forward-path and nearest-candidate-to-reference tasks,
   - ask for an integer count for scoped-attribute-count,
   - refer to the red-boxed robot and red arrow,
   - for nearest-reference prompts, refer either to the red sphere and candidate robots or to the reference robot and candidate warehouse objects,
   - for scoped-attribute-count prompts, include the queried rack color as `<color name> [#RRGGBB]` and the queried shelf level,
   - robot-task annotation should mark the selected warehouse object or robot as the minimal visual witness,
   - scoped-attribute-count annotation should mark the counted shelf items.

## 3) Shared Helper Direction
1. `trace/tasks/three_d/shared/color_variation.py` owns deterministic non-semantic fill-color variation for synthetic 3D objects. `trace/tasks/three_d/shared/option_panel.py` owns independent prompt-color assignment for object-scene option-panel candidates. Renderers should record resolved object colors in scene-entity attrs as `fill_rgb`; task code should not assign non-semantic colors from answer slots, relation slots, or fixed construction order.
2. `trace/tasks/three_d/shared/object_resources.py` owns the canonical named 3D object resource layer. It defines object pools, prompt-facing names, scene-role profiles, base dimensions, color defaults, render-attribute pools, resource kinds, support/mounting annotations, and task-specific allowed-subset pools for object-scene, room, street, and warehouse renderers. Use its profile lookup helpers (`object_profile`, `object_profile_or_none`, `object_profile_by_id`, and `scene_profile_ids`) instead of open-coding registry scans in scene modules.
3. `trace/tasks/three_d/shared/scene_schema.py` owns renderer-neutral placement/style records. Scene modules should emit finalized `ThreeDPlacementSpec`-compatible object mappings after placement/camera/projection are resolved; reusable object drawing then combines that placement with a `ThreeDObjectProfile` through `ThreeDObjectSpec.from_profile_and_placement(...)`.
4. Scene/task modules should select from `object_resources.py` instead of inventing local object identities. A scene may keep task-local layout slots, camera constraints, visibility thresholds, support-geometry styles, and verifier-specific filters, but reusable object type, name, dimension, color, render-style, or allowed-subset entries should be promoted to the shared resource registry.
5. `ThreeDObjectProfile.resource_kind` separates standalone objects from mounted wall objects, supported/composite tabletop objects, floor variants, scene-support resources, and semantic reference resources. Inventory/review sheets should keep standalone small/large resources separate from mounted/composite/variant/scene-support/reference resources so tabletop picture frames, wall speakers, street buildings, and warehouse shelf racks do not look like free-floating object classes.
6. The registry intentionally permits one canonical object to have multiple scene profiles, for example `ball` as an object-scene small shape and as a room floor prop. Future renderer consolidation should prefer canonical ids plus profile-specific scale/render metadata over unrelated scene-local names.
7. Reusable object rendering is centralized in `trace/tasks/three_d/shared/object_rendering.py`, with normalized trace payloads in `trace/tasks/three_d/shared/object_schema.py` and renderer-variant metadata hooks in `trace/tasks/three_d/shared/object_variants.py`. `render_three_d_object(...)` is the shared object dispatch entry point for projected 3D object-scene glyphs and shared room/street/warehouse object implementations: `object_scene_shape`, `room_wall_object`, `room_floor_object`, `street_object`, and `warehouse_object`. Scene modules should pass a `ThreeDObjectSpec` plus `ThreeDRenderContext` instead of carrying render-loop object-type dispatch tables. Rendered scene entities should keep legacy verifier attrs and add `attrs.object_record` for the normalized object payload.
8. Object-scene, object-cluster, room, street, warehouse, and named-object inventory previews now reuse the shared object renderer surface for reusable semantic objects. Reusable room wall/floor objects, loose street objects, and loose warehouse objects live under `trace/tasks/three_d/shared/`; scene shell/support drawing still stays local: room walls/floor shells, street roads/sidewalks/markers/buildings, warehouse floors/path arrows/shelf rack frames, and surface-fixture repeated panel elements are not loose reusable objects. Room wall projection helpers live in `room_wall_rendering_geometry.py`, street object helper math lives in `street_object_rendering_common.py`, and warehouse scene/support helpers live under `trace/tasks/three_d/warehouse/`.
9. Spatial object-scene task modules should own sampling, verifier payloads, and prompt/trace assembly, while scene-local renderer modules own PIL drawing. Current spatial renderer owners are `surface_fixture_rendering.py` for fixture panels, `multiview_rendering.py` for side-by-side object-scene views, `landmark_rendering.py` for landmark overlays, and `marked_point_rendering.py` for lettered point markers. Do not reintroduce direct `ImageDraw` or `_draw_*` helper facades into those task modules.
10. Room public task modules use `wall_mounted_common.py` for constants, geometry, sampling helpers, and complexity, `wall_mounted_dataset.py` for deterministic room dataset construction, and `wall_mounted_rendering.py` for PIL/ImageDraw scene orchestration and the rendered-scene result type. The room floor uses render-only open-front continuation, while side walls use a shorter capped continuation to avoid large artificial cutaway panels; bounded semantic room coordinates are preserved.
11. Street public task modules use `intersection_scene.py` for constants, render-parameter resolution, geometry helpers, context-object sampling, visibility checks, object spec finalization, and camera/frame reconstruction. Final PIL/ImageDraw orchestration, reference markers, direction arrows, option-panel composition, and the rendered-scene result type live in `intersection_rendering.py`; road and building support drawing stays in `intersection_road_rendering.py` and `intersection_building_rendering.py`.
12. `task_three_d__warehouse__robot_forward_path_label` and `task_three_d__warehouse__nearest_candidate_to_reference_label` use the focused warehouse robot renderer in `trace/tasks/three_d/warehouse/warehouse_rendering.py`, while `task_three_d__warehouse__scoped_attribute_count` uses `warehouse_shelf_rendering.py`. Public warehouse task modules own sampling, prompt/trace assembly, and verifier payloads only; PIL/ImageDraw floor, marker, option-panel, and shelf-item rendering stays in those focused renderer modules. Shared warehouse scene helpers live in `warehouse_scene_common.py`; shelf-rack support drawing lives in `warehouse_support_rendering.py`.
