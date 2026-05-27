# Three-D Coverage Extension

## Scope

This note tracks `three_d` coverage gaps found from the external benchmark
failure analysis, then records candidate changes for the domain.

Current working conclusion: `three_d` already covers the core synthetic
perspective-spatial reasoning form, but its scene vocabulary is still narrow.
Active tasks cover camera-distance extrema, object relation labels, nearest to
a reference, between two references, occlusion order, height extrema, and
wall-mounted object reasoning in room scenes. The remaining benchmark gaps are
mostly about richer indoor scenes, broader relation vocabularies, multi-view
correspondence, controlled lighting/material reasoning, and embodied
manipulation if we choose to target robotics benchmarks.

Relevant benchmark cues:

- EmbSpatial: left/right/above/under spatial relations, nearest/farthest from
  viewpoint, and object-scene relations in indoor-looking images.
- BLINK: relative depth, visual correspondence under camera or lighting change,
  multi-view camera motion, relative reflectance/albedo, object localization,
  visual similarity, and semantic/functional correspondence.
- ERQA: robot trajectory outcomes, gripper/camera action choice, contact,
  grasp state, task progress, and multi-view object-part matching.
- VStarBench: relative position and direct object attributes in real images.
  The spatial reasoning shape maps to `three_d`, while real-object recognition
  and rare attributes remain out of scope unless synthesized.
- GameQALite: 3D reconstruction and 3D maze tasks. These are 3D-flavored, but
  many are puzzle/game state tasks rather than perspective-scene reasoning.
- MathVista and MathVision: occasional 3D/block/object reasoning, but most
  failures are better assigned to geometry, puzzles, or illustrations unless
  camera/depth is the operative source of truth.

Boundary rule:

- Put a task in `three_d` when the verifier source of truth is a synthetic 3D
  world state: object coordinates, camera coordinates, visibility, projected
  geometry, depth, physical support, or multi-view consistency.
- Put it in `illustrations` when the source of truth is a 2D drawing of
  recognizable objects, semantic parts, style, or paired-image difference.
- Put it in `physics` when the answer depends on a physical law such as force,
  torque, momentum, work, optics, fluids, or electromagnetism rather than 3D
  spatial state alone.
- Put it in `puzzles` or `games` when the task is a voxel reconstruction game,
  maze, Rubik's cube, block-count puzzle, or other rule/state game, even if it
  displays a 3D object.
- Put it in `charts` when the visual is a 3D chart or surface encoding data.
- Put it in `pages` when the task is GUI or document target grounding.
- Keep natural-image recognition, open object identity, brand/logo recognition,
  and real-world semantics out of `three_d` unless all relevant objects and
  attributes are synthetic and metadata-backed.

## Current Three-D Surface

Closest active scene families:

- `object_scene_3d`: lettered candidate objects and unlettered context props on
  an open floor, table, or studio platform with a perspective camera.
- `room_scene_3d`: perspective indoor rooms with visible walls, furniture,
  wall-mounted objects, and distractor objects.

Closest active task families:

- Spatial:
  `proposal:three_d/spatial/camera_distance_extremum_label`,
  `proposal:three_d/spatial/object_relation_label`,
  `proposal:three_d/spatial/reference_nearest_label`,
  `proposal:three_d/spatial/between_references_label`,
  `proposal:three_d/spatial/occlusion_order_label`, and
  `proposal:three_d/spatial/height_extremum_label`.
- Room:
  `task_three_d__room__wall_mounted_object_count`,
  `task_three_d__room__wall_object_camera_distance_label`,
  `task_three_d__room__wall_object_same_wall_reference_label`, and
  `task_three_d__room__wall_object_side_relation_label`.

Current strengths:

- Perspective camera model with projected evidence bboxes.
- Camera-distance and depth-order tasks.
- Local object relation queries: on top of, under, inside, between, nearest,
  and height extrema.
- Basic indoor room geometry with wall-mounted object semantics.

Current limits:

- Object scenes use mostly simple geometric props rather than rich indoor or
  tabletop objects.
- Room tasks focus on wall-mounted objects, not free objects on furniture,
  floors, shelves, or in containers.
- The public output shape is mostly option labels and counts; there are no
  explicit point/bbox output tasks.
- There is no multi-view scene, controlled material/lighting scene, or robotics
  scene yet.

## Identified Issues

### D1. Indoor Spatial Relation Variety

Status: `partial`

EmbSpatial failures are dominated by indoor object relations: left, right,
above, under, near, far, and blocking. Current `three_d` spatial tasks cover
several relation forms, but the open object scene is abstract and the room
scene is mostly wall-object focused.

Closest existing tasks:

- `proposal:three_d/spatial/object_relation_label`
- `proposal:three_d/spatial/reference_nearest_label`
- `proposal:three_d/spatial/between_references_label`
- `proposal:three_d/spatial/occlusion_order_label`
- `task_three_d__room__wall_object_side_relation_label`

Interpretation:

- The reasoning form is covered, but scene realism and relation breadth are
  partial.
- Add room/tabletop/free-object scenes with furniture, shelves, counters, beds,
  desks, containers, and floor objects.
- The task should still use metadata-defined object categories and option
  labels, not open natural-image recognition.

### D2. Viewpoint-Dependent Left/Right/Above/Below

Status: `partial`

Current `object_scene_3d` has relation tasks such as on/under/inside and
distance-to-camera. Room has left-of-reference on a wall plane. Benchmarks
often ask viewpoint-relative left/right/above/below between arbitrary objects.

Closest existing tasks:

- `proposal:three_d/spatial/object_relation_label`
- `task_three_d__room__wall_object_side_relation_label`
- `proposal:icons/relation/relative_position_type`
- `proposal:illustrations/relation/named_object_side_count`

Interpretation:

- `three_d` should own this when left/right/above/below is computed from the
  rendered camera view or from explicit 3D frame metadata.
- Prompts must say whether "left" means image/view left or object/world left.
- First versions should use option labels for one unique candidate rather than
  free-form relation strings.

### D3. Depth, Occlusion, Contact, And Support

Status: `partial`

BLINK includes relative depth, while EmbSpatial includes blocking/touching.
TRACE has camera-distance and occlusion-order tasks, and object relations for
on/under/inside. It does not yet cover touching/contact counts, support chains,
stack order, or visible partial occlusion variants in room scenes.

Closest existing tasks:

- `proposal:three_d/spatial/camera_distance_extremum_label`
- `proposal:three_d/spatial/occlusion_order_label`
- `proposal:three_d/spatial/object_relation_label`
- `proposal:physics/mechanics/sticky_collision_direction_choice`

Interpretation:

- Direct 3D contact/support relation belongs in `three_d` when it is static
  scene metadata.
- Dynamic contact, collision outcomes, and force effects belong in `physics`
  or a robotics/manipulation scene.
- Evidence can remain the selected object bbox for label tasks, or bbox sets
  for counted contact/support objects.

### D4. Camera Distance And Near/Far Query Breadth

Status: `covered / partial`

EmbSpatial nearest/farthest prompts map strongly to current camera-distance and
reference-nearest tasks. What is missing is broader scene and phrasing variety:
nearest object from the viewer, closest/farthest among named indoor objects,
nearest to a moving camera, and distance comparisons between two candidates.

Closest existing tasks:

- `proposal:three_d/spatial/camera_distance_extremum_label`
- `proposal:three_d/spatial/reference_nearest_label`
- `task_three_d__room__wall_object_camera_distance_label`

Interpretation:

- Do not add many new task ids for the same closest/farthest contract.
- Prefer query/style variants and richer scene types unless we need a distinct
  output form such as binary comparison or pairwise ordering.

### D5. Multi-View Correspondence

Status: `gap / partial`

BLINK and ERQA include matching a marked point, part, line, or object across
camera changes. Current `three_d` tasks render one final view per instance and
do not expose multi-view correspondence.

Closest existing tasks:

- `proposal:three_d/spatial/camera_distance_extremum_label`
- `proposal:three_d/spatial/object_relation_label`
- `proposal:illustrations/visual/object_difference_count`
- `proposal:illustrations/visual/missing_patch_label`

Interpretation:

- This is one of the most natural `three_d` expansions.
- Use synthetic objects with stable part anchors or marked surface points. The
  verifier can project the same 3D point into two camera views and choose among
  labeled candidates.
- Keep the first version option-label based rather than asking for raw pixel
  coordinates.

### D6. Controlled Material, Lighting, And Reflectance

Status: `gap / partial`

BLINK relative reflectance/albedo is a common failure pattern. Current `three_d`
does not model semantic materials or lighting beyond non-semantic visual
variation.

Closest existing tasks:

- `proposal:three_d/spatial/occlusion_order_label`
- `proposal:three_d/spatial/camera_distance_extremum_label`
- `proposal:illustrations/visual/object_difference_count`

Interpretation:

- `three_d` can add controlled material/lighting tasks if albedo, lighting,
  shadow, and observed color are explicitly separated in metadata.
- Avoid changing ordinary color semantics for existing tasks.
- Start with option labels or binary choices such as which marked patch has
  darker intrinsic color, which surface is more illuminated, or which object is
  in shadow.

### D7. Object Attributes, Pose, And Part Semantics

Status: `partial / boundary-sensitive`

VStarBench direct attributes include color, pose, logo/species, and material.
Current `three_d` objects are simple shapes and room props. Some attributes fit
3D, but many are better handled by `illustrations` or out of scope.

Closest existing tasks:

- `proposal:three_d/spatial/object_relation_label`
- `task_three_d__room__wall_mounted_object_count`
- `proposal:illustrations/counting/shop_color_attribute_count`
- `proposal:icons/counting/single_attribute_match_count`

Interpretation:

- 3D-owned attributes should be geometric or rendering-grounded: object pose,
  orientation, support state, material/albedo, shadow state, visibility, or
  which face/side is visible.
- Real species, logos, brands, fine-grained natural categories, and open visual
  identity should stay out of `three_d`.

### D8. Object Localization And Grounding Outputs

Status: `boundary-sensitive`

BLINK has object localization and point/bbox questions. TRACE `three_d`
evidence already contains projected bboxes, but current tasks generally answer
with option labels or counts.

Closest existing tasks:

- `proposal:three_d/spatial/object_relation_label`
- `proposal:three_d/spatial/occlusion_order_label`
- `proposal:pages/relation/command_intent_target_label`

Interpretation:

- Do not add raw point/bbox output just because evidence exists.
- If we need grounding-style `three_d` tasks, prefer label selection over
  lettered objects, marked points, or marked parts.
- GUI and document grounding remains `pages`.

### D9. Robotics And Manipulation Scenes

Status: `gap`, possible future `three_d` scene.

ERQA failures involve robot grippers, camera-attached actions, contact, grasp
state, trajectory outcome, and task progress. These are not covered by current
static `three_d` scenes, but they are plausibly a new scene family inside
`three_d` because the world model is 3D, camera-relative, and action-state
grounded.

Closest existing tasks:

- `proposal:three_d/spatial/object_relation_label`
- `proposal:three_d/spatial/camera_distance_extremum_label`
- `proposal:physics/mechanics/sticky_collision_direction_choice`
- `proposal:pages/process/flow_condition_path_endpoint_label`

Interpretation:

- Add robotics only if embodied evaluation becomes a priority.
- The first version should be a controlled synthetic tabletop manipulation
  scene, not open robot video understanding.
- It should use typed metadata for gripper pose, contact, grasped object,
  target region, simple trajectory, and final object state.

### D10. 3D Reconstruction, Voxel, And Maze Tasks

Status: `partial`, mostly outside `three_d`.

GameQALite includes 3D reconstruction and 3D maze tasks. These are visually 3D
but usually operate as puzzle/game-state reasoning over voxels, projections, or
grid routes.

Closest existing tasks:

- `proposal:puzzles/spatial/cube_visible_projection_count`
- `proposal:puzzles/spatial/cube_structure_change_count`
- `proposal:puzzles/spatial/cube_count`
- `task_games__minecraft__resource_route_cost_value`
- `task_games__minecraft__tunnel_clearance_count`

Interpretation:

- Keep voxel reconstruction and maze-state tasks in `puzzles` or `games`
  unless the verifier depends on perspective camera geometry rather than a
  puzzle grid.
- `three_d` may still share renderer helpers if needed, but task ownership
  should follow the reasoning contract.

### D11. 3D Charts And Surfaces

Status: `covered elsewhere / boundary`

TRACE has chart-owned 3D bar and surface tasks. These should not migrate into
`three_d` because the source of truth is quantitative data encoding, not object
spatial state.

Closest existing tasks:

- `proposal:charts/three/d_bar_axis_total_value`
- `proposal:charts/three/d_surface_extremum_label`
- `proposal:charts/three/d_reference_nearest_label`

Interpretation:

- Keep chart-encoded 3D visuals in `charts`.
- Only use `three_d` when the answer is about object-world geometry, camera
  projection, visibility, or scene state.

## Candidate Changes

### C1. Rich Indoor Object Scene

Extend `room_scene_3d` beyond wall-mounted objects to include free objects on
tables, desks, beds, shelves, floors, counters, containers, and cabinets. Add
object categories with controlled prompt names and enough same-type distractors
to require the spatial relation, not only recognition.

Candidate tasks:

- `proposal:three_d/room/object_relation_label`
- `proposal:three_d/room/object_view_side_relation_label`
- `proposal:three_d/room/nearest_object_label`
- `proposal:three_d/room/object_support_label`
- `proposal:three_d/room/container_object_count`

Addresses: D1, D2, D3, D4.

### C2. View-Relative Relation Variants

Add explicit image/view-frame relation tasks for arbitrary 3D objects. The
prompt should say "in the image" or "from the camera view" so the relation is
not confused with world-frame left/right.

Candidate tasks:

- `proposal:three_d/spatial/view_left_right_label`
- `proposal:three_d/spatial/view_above_below_label`
- `proposal:three_d/spatial/view_relation_count`
- `proposal:three_d/spatial/pair_relation_choice`

Addresses: D2.

### C3. Contact, Support, And Stack Relations

Add static contact/support reasoning with metadata-defined contact pairs and
support chains.

Candidate tasks:

- `proposal:three_d/spatial/touching_object_count`
- `proposal:three_d/spatial/supported_by_label`
- `proposal:three_d/spatial/stack_order_label`
- `proposal:three_d/spatial/objects_on_support_count`
- `proposal:three_d/spatial/partly_occluded_count`

Addresses: D3.

### C4. Multi-View Correspondence Scene

Render two views of the same 3D scene or object, with a marked reference point,
part, or object in one view and labeled candidates in the other.

Candidate tasks:

- `proposal:three_d/spatial/multiview_object_match_label`
- `proposal:three_d/spatial/multiview_point_match_label`
- `proposal:three_d/spatial/multiview_part_match_label`
- `proposal:three_d/spatial/camera_motion_direction_label`

Addresses: D5.

### C5. Material And Lighting Scene

Add a controlled renderer layer for intrinsic albedo, light direction, shadow
state, gloss/roughness buckets, and observed brightness. This should be an
explicit scene family or query-owned layer, not a silent global visual
variation.

Candidate tasks:

- `proposal:three_d/material/albedo_comparison_label`
- `proposal:three_d/material/lit_shadow_label`
- `proposal:three_d/material/brightness_vs_albedo_choice`
- `proposal:three_d/material/same_albedo_match_label`

Addresses: D6, D7.

### C6. 3D Pose And Visible-Face Tasks

Add pose/orientation tasks for simple objects with marked faces or asymmetric
parts.

Candidate tasks:

- `proposal:three_d/spatial/visible_face_label`
- `proposal:three_d/spatial/object_orientation_label`
- `proposal:three_d/spatial/rotated_match_label`
- `proposal:three_d/spatial/face_count_visible_value`

Addresses: D5, D7.

### C7. Grounded Label Selection For Objects Or Parts

If grounding-style coverage is needed, use label selection over marked objects,
parts, faces, or points rather than direct point/bbox output.

Candidate tasks:

- `proposal:three_d/spatial/marked_part_label`
- `proposal:three_d/spatial/marked_point_correspondence_label`
- `proposal:three_d/room/named_object_target_label`

Addresses: D8.

### C8. Robotics / Manipulation Scene

Add only after deciding that ERQA-style embodied reasoning is in scope. This
should be a distinct scene family, for example `robot_tabletop_scene_3d`, with
gripper pose, grasp state, contact, target regions, trajectory arrows, and
post-action object state in metadata.

Candidate tasks:

- `proposal:three_d/robotics/grasped_object_label`
- `proposal:three_d/robotics/contact_state_label`
- `proposal:three_d/robotics/trajectory_endpoint_label`
- `proposal:three_d/robotics/action_effect_relation_label`
- `proposal:three_d/robotics/camera_motion_choice`
- `proposal:three_d/robotics/task_progress_label`

Addresses: D9.

### C9. Keep Neighboring Gaps Out Of Three-D

Do not solve these inside current `three_d`:

- Voxel reconstruction, 3D maze, Rubik's cube, block-count puzzle, and
  projection puzzles: `puzzles` or `games`.
- 3D charts and surfaces: `charts`.
- Pure force, work, collision, optics, or other law-based physical reasoning:
  `physics`.
- GUI/document point grounding: `pages`.
- Natural-image recognition, rare object identity, logos, species, art style,
  and forensic detection: out of scope unless metadata-grounded in another
  synthetic domain.

Addresses: D10, D11.

## Suggested First Wave

1. Expand `room_scene_3d` to support free indoor objects and add
   `proposal:three_d/room/object_relation_label`.
2. Add view-relative left/right/above/below tasks over the existing
   `object_scene_3d` or the expanded room scene.
3. Add one contact/support task, preferably
   `proposal:three_d/spatial/objects_on_support_count` or
   `proposal:three_d/spatial/supported_by_label`.
4. Add a multi-view correspondence scene with
   `proposal:three_d/spatial/multiview_point_match_label`.
5. Defer robotics and material/lighting until the static room and multi-view
   expansion has been reviewed, because those introduce larger renderer and
   metadata contracts.
