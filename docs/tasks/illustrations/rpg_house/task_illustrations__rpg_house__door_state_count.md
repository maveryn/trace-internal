# `task_illustrations__rpg_house__door_state_count`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_house`
- Implementation scene package: `rpg_house`
- Implementation source: `trace/tasks/illustrations/rpg_house/door_state_count.py`

## Task Contract
Counts visible doors in a requested state within a top-down pixel RPG house layout.

## Program Contract
`count(door, state(door, target_state)); scene=rpg_house; scope=door_state_count`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `open_door_count` | `count(door, state(door, open)); scene=rpg_house; scope=door_state_count` |
| `closed_door_count` | `count(door, state(door, closed)); scene=rpg_house; scope=door_state_count` |

## Program Metadata
- Program signatures: `count.door_state`
- Base program contract: `count(door, state(door, target_state)); scene=rpg_house; scope=door_state_count`
- Parameter axes: `target_state`, `door_state_count`, `room_count`
- Arguments:
  - `door`: doorway; allowed visible generated doors; source `scene_ir.doors`
  - `target_state`: door_state; allowed `open|closed`; source `query_id`
  - `door_state_count`: integer; configured answer support is constrained by generated door count; source `parameter_axes`
- Argument metadata status: `curated`
- Supported query ids: `open_door_count`, `closed_door_count`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer is the number of visible doors whose state matches the query.

## Annotation Contract
- Annotation schema: `point_set`
- Generator `annotation_gt.type`: `point_set`
- Annotation contains one point on each counted door.
- Annotation excludes doors in the opposite state, rooms, walls, furniture, and decorative fixtures.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_house/illustrations_rpg_house_v0.json`.
- Public prompts ask for either open doors or closed doors.
- Render-only attributes such as palette, floor colors, furniture layout, room shapes, and canvas profile must not be query ids.
- Door ids, door states, matching door ids, matching door center points, generated room count, projected point-set annotation, and diagnostic room/door bboxes must be recorded in the trace.
