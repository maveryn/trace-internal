# `task_illustrations__rpg_tactical_map__movement_reachable_tile_label`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_tactical_map`
- Implementation scene package: `rpg_tactical_map`
- Implementation source: `trace/tasks/illustrations/rpg_tactical_map/movement_reachable_tile_label.py`

## Task Contract
Selects the single lettered terrain tile that the blue unit can reach within a visible movement-point budget on a top-down tactical RPG map.

## Program Contract
`select(tile, reachable_by_movement_budget(unit, tile, budget, terrain_costs)); scene=rpg_tactical_map; scope=movement_reachable_tile_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select(tile, reachable_by_movement_budget(unit, tile, budget, terrain_costs)); scene=rpg_tactical_map; scope=movement_reachable_tile_label` |

## Program Metadata
- Program signatures: `select.reachable_tile_under_movement_budget`
- Base program contract: `select(tile, reachable_by_movement_budget(unit, tile, budget, terrain_costs)); scene=rpg_tactical_map; scope=movement_reachable_tile_label`
- Parameter axes: `movement_budget`, `candidate_tile_set`, `terrain_layout`, `canvas_profile`
- Arguments:
  - `unit`: blue_unit; the single reference unit visible in the scene; source `scene_ir.units`
  - `tile`: candidate_tile; visible lettered terrain tile; source `render_map.candidate_tile_ids_by_label`
  - `budget`: integer; allowed `4|5|6`; source `query_spec.params.movement_budget`
  - `terrain_costs`: mapping; `grass=1`, `road=1`, `bridge=1`, `forest=2`, `mountain=3`, `water=blocked`; source `scene_ir.relations.terrain_movement_costs`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer is the letter of the only candidate tile reachable by the blue unit using at most the movement budget.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation contains one pixel bounding box around the selected reachable terrain tile.
- Annotation excludes the letter badge, the blue unit, non-selected candidate tiles, and path traces.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_tactical_map/illustrations_rpg_tactical_map_v0.json`.
- Public prompts must state the movement budget, orthogonal movement rule, and terrain costs, including mountain cost `3`.
- The task has no semantic query branch beyond `single`; sampled map layout, budget, tile labels, terrain colors, and canvas profile are trace metadata, not public query ids.
- Candidate tile ids, tile bboxes, label bboxes, terrain types, shortest movement costs, movement budget, selected label, selected tile id, and scalar bbox annotation must be recorded in the trace.
