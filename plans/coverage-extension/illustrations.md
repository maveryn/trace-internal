# Illustrations Coverage Extension

## Scope

This note tracks illustration-domain coverage gaps found from the external
benchmark failure analysis, then records candidate changes for `illustrations`.

Current working conclusion: the illustrations domain already has broad
synthetic object reasoning coverage. Active tasks cover object type counts,
feature-relative counts, indoor surface/container counts, market/shop counts,
library book counts, park/playground people and equipment counts, transit
terminal person/luggage/queue counts, construction-site worker/material/equipment
counts, visible-part counts, counterfactual counts, spatial side counts, paired
scene differences, jigsaw ordering, rotated tiles, missing patches, and odd
scene selection. The remaining benchmark gaps are mostly about density,
crowding, repeated small objects, richer controlled attributes, multi-image
correspondence, and natural-image-style scene variety.

Relevant benchmark cues:

- CountQA: dense repeated object counting in natural scenes, including objects
  such as cups, chairs, books, pieces, balls, boxes, pens, tiles, cards,
  bottles, tape rolls, bookmarks, and wall tiles.
- VStarBench: direct object attributes such as color, material, pose, logos or
  species, plus relative left/right or above/below relations between named
  objects.
- BLINK: semantic correspondence across object instances, functional
  correspondence across actions/tools, visual correspondence under viewpoint or
  lighting changes, jigsaw/missing-corner matching, relative reflectance, object
  localization, and visual similarity.
- MathVista and MathVision: object counting, visible-part counting, missing
  blocks/bricks/dots/digits, abstract scene counting, and occasional point or
  answer selection over drawings.
- SimpleVQAEn: a small grounded subset of counting, spatial, and attribute
  questions, plus many open-world identity/factual questions that should stay
  out of TRACE.

Boundary rule:

- Put a task in `illustrations` when the source of truth is a synthetic drawing
  of recognizable objects, their visible parts, controlled attributes, relative
  positions, occlusion, or paired-image differences.
- Put it in `icons` when the objects are symbolic icon glyphs and the task is
  primarily about icon identity, color, orientation, size, or abstract pattern.
- Put it in `three_d` when camera geometry, true depth, 3D pose, or multi-view
  object geometry is the verifier source of truth.
- Put it in `puzzles` when the primary operation is assembly, hidden-rule
  completion, jigsaw puzzle solving, tiling, or puzzle-state manipulation.
- Keep natural-image identity, rare real categories, brand/logo recognition,
  celebrity/person identity, art-style knowledge, and external factual lookup
  out of TRACE unless the answer is explicitly represented in controlled
  synthetic metadata.

## Current Illustrations Surface

Closest active scene families:

- `mixed_object_canvas`: non-overlapping synthetic animals, vehicles, plants,
  people, sky objects, household objects, tools, and scene fixtures on simple
  backgrounds.
- `environment_object_canvas`: roads, rivers, bridges, crosswalks, skyline
  buildings, foreground objects, and feature-relative placement metadata.
- `indoor_room_canvas`: living room, kitchen, study, and bedroom scenes with
  furniture, surfaces, containers, small objects, and side/surface/container
  metadata.
- `urban_market_canvas`: shop/stall fronts, signs, awnings, counters,
  inventory items, customers, and market-lane layouts.
- `library_canvas`: labeled shelf sections, books, reading tables, people, and
  library decor.
- `park_playground_canvas`: park/playground zones, equipment, activity-labeled
  people, paths, benches, plants, and pond/garden areas.
- `transit_terminal_canvas`: rail/bus/airport settings, boarding areas,
  people, luggage, queues, kiosks, signs, and service counters.
- `construction_site_canvas`: site zones, workers, safety gear, material
  stacks, construction equipment, vehicles, and scaffolding/crane/roadwork
  decor.
- Shared visual scenes: paired scene differences, jigsaw board ordering,
  rotated tile detection, missing-patch options, and odd-scene selection.

## Identified Issues

### L1. Dense Repeated Object Counting

Status: `partial`

CountQA is dominated by dense natural-image object counting. TRACE has multiple
synthetic counting tasks, but current scenes are not always designed for very
dense repeated small objects such as wall tiles, bookmarks, tape rolls, pens,
books, bottles, cups, chairs, boxes, cards, or balls.

Closest existing tasks:

- `proposal:illustrations/counting/type_count`
- `proposal:illustrations/counting/library_book_count`
- `proposal:illustrations/counting/shop_selling_object_count`
- `proposal:illustrations/counting/object_type_on_surface_count`
- `proposal:illustrations/counting/material_stack_type_count`
- `proposal:icons/counting/multi_attribute_match_count`

Interpretation:

- The reasoning contract is covered: count objects of a named type.
- The missing coverage is density, repeated-object layout, and crowded but
  still synthetic scenes.
- We should not try to reproduce natural-image recognition. Instead, add
  controlled dense tabletop, shelf, wall, desk, pantry, classroom, bathroom, or
  storage scenes with metadata-backed repeated objects.

### L2. Positional And Zone-Filtered Object Counts

Status: `partial`

CountQA and VStarBench include subset counts using spatial or contextual
phrases such as on the wall, on the left, in the foreground, on a table, in a
zone, near an object, or inside a container. TRACE has several relation and
zone tasks, but the scene vocabulary can be broader.

Closest existing tasks:

- `proposal:illustrations/counting/feature_relation_object_count`
- `proposal:illustrations/counting/object_type_on_surface_count`
- `proposal:illustrations/counting/container_object_count`
- `proposal:illustrations/counting/equipment_in_zone_count`
- `proposal:illustrations/counting/person_in_park_zone_count`
- `proposal:illustrations/relation/named_object_side_count`
- `proposal:illustrations/relation/furniture_side_count`

Interpretation:

- Existing tasks cover the reasoning form.
- Add more scene-specific zones and supports before adding generic spatial
  language. Useful additions include wall/floor/tabletop/shelf/counter,
  foreground/background bands, left/right room regions, aisle/shelf sections,
  and near/far relative to a marked object.

### L3. Attribute-Filtered Object Counts And Lookup

Status: `partial`

VStarBench and CountQA include color, material, pose, shape, and sometimes logo
or species attributes. TRACE has color attributes in shops, books, worker gear,
icons, and some person activity tasks, but there is no general illustration
attribute layer across object types.

Closest existing tasks:

- `proposal:illustrations/counting/shop_color_attribute_count`
- `proposal:illustrations/counting/library_book_count`
- `proposal:illustrations/counting/worker_safety_gear_count`
- `proposal:illustrations/counting/person_activity_count`
- `proposal:icons/counting/single_attribute_match_count`
- `proposal:icons/counting/multi_attribute_match_count`

Interpretation:

- Controlled color/material/pose/shape attributes fit `illustrations`.
- Brand/logo identity and rare species recognition should stay out of scope
  unless we synthesize a small explicit symbol vocabulary.
- First versions should prefer counts or option labels over free-form attribute
  strings.

### L4. Multi-Class Summed Counts And Filtered Subtraction

Status: `partial`

CountQA and MathVista include prompts that sum multiple object classes or
subtract filtered groups from a total. TRACE has many single-class count tasks
and page arithmetic, but illustration-specific multi-class arithmetic is sparse.

Closest existing tasks:

- `proposal:illustrations/counting/type_count`
- `proposal:illustrations/counting/feature_relation_object_count`
- `proposal:pages/arithmetic/section_expression_value`
- `proposal:icons/counting/multi_attribute_match_count`
- `proposal:illustrations/counterfactual/object_count_after_edit`

Interpretation:

- This is a useful query expansion if kept small and metadata-grounded.
- Good contracts: count A plus B, count A minus B, count objects left after
  excluding a type/attribute, or compare whether count A is greater than count
  B.
- Avoid list outputs and broad natural-language filters.

### L5. Fine-Grained Object Parts, Pose, And Activity Attributes

Status: `partial`

VStarBench includes pose questions, while MathVision includes visible parts,
missing pieces, and object/digit/dot counts. TRACE has visible-part counting,
person activity counts, and worker gear counts, but only a small set of part
and pose categories.

Closest existing tasks:

- `proposal:illustrations/counting/visible_part_count`
- `proposal:illustrations/counterfactual/visible_part_count`
- `proposal:illustrations/counting/person_activity_count`
- `proposal:illustrations/counting/worker_safety_gear_count`
- `proposal:illustrations/counting/person_using_equipment_count`

Interpretation:

- Extend the object library's part and pose metadata before adding many tasks.
- Useful new parts include wheels, windows, buttons, legs, arms, handles,
  straps, pockets, screens, labels, caps, and lids.
- Useful pose/activity variants include walking, standing, sitting, running,
  carrying, pointing, reading, holding, and using a tool.

### L6. Multi-Image Semantic Correspondence

Status: `gap / partial`

BLINK includes semantic correspondence across object instances, such as finding
the corresponding part on a different object of the same category. TRACE has
paired scene differences, jigsaw/missing-patch tasks, and object-part metadata,
but not a direct part-correspondence task across two object instances.

Closest existing tasks:

- `proposal:illustrations/visual/object_difference_count`
- `proposal:illustrations/visual/missing_patch_label`
- `proposal:illustrations/visual/rotated_tile_label`
- `proposal:icons/transformation/pair_attribute_rule_count`
- `proposal:three_d/spatial/camera_distance_extremum_label`

Interpretation:

- This is one of the strongest illustration-owned BLINK gaps.
- It requires consistent part metadata across object instances and option
  markers on candidate parts.
- Keep it synthetic: same object category, controlled stylization, visible part
  labels or markers, and one unique corresponding part.

### L7. Functional Correspondence Across Tools Or Actions

Status: `gap / boundary-sensitive`

BLINK functional correspondence asks which part of different objects plays the
same functional role in an action, such as grasping, cutting, pouring, or
pressing. TRACE does not currently have a functional affordance scene.

Closest existing tasks:

- `proposal:illustrations/counting/person_activity_count`
- `proposal:illustrations/counting/worker_safety_gear_count`
- `proposal:illustrations/visual/object_difference_count`

Interpretation:

- This can fit illustrations if the functions are synthetic and explicitly
  metadata-defined: handle, blade, spout, wheel, button, writing tip, lid,
  strap, screen.
- It should not require real-world affordance knowledge beyond a controlled
  vocabulary rendered in the object library.

### L8. Visual Correspondence Under Style, View, Or Lighting Change

Status: `partial`

BLINK includes visual correspondence under viewpoint or lighting changes, plus
relative reflectance. TRACE has image comparison and rotated-tile tasks, and
global noise now covers many image degradations, but not a targeted material or
lighting correspondence scene in illustrations.

Closest existing tasks:

- `proposal:illustrations/visual/rotated_tile_label`
- `proposal:illustrations/visual/object_difference_count`
- `proposal:illustrations/visual/missing_patch_label`
- `proposal:three_d/spatial/camera_distance_extremum_label`
- `proposal:three_d/spatial/occlusion_order_label`

Interpretation:

- Pure 3D camera/viewpoint correspondence belongs in `three_d`.
- Illustration-owned versions can cover style changes, color-lightness changes,
  material swatches, and same-part matching across stylized render variants.
- Relative reflectance should only be added if we can define albedo/material
  metadata separately from shading/noise.

### L9. Object Localization And Grounding Outputs

Status: `partial / low priority`

BLINK and VStarBench include localization or pointing tasks. TRACE illustration
tasks already use bbox evidence for counted or selected objects, but the final
answer is usually a count or label rather than a point/bbox.

Closest existing tasks:

- `proposal:illustrations/visual/missing_patch_label`
- `proposal:illustrations/visual/rotated_tile_label`
- `proposal:illustrations/visual/odd_scene_label`
- `proposal:pages/relation/command_intent_target_label`
- `proposal:icons/relation/relative_position_type`

Interpretation:

- The schema can already ground evidence, so this is not an urgent missing
  capability.
- Add explicit localization only if we decide to train point/bbox answer tasks.
  Otherwise, keep using option labels with bbox evidence.

### L10. Open-World Recognition And Factual Knowledge

Status: `out of scope`

SimpleVQAEn and VStarBench include public facts, identity, logos, rare species,
art styles, real places, and open-world object categories.

Interpretation:

- Keep these out of TRACE unless the answer is synthetic, visible, and
  metadata-grounded.
- Do not add broad "what is this real object/person/place" tasks to
  illustrations.

## Candidate Changes

### M1. Add Dense Repeated-Object Scene Families

Decision: candidate first wave.

Issues addressed:

- L1. Dense repeated object counting.
- L2. Positional and zone-filtered object counts.
- L4. Multi-class summed counts and filtered subtraction.

Implementation idea:

- Add or extend scene families for dense but readable repeated objects:
  `tabletop_collection_canvas`, `shelf_storage_canvas`,
  `bathroom_wall_canvas`, `classroom_desk_canvas`, `pantry_shelf_canvas`, and
  `workbench_canvas`.
- Candidate tasks:
  - `proposal:illustrations/counting/dense_object_type_count`
  - `proposal:illustrations/counting/dense_zone_object_count`
  - `proposal:illustrations/counting/dense_surface_object_count`
  - `proposal:illustrations/counting/dense_two_type_sum_value`
  - `proposal:illustrations/counting/dense_exclusion_remaining_count`
- Seed object pools from benchmark signals: cups, chairs, books, tiles, pens,
  bottles, boxes, balls, cards, tape rolls, bookmarks, and small tools.
- Keep object bboxes individually trace-visible and reject scenes where small
  repeated objects become indistinguishable.

### M2. Add A General Controlled Attribute Layer

Decision: candidate first wave.

Issues addressed:

- L3. Attribute-filtered object counts and lookup.
- L5. Fine-grained object parts, pose, and activity attributes.

Implementation idea:

- Extend object records with controlled attributes where appropriate:
  color, material, pattern, pose, orientation, open/closed state,
  filled/empty state, worn/carried state, and visible mark/symbol.
- Candidate tasks:
  - `proposal:illustrations/counting/attribute_object_count`
  - `proposal:illustrations/counting/multi_attribute_object_count`
  - `proposal:illustrations/relation/object_attribute_label`
  - `proposal:illustrations/counting/pose_activity_count`
  - `proposal:illustrations/counting/part_presence_object_count`
- Prefer option-letter or integer answers. Use attribute-string answers only
  for a small closed vocabulary with exact prompt templates.

### M3. Expand Part Metadata And Visible-Part Tasks

Decision: candidate.

Issues addressed:

- L5. Fine-grained object parts, pose, and activity attributes.
- L6. Multi-image semantic correspondence.

Implementation idea:

- Add part records for additional object families and ensure each part has a
  stable semantic id, kind, and bbox.
- Candidate tasks:
  - `proposal:illustrations/counting/part_kind_count`
  - `proposal:illustrations/relation/marked_part_type_label`
  - `proposal:illustrations/visual/missing_part_label`
  - `proposal:illustrations/counterfactual/part_count_after_edit`
- This should precede correspondence tasks so part identities are reliable.

### M4. Add Multi-Image Object-Part Correspondence

Decision: candidate first wave if BLINK is a priority.

Issues addressed:

- L6. Multi-image semantic correspondence.
- L8. Visual correspondence under style, view, or lighting change.

Implementation idea:

- Add a two-panel scene with a reference object part marked in the left panel
  and several candidate marked parts on the right panel.
- Candidate tasks:
  - `proposal:illustrations/visual/corresponding_part_label`
  - `proposal:illustrations/visual/same_part_after_style_change_label`
  - `proposal:illustrations/visual/same_part_after_pose_change_label`
  - `proposal:illustrations/visual/matching_object_instance_label`
- Keep object categories controlled and exclude ambiguous or hidden parts.
- Evidence should include the reference part bbox and the selected candidate
  part bbox.

### M5. Add Controlled Functional Correspondence

Decision: lower-priority candidate.

Issues addressed:

- L7. Functional correspondence across tools or actions.

Implementation idea:

- Add a small affordance vocabulary to object parts: handle, blade, tip, spout,
  button, wheel, strap, screen, lid, opening, grip, and writing end.
- Candidate tasks:
  - `proposal:illustrations/visual/functional_part_match_label`
  - `proposal:illustrations/relation/affordance_part_count`
  - `proposal:illustrations/visual/tool_action_part_label`
- Keep all functions visible or stated in prompt templates; avoid relying on
  open-ended real-world affordance knowledge.

### M6. Add Material And Reflectance Mini-Scenes

Decision: lower-priority candidate.

Issues addressed:

- L3. Attribute-filtered object counts and lookup.
- L8. Visual correspondence under style, view, or lighting change.

Implementation idea:

- Add synthetic material swatches or objects with metadata-separated material,
  base color, and shading level.
- Candidate tasks:
  - `proposal:illustrations/relation/material_attribute_label`
  - `proposal:illustrations/comparison/reflectance_label`
  - `proposal:illustrations/counting/material_object_count`
- Avoid conflict with global noise or color semantics by keeping material
  labels explicit and using strong visual separation.

### M7. Add Scene-Specific Style And Density Packs

Decision: candidate after semantic gaps.

Issues addressed:

- L1. Dense repeated object counting.
- L8. Visual correspondence under style, view, or lighting change.

Implementation idea:

- Add scene style packs such as product-shelf, catalog, cluttered desk,
  classroom worksheet, storage room, bathroom wall, tool bench, pantry,
  crowded park, and busy terminal.
- Keep synthetic drawing semantics and object bboxes stable.
- Do not let background decor become countable unless the task sampler creates
  explicit metadata for it.

## Suggested First Wave

1. Add dense repeated-object scene families, because CountQA is the strongest
   illustration-relevant benchmark signal and current counting tasks cover the
   reasoning but not the crowding/density regime.
2. Add a general controlled attribute layer, because VStarBench and CountQA
   repeatedly ask for color/material/pose/state filters and current coverage is
   scene-specific.
3. Expand part metadata, then add object-part correspondence if BLINK becomes a
   target benchmark.
4. Add multi-class arithmetic count variants after dense scenes exist, because
   they reuse the same object records and evidence.
5. Leave open-world identity, real logos, rare species, art style, and factual
   knowledge out of illustrations.

## Remaining Open Questions

1. Which dense scene should be first: tabletop/desk, shelf/storage, bathroom
   wall, pantry, classroom, or workbench?
2. Should attribute lookup answers be option letters or closed-vocabulary
   strings?
3. How much object overlap/crowding should dense illustrations allow before
   evidence review becomes unreliable?
4. Should BLINK-style correspondence live in `illustrations`, `three_d`, or a
   shared multi-image correspondence family split across both domains?
