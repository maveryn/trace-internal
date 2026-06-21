# `task_illustrations__rpg_dungeon__reachable_chest_count`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_dungeon`
- Implementation scene package: `rpg_dungeon`
- Implementation source: `trace/tasks/illustrations/rpg_dungeon/reachable_chest_count.py`

## Task Contract
Counts the treasure chests reachable from the player by following only unblocked dungeon floor and corridor tiles.

## Program Contract
`count(chest, reachable(chest_tile, player_tile, passable_tile=open_floor) and chest.object_type=treasure_chest); scene=rpg_dungeon; scope=reachable_chest_count`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `count(chest, reachable(chest_tile, player_tile, passable_tile=open_floor) and chest.object_type=treasure_chest); scene=rpg_dungeon; scope=reachable_chest_count` |

## Program Metadata
- Program signatures: `count.reachable_graph_objects`
- Base program contract: `count(chest, reachable(chest_tile, player_tile, passable_tile=open_floor) and chest.object_type=treasure_chest); scene=rpg_dungeon; scope=reachable_chest_count`
- Parameter axes: `player_tile`, `reachable_chest_count`, `blocked_tiles`
- Arguments:
  - `chest`: treasure_chest; allowed visible generated treasure chests; source `scene_ir.entities`
  - `player_tile`: tile coordinate containing the visible player; source `scene_ir.entities`
  - `passable_tile`: floor tile not occupied by a blocker; allowed open floor and corridors; source `program_schema_concrete`
  - `reachable_chest_count`: integer; allowed `0|1|2|3|4|5`; source `parameter_axes`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer is the number of visible treasure chests reachable from the player without crossing sealed doors, rubble, or wall/background tiles.

## Annotation Contract
- Annotation schema: `point_set_map`
- Generator `annotation_gt.type`: `point_set_map`
- Annotation key `player` contains one point on the visible player marker.
- Annotation key `reachable_chests` contains one point on each counted reachable treasure chest and is empty when the answer is zero.
- Annotation excludes unreachable chests, blockers, walls, background stone, and decorative fixtures.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_dungeon/illustrations_rpg_dungeon_v0.json`.
- Public prompts refer to the player and require following only unblocked/open floor paths.
- Render-only attributes such as palette, chamber positions, decorative crystals/torches, blocker type, and canvas profile must not be query ids.
- Floor tiles, blocked tiles, player entity, all chest entities, reachable chest ids, projected keyed point-set annotation, and diagnostic blocker/entity bboxes must be recorded in the trace.
