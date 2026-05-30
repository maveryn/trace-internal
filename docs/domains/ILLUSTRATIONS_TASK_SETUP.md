# Illustrations Task Setup

## Purpose
Capture the active contract for the `illustrations` domain.

Illustrations covers synthetic drawings of recognizable objects. The domain is
for object recognition, visible-part counting, and spatial reasoning over
drawn objects. It does not use natural images, external object detectors, or
free-form captions.

## Active families
1. Current active `task_group` values:
   - `counting`
   - `counterfactual`
   - `relation`
   - `visual`
2. Current active task ids and scene counts are generated in
   `docs/ACTIVE_TASK_INVENTORY.md`.

## Calibration state
Illustration tasks are pending fresh `v0` task review and qwen25vl7b
solve-rate calibration unless `review/calibration_sweep_status.json` records
regenerated baseline-tagged artifacts for a task. Current retained solve-rate
artifacts must use `100` prompts with `24` rollouts per prompt unless a task
note says otherwise. The current domain inventory is generated in
`docs/ACTIVE_TASK_INVENTORY.md`; task-level review sidecars live under
`review/task-reviews/illustrations/<scene_id>/<task_id>/`.

## Scene contract
1. `object_field` renders a single canvas with multiple non-overlapping
   synthetic objects.
2. `environment` renders curved roads, curved rivers, bridges,
   crosswalks, city skylines, and mixed foreground objects.
3. `indoor_room` renders room backgrounds with semantic furniture,
   surfaces, containers, and small household/tool/plant/fruit objects.
4. `library` renders a synthetic library with labeled shelf sections,
   visible book spines/covers, reading tables, people, plants, desk books, and
   other non-query decor. Library tasks count only semantic book records
   assigned to labeled sections; desk books and people are visual distractors.
   Section labels sample one font from the role-appropriate shared font pool per scene
   and use it consistently across all shelf-section labels.
5. `park_playground` renders a synthetic park/playground with curved
   walking paths, playground equipment, picnic/pond/garden zones, benches,
   trees, flowers, lamps, and activity-labeled people.
6. `transit_terminal` renders a synthetic transit terminal with labeled
   boarding areas, train/bus/airport visual settings, vehicles or gates,
   departure boards, clocks, info kiosks, benches, service counters, queue ropes,
   loose luggage, luggage carts, and people assigned to semantic boarding
   areas or queues.
7. `construction_site` renders a synthetic construction site with
   labeled excavation/loading/roadwork zones, workers, material stacks,
   construction vehicles/equipment, scaffold/crane/roadwork decor, and varied
   site layouts/styles. Construction zone labels sample one font from the
   role-appropriate shared font pool per scene and use it consistently across all zone
   labels; the resolved font trace is recorded in render metadata.
8. Shared visual task scenes render derived canvases from illustration sources:
   `difference_pair` shows Scene A/B panels, `image_cutout_board`
   supports jigsaw-style image reconstruction layouts including 1x3 and 2x2
   anchored-piece boards and a 3x3 rotated-tile grid, and
   `missing_patch` shows a source image with a missing
   region plus labeled patch options. These tasks may draw their source image
   from current illustration scene renderers but ask scene-agnostic visual
   comparison or reconstruction questions. Missing-patch and jigsaw-order
   sources exclude `object_field`.
9. Public object taxonomy is global across illustration scenes. Scene
   interfaces should request object/background types plus attributes; scenes
   own grammar, placement constraints, and allowed object subsets, not drawing
   implementations or private object naming conventions.
10. Object/background drawing and object metadata are separated:
   - `object_catalog.py` is the single source for drawable object, fixture,
     region, and background vocabularies, including render layer, size class,
     placement tags, scene tags, renderer id, public names, labels, and variant
     ids. Use its tag, scene, layer, and size-class query helpers instead of
     re-declaring object pools in scene code.
   - `object_library.py` owns reusable glyph drawing and visible-part records
     for shared synthetic objects. `person_rendering.py` owns shared
     person-appearance helpers used by shared people, park people, transit
     people, and construction workers.
   - `object_schema.py` defines the normalized `object_record` payload.
   - `object_registry.py` adapts catalog-backed public object type definitions
     into the normalized `object_record` contract, including families,
     semantic/visual attribute slots, render layer, size class, and placement
     tags.
   - `scene_objects.py` extracts normalized object records from mixed
     scene-specific entity payloads for downstream scene-agnostic tasks.
   - `*_rendering.py` modules own PIL drawing for scene backgrounds, fixtures,
     and scene-specific object renderers.
   - `*_scene.py` modules are drawing-free public interfaces. Architecture
     tests enforce that they do not import PIL, create images/draw contexts, or
     define local `_draw_*` helpers.
11. Each object-capable entity should include an `object_record` with:
   - `object_id`, public `object_type`, `public_name`, `family`, and bbox,
   - `semantic_attributes` used by tasks/verifiers, such as activity, zone,
     material type, or queried color name,
   - `visual_attributes` used only for rendering variation, such as RGB fills,
     style id, and person `gender_id`,
   - `role`, `source_entity_type`, and optional visible part records.
12. Existing scene-specific entity fields remain available for compatibility,
   but new cross-scene visual tasks should consume `object_record` or
   `extract_scene_object_records(...)` instead of branching on every scene.
13. Person-like entities use public categories such as `person`,
   `pedestrian_with_bag`, or `worker`. They sample render-only
   `gender_id` from `male`/`female` with equal probability where supported, but
   no task prompt or verifier should ask a gender-specific question. `child` is
   not a public object category; `childrens_corner` remains only a library
   background setting.
15. Current illustration styles are `flat_vector`, `outlined_cartoon`,
   `paper_cutout`, and `soft_shadow`.
16. The shared foreground object library currently contains 65 reusable
   illustration-native object types. It includes common scene objects plus a
   small set borrowed from the named-icon vocabulary as native illustration
   drawings: backpack, bucket, camera, gift, guitar, kite, lightbulb, mailbox,
   shovel, soccer ball, teapot, and train.
17. Current backgrounds for `object_field` are simple non-semantic canvas
   variants such as studio, meadow, sky/ground, tabletop, paper, and shelf.
   Each instance samples explicit background geometry such as horizon/table
   height, shelf levels, paper rule spacing, color jitter, and a placement
   layout (`free_scatter`, `loose_grid`, `two_clusters`, or `diagonal_band`).
   The same sampled layout is used for object placement and rendering.
18. Current environment themes are `park_road`, `river_meadow`, `road_and_river`,
    `canal_city`, and `skyline_street`.
19. Current indoor themes are `living_room`, `kitchen`, `study`, and `bedroom`.
20. Current library settings are `reading_room`, `archive_room`, and
    `childrens_corner`.
21. Current park settings are `playground_lawn`, `picnic_park`,
    `pond_playground`, and `flower_garden`.
22. Current transit-terminal settings are `rail_station`, `bus_terminal`, and
    `airport_concourse`.
23. Current construction-site settings are `urban_build`, `roadwork`,
    `foundation_yard`, and `scaffold_site`.
24. Object placement should be habitat-aware rather than uniformly random:
   airplanes, birds, butterflies, and kites use sky bands; cars/buses/trucks/
   bicycles plus taxis/vans/scooters use roads when a road scene is present;
   boats, sailboats, canoes, fish, ducks, buoys, and lily pads use rivers when
   a river scene is present; people, plants, animals, and household/tool/
   scene-fixture objects use land or surface bands. Land-object pools are
   theme-specific so city scenes favor pedestrians and street fixtures, while
   park/meadow scenes favor people, animals, plants, benches, small outdoor
   objects, cameras, backpacks, and sports/tool props.
   City/canal themes may cap foreground object count slightly below the global
   request to keep crowded skyline scenes legible.
25. Environment features are semantic entities:
   - roads and rivers store curved path points, width, bbox, and nearest-point
     geometry support plus a sampled large-feature style id,
   - bridges and crosswalks store bboxes and crossing relationships,
   - buildings store building bboxes, roof type, door bbox, window bboxes, and
     lit-window bboxes; each building also records a sampled building style id.
26. Clouds and sun are non-counted sky decor features in environment scenes;
    they enrich backgrounds but do not enter foreground-object count tasks.
27. Benches, road signs, streetlamps, traffic lights, mailboxes, trash bins,
    and similar scene fixtures are foreground objects when placed through the
    object library, so they are eligible for object-level count tasks.
28. Object placements in environment scenes record the sampled zone and
    precomputed relation metadata to roads/rivers, including above/below/on
    relation, signed vertical distance, nearest distance, nearest point, and
    whether the object lies between the road and river when both are present.
29. Task generators may request exact road/river placement counts from the
    renderer when a count target must be balanced by construction; the renderer
    still owns final object positions and bboxes.
30. Indoor-room placements record whether each object is on a named surface,
    inside a named container, or in a side region relative to named furniture.
    Furniture, surface, and container bboxes are exported in the render map.
31. Indoor surfaces are rendered as 2.5D perspective planes: table, shelf, and
    counter tops use trapezoid support geometry, surface objects record a
    pixel-space contact point and depth value, and evidence remains the final
    tight rendered object bbox.
32. Indoor-room furniture, shelf/counter/table geometry, containers, rugs,
    window placement, and large-object colors are sampled per instance. Layout
    variants swap the cabinet/shelf and sofa/container sides so the room
    topology is not fixed. The renderer exports the sampled furniture,
    surface, and container bboxes plus each surface plane so task answers and
    evidence stay tied to the same geometry that is drawn.
33. Indoor-room visual style variation applies to both foreground objects and
    room structure. The room renderer samples furniture shape variants
    including table-leg, sofa, cabinet, shelf, rug-pattern, container, floor,
    window, and wall-decor styles while preserving the same semantic
    furniture/surface/container bboxes used by tasks.
34. Environment scenes sample explicit layout metadata per instance, including
    land/sky boundary, road/river base paths, path amplitudes, feature widths,
    city building horizon, background colors, and zone-bias weights. This keeps
    road/river/city scenes varied while preserving semantic path, feature, and
    object-placement metadata for verification.
35. Library scenes record each labeled section bbox, label bbox, shelf row
    bboxes, book ids, book color, book orientation, and book bbox. Library
    tasks use book bboxes as evidence because the answer unit is an individual
    shelf book. Section label bboxes and font trace are metadata, not public
    evidence for the section-book count task.
36. Park/playground scenes record each person bbox, symbolic activity id, and
    semantic zone id. The activity pose and any supporting object such as a
    bench or ball are drawn from the same person record. Park person tasks use
    person bboxes as evidence because the answer unit is a person.
37. Park/playground scenes also record semantic playground-equipment decor
    records for slides, swing sets, seesaws, and climbing frames. Equipment
    count tasks use the equipment decor bbox because the answer unit is the
    equipment item, not a person or support object.
38. Transit-terminal scenes record each boarding area bbox, sign bbox,
   platform bbox, person bbox, semantic person area id, setting id, layout id,
    and non-query decor bboxes. Transit person-count tasks use person bboxes
    as evidence because the answer unit is a person.

## Task Contracts

### `task_illustrations__environment__feature_relation_count`
1. The task records query ids `feature_side_object_count`,
   `on_feature_object_count`, and `crossing_feature_count`.
2. It renders `environment` and asks for counts relative to a
   road or river: foreground objects above/below the feature, foreground objects
   on/in the feature, or bridge/crosswalk features crossing it.
3. Answer contract:
   - `answer_gt.type = integer`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - one box per counted foreground object or crossing feature in final image
     pixel coordinates
5. The answer and evidence are projected from object placement/feature relation
   metadata and rendered bboxes, not pixels.
6. Environment scene prompt variants name the outdoor setting only; task/query
   variants name the counted relation or lit-window target.

### Other environment-count tasks
1. `task_illustrations__environment__lit_window_count` counts lit windows in
   city/skyline buildings. The renderer samples the lit-window answer in
   `1..10`; dark windows remain visible distractors. Evidence is one bbox per
   counted lit window.

### Indoor-room tasks
1. `task_illustrations__indoor_room__surface_object_count` counts objects
   of one named type on one named surface. Distractors include the same object
   type elsewhere and other object types on the queried surface.
2. `task_illustrations__indoor_room__furniture_side_count` counts objects of one
   named type left/right/above/below a named furniture item: table, sofa, or
   cabinet. Distractors include the same object type on another side and other
   object types on the queried side. The configured answer support is `1..6`,
   with task-local sampling decoupled across answer, furniture/relation, object
   type, object count, and room theme.
3. The configured indoor task object support uses `27` recognizable household,
   tabletop, toy, tool, plant, and decor objects; it excludes oversized or
   awkward surface-query objects such as guitars.
4. All indoor answers are constructed by semantic placement metadata and all
   evidence boxes are final image pixel bboxes for the counted objects.
5. Indoor-room scenes do not render text, so the role-aware font rule does not
   apply. Scene prompts name the room setting directly, while task/query prompt
   layers name the counted object, surface, furniture, or relation.

### Library tasks
1. `task_illustrations__library__section_book_count` counts books in one
   labeled shelf section. Query ids count all books, books with a
   queried canonical color, upright books, or horizontal books. Prompt color
   names include hex codes. Evidence is one bbox per counted book; keyed
   evidence is not needed because the witnesses are an unordered homogeneous
   set of counted books.
2. Library scenes include people, reading tables, plants, lamps, and desk-book
   decor as distractors, but those decor records are not counted for section
   book tasks.

### Park/playground tasks
1. `task_illustrations__park_playground__person_count` counts people by internal
   `query_id`. Query ids cover activity, semantic zone, and equipment use:
   `sitting_person_count`, `walking_person_count`, `standing_person_count`,
   `playing_ball_person_count`, `playground_area_person_count`,
   `picnic_area_person_count`, `garden_area_person_count`,
   `person_using_slide_count`, `person_using_swing_set_count`, and
   `person_using_seesaw_count`.
2. `task_illustrations__park_playground__playground_equipment_count` counts named
   equipment items. Query ids are `slide_count`,
   `swing_set_count`, `seesaw_count`, and `climbing_frame_count`.
3. Each person has exactly one activity id in the render trace. The renderer
   uses fixed symbolic pose templates so sitting, walking, standing, and
   playing with a ball remain visually distinct.
4. Evidence is one final-image pixel bbox per counted entity. Park person
   queries use person bboxes; equipment count queries use equipment decor
   bboxes. Balls, benches, trees, paths, and unqueried park zones are
   decor/support entities and are not counted as evidence for these tasks.

### Transit-terminal tasks
1. `task_illustrations__transit_terminal__entity_location_count` counts
   terminal entities by internal `query_id`. Query ids cover the reasoning
   pattern: people in a named boarding area, suitcases/backpacks/luggage carts
   in a named boarding area, and people standing in a named terminal queue.
   The specific boarding area, luggage type, and service point are sampled
   parameters rather than separate query ids.
2. The transit scene samples rail-station, bus-terminal, and airport-concourse
   visual settings plus multiple boarding-area layouts. The semantic area id is
   assigned by the task sampler and preserved in each rendered person record.
   Current sampling uses `14..22` people with queried area counts `2..8`.
3. Evidence is one final-image pixel bbox per counted entity. Person queries use
   person bboxes; luggage tasks use standalone luggage bboxes. Vehicles, signs,
   clocks, info kiosks, benches, queue ropes, and boarding-area surfaces are
   decor/support entities unless a task explicitly targets them. Transit raw
   count and location diagnostics stay in trace metadata; public complexity
   components use normalized numeric scan/load/clutter values.

### Construction-site tasks
1. `task_illustrations__construction_site__worker_attribute_count` counts workers with a
   queried hard-hat color, safety-vest color, or visible hand tool. Evidence is
   one worker bbox per counted worker. Color-query prompts include color names
   with hex codes.
2. `task_illustrations__construction_site__equipment_zone_count` counts construction
   vehicles or equipment items in one labeled site zone. Evidence is one
   equipment bbox per counted item.
3. Construction-site tasks construct target and distractor records explicitly;
   answers are checked against rendered worker/material/equipment records after
   rendering. Zone bbox jitter, object placement, and counted evidence are all
   resolved before projected evidence is emitted.

### `task_illustrations__object_field__visible_part_count`
1. `task_illustrations__object_field__visible_part_count` records
   `query_id=visible_part_count`.
2. The prompt asks for the count of one visible part kind from the configured
   support: doors, eyes, handles, tails, or wings. Current scenes use `6..9`
   objects and answer support `1..6`.
3. Answer contract:
   - `answer_gt.type = integer`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - one box per visible queried part in final image pixel coordinates
5. The answer and evidence are projected from the same rendered part records;
   no pixel-based inference is used by the verifier.

### Shared visual tasks
1. `task_illustrations__difference_pair__object_difference_count` shows Scene A/B panels
   and counts object-level changes. Query ids are
   `added_object_count`, `removed_object_count`, `changed_color_object_count`,
   and `moved_object_count`. Evidence is one bbox per changed object, using
   Scene B boxes except for removed objects, which use Scene A boxes. Moved
   objects must clear the configured minimum center displacement, and the
   sampled Scene A/B panel-label font is recorded in render metadata.
2. `task_illustrations__image_cutout_board__jigsaw_piece_order` shows either a 1x3 board
   with the left source piece anchored or a 2x2 board with the top-left source
   piece anchored. The remaining labeled pieces are shuffled below the board.
   The answer is a space-separated label string in the prompted empty-cell
   order. Evidence is a `bbox_sequence` over the displayed piece options in
   answer order. Default sampling gives the two board shapes equal weight.
   The 2x2 option row avoids the already-correct display order, and board
   style plus option-label font are recorded in render metadata.
3. `task_illustrations__image_cutout_board__rotated_tile_label` shows a full illustration cut
   into a labeled 3x3 grid, with exactly one tile rotated in place. The answer
   is the rotated tile label, and evidence is the full rotated tile bbox.
   Grid style and tile-label font are recorded in render metadata.
4. `task_illustrations__missing_patch__missing_patch_label` shows a source image with a
   blacked-out missing region and labeled patch options. Query ids
   use plain rectangular patches, rotation/reflection-allowed patches, and an
   axis-aligned rectangular cutout. Evidence is a `keyed_bbox_map` with
   `missing_region` and `selected_option` boxes. The default option count is
   six so option-letter answer support clears review diversity gates, while
   explicit four-option renders remain supported. Frame style and label font
   are recorded in render metadata.
5. `task_illustrations__scene_options__odd_scene_label` shows six labeled illustration
   panels from one source query. Five panels share the same count for a named
   target, and one panel has a different count. The answer is the odd panel
   label, and evidence is the full odd panel image bbox, not just its label
   badge. Option frame style and one consistent global-pool option-label font
   are recorded in render metadata.
6. These tasks intentionally test image comparison/reconstruction rather than
   scene-specific world knowledge. Source images for jigsaw and missing-patch
   tasks are sampled from current illustration renderers to keep
   visual variety high while preserving a synthetic-only pipeline.

### Counterfactual object tasks
1. `task_illustrations__single_object_figure__visible_part_count` renders one large
   stylized object in scene `single_object_figure`. Query ids ask for visible
   legs on a bird or quadruped, visible wings on an
   airplane or butterfly, visible bicycle wheels, visible traffic-light lenses,
   visible clover leaves, star points, glove fingers, fork tines, snowflake
   arms, or chair legs. The rendered visible count may differ from the familiar
   canonical count; evidence is one bbox per counted visible part. Neutral
   background style, object placement, object style, and object colors are
   sampled as render-only variation and recorded in trace metadata.
2. `task_illustrations__source_scene_edit__object_count_after_edit` renders one
   current source illustration scene in scene `source_scene_edit`.
   Query ids ask for the resulting target-object count after `K=1..3`
   objects are hypothetically added or removed. Evidence is the bbox set of all
   currently visible target objects before the hypothetical edit. Prompt JSON
   examples are generated from the active add/remove operation and sampled
   `K` so their arithmetic stays valid for each rendered instance.

### Other mixed-object tasks
1. `task_illustrations__object_field__object_type_count` counts objects of one named object
   type. The named type is sampled from renderer object ids with prompt-facing
   display names. Default sampling uses `11..20` total objects and
   target counts over `1..10`; the target-count cycle is independent of the
   object-type cycle so exact 100-row review samples cover the full answer
   support.
2. `task_illustrations__object_field__named_object_side_count` counts objects
   left/right/above/below the only instance of a named object type. The
   reference object type is unique by construction; evidence is one bbox per
   counted object.

## Expansion direction
The shared object library is intended to support roughly 20 tasks over time:
type counts, attribute counts, part-presence counts, spatial anchor counts,
nearest/farthest object labels, occlusion-visible counts, paired-panel changes,
and single-object marked/missing-part tasks.

Environment-scene tasks should prefer questions grounded by the renderer's
semantic feature metadata, such as object counts above/below a curved river,
objects on roads/rivers, bridge/crosswalk counts, or building-window counts.
