# `task_illustrations__isometric_farmstead__terrain_elevation_extremum_label`

## Summary
- Domain: `illustrations`
- Scene id: `isometric_farmstead`
- Implementation scene package: `isometric_farmstead`
- Implementation source: `trace/tasks/illustrations/isometric_farmstead/terrain_elevation_extremum_label.py`

## Task Contract
Selects the lettered terrain tile at the requested elevation extremum in an isometric farmstead scene.

## Program Contract
`select(label, extremum(level(tile), mode=highest|lowest), tile in lettered_ground_tiles); scene=isometric_farmstead; scope=terrain_elevation_extremum_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `highest_terrain_tile` | `select(label, max(level(tile)), tile in lettered_ground_tiles); scene=isometric_farmstead; scope=terrain_elevation_extremum_label` |
| `lowest_terrain_tile` | `select(label, min(level(tile)), tile in lettered_ground_tiles); scene=isometric_farmstead; scope=terrain_elevation_extremum_label` |

## Program Metadata
- Program signatures: `select.spatial_elevation_extremum`
- Base program contract: `select(label, extremum(level(tile), mode=highest|lowest), tile in lettered_ground_tiles); scene=isometric_farmstead; scope=terrain_elevation_extremum_label`
- Parameter axes: `canvas_profile`, `candidate_count`, `candidate_tile_ids`, `terrain_level`, `extremum_mode`
- Arguments:
  - `tile`: visible lettered terrain tile; allowed generated candidate terrain tiles not occupied by farm objects or transitions; source `scene_ir.tiles`
  - `level`: integer terrain elevation; allowed `0|1|2|3`; source `scene_ir.tiles`
  - `mode`: extremum operator; allowed `highest|lowest`; source `query_id`
- Argument metadata status: `curated`
- Supported query ids: `highest_terrain_tile`, `lowest_terrain_tile`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer is the letter on the unique candidate terrain tile whose ground level is highest or lowest as requested by the query branch.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation contains one bounding box around the selected terrain tile, not the letter badge and not any contextual farm object.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/isometric_farmstead/illustrations_isometric_farmstead_v0.json`.
- Public prompts must refer to ground or terrain tiles so object height is not confused with terrain elevation.
- Render-only attributes such as palette, canvas profile, farm object placement, tile geometry, and label font must not be query ids.
- Tile levels, candidate tile ids by label, candidate levels by label, selected label, selected tile id, selected tile bbox, projection metadata, and the scalar bbox annotation must be recorded in the trace.
