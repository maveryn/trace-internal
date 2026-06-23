# `task_illustrations__isometric_farmstead__farmer_same_level_tile_label`

## Summary
- Domain: `illustrations`
- Scene id: `isometric_farmstead`
- Implementation scene package: `isometric_farmstead`
- Implementation source: `trace/tasks/illustrations/isometric_farmstead/farmer_same_level_tile_label.py`

## Task Contract
Selects the lettered terrain tile that is at the same terrain elevation level as an unlettered farmer reference object.

## Program Contract
`select(label, level(candidate_tile)=level(base_tile(reference_farmer)), candidate_tile in lettered_ground_tiles); scene=isometric_farmstead; scope=farmer_same_level_tile_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select(label, level(candidate_tile)=level(base_tile(reference_farmer)), candidate_tile in lettered_ground_tiles); scene=isometric_farmstead; scope=farmer_same_level_tile_label` |

## Program Metadata
- Program signatures: `select.spatial_elevation_relation`
- Base program contract: `select(label, level(candidate_tile)=level(base_tile(reference_farmer)), candidate_tile in lettered_ground_tiles); scene=isometric_farmstead; scope=farmer_same_level_tile_label`
- Parameter axes: `canvas_profile`, `candidate_count=4`, `candidate_tile_ids`, `reference_farmer_tile_id`, `active_level_range`, `layout_family`, `terrain_level`
- Arguments:
  - `reference_farmer`: unlettered farmer entity; source `scene_ir.entities`
  - `base_tile`: terrain tile occupied by the farmer; source `scene_ir.entities.tile_ids`
  - `candidate_tile`: visible lettered terrain tile; source `scene_ir.tiles`
  - `level`: integer terrain elevation; allowed active subset of `0|1|2`; source `scene_ir.tiles`
- Argument metadata status: `curated`
- Supported query ids: `single`
- Internal prompt/query key: `farmer_same_level_tile`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer is the letter on the unique candidate terrain tile whose elevation level matches the farmer's base terrain tile.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation contains one bounding box around the selected terrain tile, not the letter badge and not the farmer.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/isometric_farmstead/illustrations_isometric_farmstead_v0.json`.
- Public prompts must identify the farmer as an unlettered reference and ask for the same terrain level among lettered ground tiles.
- The farmer must be placed only on a safe unoccupied grass tile, never on a lower-level tile adjacent to higher terrain.
- Candidate tile levels, candidate tile ids by label, selected label, selected tile id, selected tile bbox, farmer entity id, farmer tile id, farmer level, farmer bbox, internal prompt/query key, projection metadata, and the scalar bbox annotation must be recorded in the trace.
