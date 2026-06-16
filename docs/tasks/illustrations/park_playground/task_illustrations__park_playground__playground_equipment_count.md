# `task_illustrations__park_playground__playground_equipment_count`

## Summary
- Domain: `illustrations`
- Scene id: `park_playground`
- Implementation source: `trace/tasks/illustrations/park_playground/playground_equipment_count.py`

## Task Contract
Count visible playground equipment items of one sampled type.

## Program Contract
- Program code: `count(filter(playground_equipment, equipment_type(equipment)=target_equipment_type)); scene=park_playground; scope=playground_equipment_count`
- Program signature: `count.single_attribute_membership`
- Query ids: `single`
- Arguments:
  - `playground_equipment`: semantic role; allowed `visible_playground_equipment`
  - `equipment`: semantic role; allowed `playground_equipment_instance`
  - `target_equipment_type`: semantic operand; allowed `slide`, `swing_set`, `seesaw`, `climbing_frame`; source `query_spec.params.target_equipment_type`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer is the count of equipment items whose rendered equipment type equals `target_equipment_type`.

## Annotation Contract
- Annotation schema: `point_set`
- Generator `annotation_gt.type`: `point_set`
- Annotation is an unordered set of final-image pixel points, one near the center of each counted equipment item.
- Annotation and answer are projected from the same generated scene trace.

## Prompt And Trace Requirements
- Prompt text comes from `prompts/illustrations/park_playground/illustrations_park_playground_v0.json`.
- Render randomness, sampled style, `target_equipment_type`, and verifier payloads are recorded in trace metadata.
