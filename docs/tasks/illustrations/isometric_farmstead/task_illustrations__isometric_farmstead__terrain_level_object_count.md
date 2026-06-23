# `task_illustrations__isometric_farmstead__terrain_level_object_count`

## Summary
- Domain: `illustrations`
- Scene id: `isometric_farmstead`
- Implementation scene package: `isometric_farmstead`
- Implementation source: `trace/tasks/illustrations/isometric_farmstead/terrain_level_object_count.py`

## Task Contract
Counts a queried class of farm context objects whose base terrain tile is on the requested elevation extremum. Supported object classes are farm animals and trees.

## Program Contract
`count(filter(scene_entities, object_type(entity)=target_object_type and level(base_tile(entity))=extremum(level(tile), mode=highest|lowest))); scene=isometric_farmstead; scope=terrain_level_object_count`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `highest_terrain_object_count` | `count(filter(scene_entities, object_type(entity)=target_object_type and level(base_tile(entity))=max(level(tile)))); scene=isometric_farmstead; scope=terrain_level_object_count` |
| `lowest_terrain_object_count` | `count(filter(scene_entities, object_type(entity)=target_object_type and level(base_tile(entity))=min(level(tile)))); scene=isometric_farmstead; scope=terrain_level_object_count` |

## Program Metadata
- Program signatures: `count.spatial_attribute`
- Base program contract: `count(filter(scene_entities, object_type(entity)=target_object_type and level(base_tile(entity))=extremum(level(tile), mode=highest|lowest))); scene=isometric_farmstead; scope=terrain_level_object_count`
- Parameter axes: `canvas_profile`, `target_object_type=domestic_animal|tree`, `answer_count_support=0..5`, `active_level_range`, `layout_family`, `terrain_level`, `extremum_mode`
- Arguments:
  - `entity`: visible farm context object; allowed `domestic_animal|tree`; source `scene_ir.entities`
  - `base_tile`: terrain tile occupied by the entity; source `scene_ir.entities.tile_ids`
  - `level`: integer terrain elevation; allowed active subset of `0|1|2`; source `scene_ir.tiles` and `scene_ir.entities`
  - `mode`: extremum operator; allowed `highest|lowest`; source `query_id`
- Argument metadata status: `curated`
- Supported query ids: `highest_terrain_object_count`, `lowest_terrain_object_count`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer is the number of matching farm animals or trees whose base tile is on the highest or lowest active terrain level requested by the query branch.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one around each counted object. Use an empty list when the answer is `0`.
- Annotation must include only the counted objects, not terrain tiles, farm patches, retaining wall faces, labels, or uncounted context objects.
- Annotation and answer must be projected from the same generated scene trace.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/isometric_farmstead/illustrations_isometric_farmstead_v0.json`.
- Public prompts must state the queried object class and highest or lowest terrain level.
- Render-only attributes such as palette, canvas profile, active max level, layout family, connected farm patch placement, farm animal/tree subtype, tile geometry, and object sprite style must not be query ids.
- The renderer must not place any farm animal or tree on a lower-level tile adjacent to a higher-level tile, because those objects can visually read as sitting on the raised terrace.
- Target object type, target level, extremum mode, counted entity ids, counted entity bboxes, object counts by level, projection metadata, and the bbox-set annotation must be recorded in the trace.
