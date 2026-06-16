# `task_illustrations__rpg_house__reachable_room_label`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_house`
- Implementation scene package: `rpg_house`
- Implementation source: `trace/tasks/illustrations/rpg_house/reachable_room_label.py`

## Task Contract
Selects the lettered room that is reachable from a red-outlined starting room using only open doorways in a procedurally partitioned house layout.

## Program Contract
`select(candidate_room, reachable(candidate_room, start_room, passable_door_state=open)); scene=rpg_house; scope=reachable_room_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select(candidate_room, reachable(candidate_room, start_room, passable_door_state=open)); scene=rpg_house; scope=reachable_room_label` |

## Program Metadata
- Program signatures: `select.reachable_component`
- Base program contract: `select(candidate_room, reachable(candidate_room, start_room, passable_door_state=open)); scene=rpg_house; scope=reachable_room_label`
- Parameter axes: `start_room`, `answer_room`, `room_count`
- Arguments:
  - `candidate_room`: room_label; allowed `A|B|C|D`; source `visible_candidate_labels`
  - `start_room`: room_id; allowed any visible generated room id; source `parameter_axes`
  - `passable_door_state`: door_state; allowed `open`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `letter_label`
- Generator `answer_gt.type`: `string`
- The answer value is one visible room letter. Exactly one lettered candidate room is reachable from the red-outlined start room by construction.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation is the final-image pixel box around the selected reachable room.
- Annotation excludes the red-outlined starting room, closed doors, open doorways, furniture, and non-answer rooms.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_house/illustrations_rpg_house_v0.json`.
- Public prompts refer to the `red-outlined starting room` and `lettered room` candidates.
- Render-only attributes such as palette, floor colors, furniture layout, and font family must not be query ids.
- Room graph, door states, candidate room labels, start room id, answer room id, generated room count, projected bbox, and diagnostic room/door bboxes must be recorded in the trace.
