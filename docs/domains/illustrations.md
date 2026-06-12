# Illustrations Task Setup

## Purpose
Capture the active contract for the `illustrations` domain.

Illustrations covers synthetic drawings of recognizable objects. The domain is
for object recognition, visible-part counting, and spatial reasoning over
drawn objects. It does not use natural images, external object detectors, or
free-form captions.

## Active families
1. Current active task ids and scene counts are generated in
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
1. `environment` renders curved roads, curved rivers, bridges,
   crosswalks, city skylines, and mixed foreground objects.
2. `indoor_room` renders room backgrounds with semantic furniture,
   surfaces, containers, and small household/tool/plant/fruit objects.
3. `library` renders a synthetic library with labeled shelf sections,
   visible book spines/covers, reading tables, people, plants, desk books, and
   other non-query decor. Library tasks count only semantic book records
   assigned to labeled sections; desk books and people are visual distractors.
   Section labels sample one font from the role-appropriate shared font pool per scene
   and use it consistently across all shelf-section labels.
4. `park_playground` renders a synthetic park/playground with curved
   walking paths, playground equipment, picnic/pond/garden zones, benches,
   trees, flowers, lamps, and activity-labeled people.
5. `transit_terminal` renders a synthetic transit terminal with labeled
   boarding areas, train/bus/airport visual settings, vehicles or gates,
   departure boards, clocks, info kiosks, benches, service counters, queue ropes,
   loose luggage, luggage carts, and people assigned to semantic boarding
   areas or queues.
6. `construction_site` renders a synthetic construction site with
   labeled excavation/loading/roadwork zones, workers, material stacks,
   construction vehicles/equipment, scaffold/crane/roadwork decor, and varied
   site layouts/styles. Construction zone labels sample one font from the
   role-appropriate shared font pool per scene and use it consistently across all zone
   labels; the resolved font trace is recorded in render metadata.
7. Shared visual task scenes render derived canvases from illustration sources:
   `image_cutout_board` supports jigsaw-style image reconstruction layouts
   including 1x3 and 2x2 anchored-piece boards and a 3x3 rotated-tile grid, and
   `missing_patch` shows a source image with a missing
   region plus labeled patch options. These tasks may draw their source image
   from current illustration scene renderers but ask scene-agnostic visual
   comparison or reconstruction questions.
   For `image_cutout_board` and `missing_patch`, the sampled source scene is
   `content_source` metadata rather than the public scene identity. This is
   allowed only because the task programs are visual reconstruction or patch
   matching over the derived scaffold; they do not ask for source-scene
   semantic counts or source-specific verifier logic. Current source support is
   restricted to retained richer scenes (`library`, `park_playground`, and
   `construction_site`) until additional scenes are reviewed for source-image
   quality and semantic independence.
8. Public object taxonomy is global across illustration scenes. Scene
   interfaces should request object/background types plus attributes; scenes
   own grammar, placement constraints, and allowed object subsets, not drawing
   implementations or private object naming conventions.
9. Object/background drawing and object metadata are separated:
   - `object_catalog.py` is the single source for drawable object, fixture,
     region, and background vocabularies, including render layer, size class,
     placement tags, scene tags, renderer id, public names, labels, and variant
     ids. Use its tag, scene, layer, and size-class query helpers instead of
     re-declaring object pools in scene code.
   - `object_variants.py` defines shared object-variant identities and
     renderer-specific profiles for `vector`, `top_down_pixel_rpg`, and
     `isometric_pixel_rpg` treatments. Current shared variant families are
     `tree` (`oak`, `pine`, `maple`, `fruit_tree`) and `person` (`adult`,
     `farmer`, `worker`, `vendor`, `soldier`). These are render-only visual
     attributes until a task review explicitly promotes one variant family to
     a semantic prompt/verifier contract.
   - `object_rendering.py` is the renderer-neutral dispatch layer for reusable
     illustration objects. Scene renderers pass `IllustrationObjectSpec`
     records into a renderer-specific `RenderContext`; the dispatcher draws the
     object through the selected treatment (`vector`, `top_down_pixel_rpg`, or
     `isometric_pixel_rpg`) and returns the normalized `object_record`.
     The shared pixel-RPG object set covers portable village/farm/interior/cave
     objects: people, trees/plants, domestic animals, farm fixtures,
     fences/gates, village props, shop fixtures/containers, landmarks, simple
     front-facing structures, cave entrances, boulders, ore/crystal resources,
     stalagmites, torches, ladders, mine carts, rail tracks, wood supports,
     stairs, and initial inn/tavern furniture and tableware. Isometric pixel rendering uses native
     small iso solids for hay bales, crates, troughs, shop counters, shelves,
     produce bins, rugs, chests, tavern tables, chairs, stools, beds,
     fireplaces, and room dividers, plus anchored sprites for the broader
     top-down RPG object inventory until a scene promotes a more specialized
     native iso treatment.
     `renderer_id` and `renderer_variant_id` select renderer-native treatments
     when a shared object needs scene-specific pose or equipment handling.
     Vector scenes also use this layer to build record-only `object_record`
     payloads for scene-specific fixtures, regions, and custom-drawn objects so
     renderer metadata and semantic attributes stay consistent.
   - `object_library.py` owns reusable glyph drawing and visible-part records
     for shared synthetic objects. `vector_object_renderers.py` owns registered
     vector renderer-id routing for reusable scene-native families, including
     fixture benches, transit luggage, indoor furniture/surfaces/containers,
     park/playground equipment, construction materials/equipment, and delegated
     person-like renderers.
     `vector_person_rendering.py` owns shared vector person silhouettes, poses,
     support items, and visible-part records for generic people, park people,
     transit people, and construction workers.
     `person_rendering.py` owns lower-level person-appearance helpers such as
     hair and skirt shapes used by those vector renderers.
   - `object_schema.py` defines the normalized `object_record` payload.
   - `object_registry.py` adapts catalog-backed public object type definitions
     into the normalized `object_record` contract, including families,
     semantic/visual attribute slots, render layer, size class, and placement
     tags.
   - `scene_objects.py` extracts normalized object records from mixed
     scene-specific entity payloads for downstream scene-agnostic tasks.
   - `*_rendering.py` modules own PIL drawing for scene backgrounds, fixtures,
     and scene-specific object renderers; reusable object families should route
     through `object_rendering.py` instead of duplicating tree/person/animal,
     person-pose, bench, luggage, indoor-fixture, park-equipment, or
     construction-object rendering inside each scene. Scene-specific entities
     that keep local drawing should still build their normalized records through
     `object_rendering.py` rather than calling the registry directly.
   - `*_scene.py` modules are drawing-free public interfaces. Architecture
     tests enforce that they do not import PIL, create images/draw contexts, or
     define local `_draw_*` helpers.
10. Each object-capable entity should include an `object_record` with:
   - `object_id`, public `object_type`, `public_name`, `family`, and bbox,
   - `semantic_attributes` used by tasks/verifiers, such as activity, zone,
     material type, or queried color name,
   - `visual_attributes` used only for rendering variation, such as RGB fills,
     style id, `object_variant_id`, renderer-native variant ids, and person
     `gender_id`,
   - `role`, `source_entity_type`, and optional visible part records.
11. Existing scene-specific entity fields remain available for compatibility,
   but new cross-scene visual tasks should consume `object_record` or
   `extract_scene_object_records(...)` instead of branching on every scene.
12. Person-like entities use public categories such as `person`,
   `pedestrian_with_bag`, or `worker`. They sample render-only
   `gender_id` from `male`/`female` with equal probability where supported and
   may record render-only `person_variant_id` values from the shared object
   variant registry. No task prompt or verifier should ask a gender- or
   person-variant-specific question until that variant family is reviewed as a
   semantic objective. There is no supported `child` person renderer variant;
   `childrens_corner` remains only a library background setting.
13. Current renderer-native illustration art styles are `flat_vector`,
   `outlined_cartoon`, `paper_cutout`, `soft_shadow`, `ink_sketch`,
   `watercolor_wash`, and `blueprint_line`. The canonical registry is
   `trace/tasks/illustrations/shared/style_registry.py`. Scene/task configs use
   safe allowlists, so not every style is enabled for every scene by default.
   Shadow and grounding policy is renderer-specific:
   - Vector illustration objects may use decorative shadows only when the
     selected art style enables them. These shadows are visual style only,
     recorded in object `visual_attributes`, and are never semantic annotation.
   - Top-down pixel RPG objects must not add generic cast/drop shadows.
   - Isometric pixel RPG objects use projection and height for grounding, not
     generic cast/drop shadows.
   - Object annotation and object bboxes must mark the object or queried part
     itself, not any decorative shadow or renderer-local texture/shading pixels.
14. The shared foreground object library currently contains 65 reusable
   illustration-native object types. It includes common scene objects plus a
   small set borrowed from the named-icon vocabulary as native illustration
   drawings: backpack, bucket, camera, gift, guitar, kite, lightbulb, mailbox,
   shovel, soccer ball, teapot, and train.
15. `trace/tasks/illustrations/shared/pixel_village_rendering.py` is an
   experimental procedural old-school pixel RPG village renderer. It uses
   Kenney Tiny Town, Roguelike/RPG, RPG Urban Pack, graveyard-style pixel
   packs, and the Diogo Vernier RPG House Tileset as visual references only;
   it does not load
   external sprites. Generated inspection assets live under
   `review/task-reviews/assets/illustrations/pixel_village_map/`. The renderer
   is semantic from the start: buildings, landmarks, people, plants, barriers,
   path features, path tiles, water tiles, and optional territories are
   recorded in trace metadata. It samples per-instance grid dimensions and
   renders logical map tiles at `32px` by default on the final review canvas.
   The renderer also exposes an opt-in `path_person_count` parameter for
   tasks that need people placed directly on path tiles; the default remains
   `0`, so resource previews and non-path tasks keep ordinary village
   placement.
   Pixel-village people record
   render-only appearance metadata such as `gender_id`, `person_variant_id`,
   facing direction, clothes colors, skin color, and hair color; future prompts
   should not ask gender- or person-variant-specific questions.
   Pixel-village buildings stay front-facing to
   match top-down RPG map conventions; regular houses, shops, and inns use
   `4x3` footprints, tower uses `3x4`, church uses `4x4`, and castle uses
   `5x4`. Regular village buildings sample render-only
   `building_roof_style` values `shingle`, `wood_plank`, and `tile`, plus
   `building_wall_style` values `stucco`, `wood`, and `stone`. All village
   house-like structures, including inn, shop, tower, church, and castle,
   record render-only `building_door_state` values `open` or `closed`. Future
   prompts should not ask building style or door-state questions until this
   variation is explicitly reviewed as a semantic objective. Pixel-village
   trees use reusable pixel-world object templates backed by the shared
   variant registry with render-only `tree_style` values `oak`, `pine`,
   `maple`, and `fruit_tree`; the public object name remains `tree` unless a
   future review explicitly accepts style-specific questions. Pixel-village also includes
   reusable castle, church, windmill, round well, market stall, wagon, statue,
   gazebo, woodpile, variable-size/shape pond, barrel, bench, lamp post,
   notice board, cart, and single-tile flower/plant templates for future
   RPG-like scene compositions. Windmill is an optional village landmark with
   a `3x4` footprint and render-only blade pose/color metadata; it is not a
   house-like building and does not use door-state metadata. Large village
   props and landmarks reserve clear map footprints; pond records render-only
   `pond_shape`, water color, rim color, and tile footprint metadata. Small
   village props are placed near paths or other clear village space and record
   render-only appearance metadata such as orientation, facing, and palette.
   Future prompts should initially ask about stable public object names and
   regions, not prop color/orientation/facing, until those attributes are
   explicitly reviewed as semantic objectives. Dirt path tiles are rendered
   from road-neighbor connectivity so horizontal, vertical, corner,
   T-junction, and crossing pieces use appropriate edge strokes. Cemetery is
   an optional
   village `territory`, not a separate public scene; when present it records a
   boundary `gate_tile`, connector path tiles, iron-fence count, grave-marker
   count, and grave-marker entities with render-only `marker_style` values
   `rounded`, `tablet`, `cross`, and `obelisk`. Future tasks should initially
   query large landmarks/buildings/path features rather than tiny incidental
   entities. Orchard is also an optional village `territory` backed by the
   reusable helpers in `pixel_territory_rendering.py`; it samples variable
   territory dimensions, a low hedge/post boundary, a gate, connector path
   tiles, and rows of fruit-tree entities. Orchard tree entities keep public
   name `tree`, record `territory_id="orchard_0"`, and expose render-only
   row/column indices plus leaf/fruit colors for future territory-count tasks.
   Farm plots are intentionally not part of the village scene; farm crops,
   vegetable patches, hay bales, scarecrows, and farm gates belong in dedicated
   farm scenes where their visual grammar can be reviewed separately. Village
   tree, flower, person, bench, lamp-post, market-stall, wagon, gazebo, and
   pond entities are also exposed through shared `object_record` payloads.
   The
   broader portable village object inventory can be requested from the shared
   object renderer in both top-down and isometric pixel RPG styles for future
   isometric scenes.
   Pixel-village supports render-only `theme_mode` values `temperate`,
   `autumn`, `winter`, and `auto`; default generation remains temperate.
   Autumn uses restrained warm terrain, muted vegetation/crop colors, and
   subtle fallen-leaf metadata such as `autumn_intensity`, `leaf_coverage`,
   and `leaf_style`. Winter samples `snow_intensity` and per-covered-entity
   snow metadata such as `snow_coverage` and `snow_style`. These theme
   attributes are visual variation only. Prompts and verifiers must not ask
   season, autumn/winter, leaf, snow, or snow-amount questions unless those
   attributes are later promoted through a separate reviewed semantic task.
16. `trace/tasks/illustrations/shared/pixel_farm_rendering.py` is an
   experimental procedural old-school pixel RPG farm renderer. It uses Kenney
   and OpenGameArt farm-animal packs as visual references only; it does not
   load external sprites. Generated inspection assets live under
   `review/task-reviews/assets/illustrations/pixel_farm_map/`, and reusable
   pixel-world object sheets live under
   `review/task-reviews/assets/illustrations/pixel_world_objects/`. The farm
   renderer records fenced pen regions, each pen's `gate_tile`, plus each
   domestic animal's `region_id` and `inside_pen` metadata for future
   region-count tasks. Barn and chicken-coop building fixtures record
   render-only `building_door_state` values `open` or `closed`. The approved
   domestic animal set is chicken, pig, sheep, and cow; duck is intentionally
   excluded for now because the current farm scene only targets land animals.
   Chicken, pig, and sheep use 1x1 tile footprints; cow uses a 2x1 footprint
   so it reads larger than humans and smaller animals. Farm animals, trees, and
   flowers are rendered through shared `object_rendering.py` specs and expose
   normalized `object_record` payloads. Barns, coops, hay bales, troughs, and
   other portable farm fixtures also have shared top-down/isometric pixel RPG
   renderer support for reuse by future farm or village scenes. The same
   resource-sheet generator also inventories cave/mine shared objects for
   future cave, mine, mountain, dungeon, ruins, or temple scenes. These
   cave/mine/dungeon sprites are procedural 16px tile drawings; Kenney Tiny
   Dungeon, Kenney Micro Roguelike, OpenGameArt 16x16 RPG Tileset,
   OpenGameArt Cave Tileset, and 16x16 Puny Dungeon Tileset are recorded as
   visual references only, with no copied sprite pixels. Shared dungeon object
   support includes stone columns, archways, sealed doors, floor switches,
   braziers, broken walls, rubble, and magic circles in both top-down and
   isometric pixel RPG renderer styles. Their switch/door/flame/crack/glow
   attributes are render-only until a separate reviewed task promotes any of
   them to semantic query variables. This renderer is not an active public
   scene/task yet.
17. `trace/tasks/illustrations/shared/pixel_isometric_farmstead_rendering.py`
   is an experimental procedural isometric pixel RPG farmstead renderer. It
   uses a 2:1 isometric projection with explicit lower/upper levels, one- or
   two-unit elevation depth, retaining-wall faces, ramp/stair transitions,
   region polygons, projected footprints, and semantic farm entities. It
   reuses the shared pixel-world trees, animals, flowers, people, and farm
   fixtures through `object_rendering.py`, recording shared `object_variant_id`,
   `tree_style`, and `person_variant_id` metadata as render-only attributes.
   Isometric farm animals, people, trees, flowers, hay bales, crates, and
   troughs are rendered through shared specs and expose normalized
   `object_record` payloads. This renderer is not an active public scene/task
   yet.
18. `trace/tasks/illustrations/shared/pixel_rpg_interior_rendering.py` contains
   the first experimental procedural old-school RPG interior renderer:
   `pixel_rpg_general_store`. It samples one logical general-store layout and
   can render it as either top-down pixel RPG or explicit isometric pixel RPG.
   The renderer uses Kenney Roguelike/RPG and RPG Urban Pack assets as visual
   references only; it does not load external sprites. Generated inspection
   assets live under
   `review/task-reviews/assets/illustrations/pixel_rpg_general_store/`.
   The general-store layout records semantic zones for entrance, counter,
   walls, center aisle, and storage corner, plus normalized object records for
   counter, vendor, shelves, produce bin, crates/barrels, jars/pots/baskets,
   sacks, rug, chest, and notice board. Required shop fixtures and props route
   through `object_rendering.py` in both projections. Shelf `goods_type`,
   produce-bin `goods_type`, theme, floor pattern, colors, and person
   appearance are render-only attributes until separately reviewed as semantic
   task objectives. The shared object renderer also exposes render-only
   inn/tavern support for tables, chairs, stools, beds, fireplaces, room
   dividers, plates, and candles; these are previewable
   object assets only until a dedicated interior scene/task review accepts
   their layout and semantics. This renderer is not an active public scene/task
   yet.
19. Current environment themes are `park_road`, `river_meadow`, `road_and_river`,
    `canal_city`, and `skyline_street`.
20. Current indoor themes are `living_room`, `kitchen`, `study`, and `bedroom`.
21. Current library settings are `reading_room`, `archive_room`, and
    `childrens_corner`.
22. Current park settings are `playground_lawn`, `picnic_park`,
    `pond_playground`, and `flower_garden`.
23. Current transit-terminal settings are `rail_station`, `bus_terminal`, and
    `airport_concourse`.
24. Current construction-site settings are `urban_build`, `roadwork`,
    `foundation_yard`, and `scaffold_site`.
25. Object placement should be habitat-aware rather than uniformly random:
   airplanes, birds, butterflies, and kites use sky bands; cars/buses/trucks/
   bicycles plus taxis/vans/scooters use roads when a road scene is present;
   boats, sailboats, fish, ducks, buoys, and lily pads use rivers when
   a river scene is present; people, plants, animals, and household/tool/
   scene-fixture objects use land or surface bands. Land-object pools are
   theme-specific so city scenes favor pedestrians and street fixtures, while
   park/meadow scenes favor people, animals, plants, benches, small outdoor
   objects, cameras, backpacks, and sports/tool props.
   City/canal themes may cap foreground object count slightly below the global
   request to keep crowded skyline scenes legible.
26. Environment features are semantic entities:
   - roads and rivers store curved path points, width, bbox, and nearest-point
     geometry support plus a sampled large-feature style id,
   - bridges and crosswalks store bboxes and crossing relationships,
   - buildings store building bboxes, roof type, door bbox, window bboxes, and
     lit-window bboxes; each building also records a sampled building style id.
27. Clouds and sun are non-counted sky decor features in environment scenes;
    they enrich backgrounds but do not enter foreground-object count tasks.
28. Benches, road signs, streetlamps, traffic lights, mailboxes, trash bins,
    and similar scene fixtures are foreground objects when placed through the
    object library, so they are eligible for object-level count tasks.
29. Object placements in environment scenes record the sampled zone and
    precomputed relation metadata to roads/rivers, including above/below/on
    relation, signed vertical distance, nearest distance, nearest point, and
    whether the object lies between the road and river when both are present.
30. Task generators may request exact road/river placement counts from the
    renderer when a count target must be balanced by construction; the renderer
    still owns final object positions and bboxes.
31. Indoor-room placements record whether each object is on a named surface,
    inside a named container, or in a side region relative to named furniture.
    Furniture, surface, and container bboxes are exported in the render map.
32. Indoor surfaces are rendered as 2.5D perspective planes: table, shelf, and
    counter tops use trapezoid support geometry, surface objects record a
    pixel-space contact point and depth value, and annotation remains the final
    tight rendered object bbox.
33. Indoor-room furniture, shelf/counter/table geometry, containers, rugs,
    window placement, and large-object colors are sampled per instance. Layout
    variants swap the cabinet/shelf and sofa/container sides so the room
    topology is not fixed. The renderer exports the sampled furniture,
    surface, and container bboxes plus each surface plane so task answers and
    annotation stay tied to the same geometry that is drawn.
34. Indoor-room visual style variation applies to both foreground objects and
    room structure. The room renderer samples furniture shape variants
    including table-leg, sofa, cabinet, shelf, rug-pattern, container, floor,
    window, and wall-decor styles while preserving the same semantic
    furniture/surface/container bboxes used by tasks.
35. Environment scenes sample explicit layout metadata per instance, including
    land/sky boundary, road/river base paths, path amplitudes, feature widths,
    city building horizon, background colors, and zone-bias weights. This keeps
    road/river/city scenes varied while preserving semantic path, feature, and
    object-placement metadata for verification.
36. Library scenes record each labeled section bbox, label bbox, shelf row
    bboxes, book ids, book color, book orientation, and book bbox. Library
    tasks use book bboxes as annotation because the answer unit is an individual
    shelf book. Section label bboxes and font trace are metadata, not public
    annotation for the section-book count task.
37. Park/playground scenes record each person bbox, symbolic activity id, and
    semantic zone id. The activity pose and any supporting object such as a
    bench or ball are drawn from the same person record. Park person tasks use
    person bboxes as annotation because the answer unit is a person.
38. Park/playground scenes also record semantic playground-equipment decor
    records for slides, swing sets, seesaws, and climbing frames. Equipment
    count tasks use the equipment decor bbox because the answer unit is the
    equipment item, not a person or support object.
39. Transit-terminal scenes record each boarding area bbox, sign bbox,
    platform bbox, person bbox, semantic person area id, setting id, layout id,
    and non-query decor bboxes. Transit person-count tasks use person bboxes
    as annotation because the answer unit is a person.

## Task Contracts

### Environment tasks
1. `task_illustrations__environment__feature_side_object_count` counts
   foreground objects above or below a road/river.
2. `task_illustrations__environment__on_feature_object_count` counts
   foreground objects on a road or in/on a river.
3. `task_illustrations__environment__crossing_feature_count` counts bridges
   crossing rivers or crosswalks crossing roads.
4. `task_illustrations__environment__lit_window_count` counts lit windows in
   city/skyline buildings. The renderer samples the lit-window answer in
   `1..10`; dark windows remain visible distractors.
5. Environment answers are integers. Annotation is a `bbox_set` with one
   final-image pixel box per counted foreground object, crossing feature, or
   lit building window. The answer and annotation are projected from object
   placement/feature relation metadata and rendered bboxes, not pixels.
6. Environment scene prompt variants name the outdoor setting only; task/query
   layers name the counted relation or lit-window target.


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
   annotation boxes are final image pixel bboxes for the counted objects.
5. Indoor-room scenes do not render text, so the role-aware font rule does not
   apply. Scene prompts name the room setting directly, while task/query prompt
   layers name the counted object, surface, furniture, or relation.

### Library tasks
1. `task_illustrations__library__books_in_section_count` counts all books in
   one labeled shelf section.
2. `task_illustrations__library__filtered_book_in_section_count` counts books
   in one labeled section filtered by canonical color or orientation. Query ids
   are `book_color_in_section_count`, `upright_book_in_section_count`, and
   `horizontal_book_in_section_count`. Prompt color names include hex codes.
   Annotation is one bbox per counted book; keyed annotation is not needed because
   the witnesses are an unordered homogeneous set of counted books.
3. Library scenes include people, reading tables, plants, lamps, and desk-book
   decor as distractors, but those decor records are not counted for section
   book tasks.

### Park/playground tasks
1. `task_illustrations__park_playground__activity_person_count` counts people
   by activity. Query ids are `sitting_person_count`,
   `walking_person_count`, `standing_person_count`, and
   `playing_ball_person_count`.
2. `task_illustrations__park_playground__area_person_count` counts people in
   one semantic area. Query ids are `playground_area_person_count`,
   and `garden_area_person_count`.
3. `task_illustrations__park_playground__equipment_use_person_count` counts
   people using one equipment type. Query ids are
   `person_using_slide_count`, `person_using_swing_set_count`, and
   `person_using_seesaw_count`.
4. `task_illustrations__park_playground__playground_equipment_count` counts named
   equipment items. Query ids are `slide_count`,
   `swing_set_count`, `seesaw_count`, and `climbing_frame_count`.
5. Each person has exactly one activity id in the render trace. The renderer
   uses fixed symbolic pose templates so sitting, walking, standing, and
   playing with a ball remain visually distinct.
6. Annotation is one final-image pixel bbox per counted entity. Park person
   queries use person bboxes; equipment count queries use equipment decor
   bboxes. Balls, benches, trees, paths, and unqueried park zones are
   decor/support entities and are not counted as annotation for these tasks.

### Pixel-village tasks
1. `task_illustrations__pixel_village__object_type_count` counts visible
   entities for one approved public target: `building`, `person`, `tree`,
   `lamp_post`, `well`, or `pond`. Building counts use all entities
   with category `building`; person counts use all category `person` entities;
   other targets use exact public names. The task rejects generated scenes
   where the selected target answer exceeds the configured cap, currently `8`.
   When the target is `tree`, cemetery territory is suppressed so leafless
   cemetery dead-tree decor cannot be confused with counted trees.
2. `task_illustrations__pixel_village__person_path_count` counts people whose
   tile footprint intersects a visible village path tile. The task requests
   explicit path-person placements from the renderer via `path_person_count`;
   default village renders have no guaranteed people on paths. For this task,
   non-counted background people must be kept at least one tile away from path
   tiles so adjacent off-path people are not confused with counted people.
3. `task_illustrations__pixel_village__territory_object_count` counts a target
   object type inside a semantic territory. Supported operands are cemetery
   grave markers and orchard trees. The relevant territory is forced present
   for the sampled operand.
4. `task_illustrations__pixel_village__river_side_object_count` counts visible
   `building`, `person`, or `tree` entities that lie strictly on one side of a
   forced balanced river. `left`/`right` queries use a vertical river, while
   `above`/`below` queries use a horizontal river. Side membership is computed
   from each entity's full tile footprint against the recorded river bounds;
   objects intersecting the river band are not counted.
5. Pixel-village prompts must use public nouns such as `people`, `person`,
   `building`, `tree`, `lamp post`, `well`, and `pond`. Prompts must
   not expose the internal public-name value `villager` or ask render-only
   appearance/style attributes such as gender, facing, tree style, door state,
   season, snow, leaf overlay, or vegetable type.
6. Annotation is one final-image pixel bbox per counted entity. Path tiles,
   water tiles, whole territories, and context-only regions are verifier context in
   metadata and are not annotation witnesses.
7. Pixel-village renderer density should stay moderate for task reviews.
   Landmark building variants (`tower`, `church`, `castle`) are optional; do
   not force every building type into every generated village.

### Transit-terminal tasks
1. `task_illustrations__transit_terminal__person_in_boarding_area_count`
   counts people in a named boarding area.
2. `task_illustrations__transit_terminal__luggage_in_boarding_area_count`
   counts suitcases/backpacks/luggage carts in a named boarding area.
3. `task_illustrations__transit_terminal__person_in_queue_count` counts people
   standing in a named terminal queue.
4. The specific boarding area, luggage type, and service point are sampled
   parameters rather than separate query ids.
5. The transit scene samples rail-station, bus-terminal, and airport-concourse
   visual settings plus multiple boarding-area layouts. The semantic area id is
   assigned by the task sampler and preserved in each rendered person record.
   Current sampling uses `14..22` people with queried area counts `2..8`.
6. Annotation is one final-image pixel bbox per counted entity. Person queries use
   person bboxes; luggage tasks use standalone luggage bboxes. Vehicles, signs,
   clocks, info kiosks, benches, queue ropes, and boarding-area surfaces are
   decor/support entities unless a task explicitly targets them. Transit raw
   count and location diagnostics stay in trace metadata.

### Construction-site tasks
1. `task_illustrations__construction_site__worker_attribute_count` counts workers with a
   queried hard-hat color, safety-vest color, or visible hand tool. Annotation is
   one worker bbox per counted worker. Color-query prompts include color names
   with hex codes.
2. `task_illustrations__construction_site__equipment_zone_count` counts construction
   vehicles or equipment items in one labeled site zone. Annotation is one
   equipment bbox per counted item.
3. Construction-site tasks construct target and distractor records explicitly;
   answers are checked against rendered worker/material/equipment records after
   rendering. Zone bbox jitter, object placement, and counted annotation are all
   resolved before projected annotation is emitted.

### Shared visual tasks
1. `task_illustrations__image_cutout_board__jigsaw_piece_order` shows either a 1x3 board
   with the left source piece anchored or a 2x2 board with the top-left source
   piece anchored. The remaining labeled pieces are shuffled below the board.
   The answer is a space-separated label string in the prompted empty-cell
   order. Annotation is a `bbox_sequence` over the displayed piece options in
   answer order. Default sampling gives the two board shapes equal weight.
   The 2x2 option row avoids the already-correct display order, and board
   style plus option-label font are recorded in render metadata.
2. `task_illustrations__image_cutout_board__rotated_tile_label` shows a full illustration cut
   into a labeled 3x3 grid, with exactly one tile rotated in place. The answer
   is the rotated tile label, and annotation is the full rotated tile bbox.
   Grid style and tile-label font are recorded in render metadata.
3. `task_illustrations__missing_patch__missing_patch_label` shows a source image with a
   blacked-out missing region and labeled patch options. Query ids
   use plain rectangular patches, rotation/reflection-allowed patches, and an
   axis-aligned rectangular cutout. Annotation is a `keyed_bbox_map` with
   `missing_region` and `selected_option` boxes. The default option count is
   six so option-letter answer support clears review diversity gates, while
   explicit four-option renders remain supported. Frame style and label font
   are recorded in render metadata.
4. These tasks intentionally test image comparison/reconstruction rather than
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
   canonical count; annotation is one bbox per counted visible part. Neutral
   background style, object placement, object style, and object colors are
   sampled as render-only variation and recorded in trace metadata. The single
   target object exposes a normalized `object_record` with visible part records
   attached from the same drawing trace.
2. `task_illustrations__source_scene_edit__object_count_after_edit` renders one
   current source illustration scene in scene `source_scene_edit`.
   Query ids ask for the resulting target-object count after `K=1..3`
   objects are hypothetically added or removed. Annotation is the bbox set of all
   currently visible target objects before the hypothetical edit. Prompt JSON
   examples are generated from the active add/remove operation and sampled
   `K` so their arithmetic stays valid for each rendered instance.

## Expansion direction
Future illustration expansion should add scene-grounded object tasks rather
than generic loose object fields. Candidate directions include type counts,
attribute counts, part-presence counts, spatial anchor counts,
nearest/farthest object labels, occlusion-visible counts, paired-panel changes,
and single-object marked/missing-part tasks inside richer environment,
construction, transit, indoor, park, or library scene grammars.

Environment-scene tasks should prefer questions grounded by the renderer's
semantic feature metadata, such as object counts above/below a curved river,
objects on roads/rivers, bridge/crosswalk counts, or building-window counts.
