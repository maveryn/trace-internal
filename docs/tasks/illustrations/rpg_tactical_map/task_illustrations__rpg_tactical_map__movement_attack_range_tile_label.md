# `task_illustrations__rpg_tactical_map__movement_attack_range_tile_label`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_tactical_map`
- Implementation scene package: `rpg_tactical_map`
- Implementation source: `trace/tasks/illustrations/rpg_tactical_map/movement_attack_range_tile_label.py`

## Task Contract
Selects the single lettered terrain tile that the blue unit can attack after first moving within a visible movement-point budget on a top-down tactical RPG map.

## Program Contract
`select(tile, exists move_tile where reachable_by_movement_budget(unit, move_tile, movement_budget, terrain_costs) and cardinal_distance(move_tile, tile) in 1..attack_range); scene=rpg_tactical_map; scope=movement_attack_range_tile_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select(tile, exists move_tile where reachable_by_movement_budget(unit, move_tile, movement_budget, terrain_costs) and cardinal_distance(move_tile, tile) in 1..attack_range); scene=rpg_tactical_map; scope=movement_attack_range_tile_label` |

## Program Metadata
- Program signatures: `select.attackable_tile_after_movement`
- Base program contract: `select(tile, exists move_tile where reachable_by_movement_budget(unit, move_tile, movement_budget, terrain_costs) and cardinal_distance(move_tile, tile) in 1..attack_range); scene=rpg_tactical_map; scope=movement_attack_range_tile_label`
- Parameter axes: `movement_budget`, `attack_range`, `candidate_tile_set`, `terrain_layout`, `water_feature_style`, `canvas_profile`
- Arguments:
  - `unit`: blue_unit; the single reference unit visible in the scene; source `scene_ir.units`
  - `move_tile`: terrain_tile; any tile reachable by the blue unit before attacking; source `execution_trace.reachable_move_tile_ids`
  - `tile`: candidate_tile; visible lettered terrain tile; source `render_map.candidate_tile_ids_by_label`
  - `movement_budget`: integer; allowed `3|4|5`; source `query_spec.params.movement_budget`
  - `attack_range`: integer; allowed `1|2`; source `query_spec.params.attack_range`
  - `terrain_costs`: mapping; `grass=1`, `road=1`, `bridge=1`, `forest=2`, `mountain=3`, `water=blocked`; source `scene_ir.relations.terrain_movement_costs`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer is the letter of the only candidate tile attackable after the blue unit moves.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation contains one pixel bounding box around the selected attackable terrain tile.
- Annotation excludes the letter badge, the blue unit, non-selected candidate tiles, reachable movement tiles, and attack-source tiles.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_tactical_map/illustrations_rpg_tactical_map_v0.json`.
- Public prompts must state the movement budget, terrain movement costs, that movement is orthogonal, that attack range is horizontal or vertical only, and that attack range ignores terrain cost.
- The task has no semantic query branch beyond `single`; sampled map layout, water feature style, movement budget, attack range, tile labels, terrain colors, and canvas profile are trace metadata, not public query ids.
- Candidate tile ids, selected tile id, movement costs, reachable movement tile ids, attackable tile ids, attack-source tile ids, movement budget, attack range, selected label, and scalar bbox annotation must be recorded in the trace.
- Candidate selection should avoid making the selected tile consistently identifiable as the nearest lettered tile to the blue unit by raw Manhattan distance. Trace metadata must include `candidate_start_manhattan_by_label`, nearest-candidate labels, and whether the selected label is the unique nearest candidate.
