# `task_illustrations__park_playground__equipment_use_person_count`

## Summary
- Domain: `illustrations`
- Scene id: `park_playground`
- Implementation source: `trace/tasks/illustrations/park_playground/equipment_use_person_count.py`

## Task Contract
Count visible people using one sampled playground equipment type.

## Program Contract
- Program code: `count(filter(people, uses_equipment(person, target_equipment_type))); scene=park_playground; scope=equipment_use_person_count`
- Program signature: `count.relation_attribute`
- Query ids: `single`
- Arguments:
  - `people`: semantic role; allowed `visible_people`
  - `person`: semantic role; allowed `park_person_instance`
  - `target_equipment_type`: semantic operand; allowed `slide`, `swing_set`, `seesaw`; source `query_spec.params.target_equipment_type`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer is the count of people whose rendered equipment-use attribute equals `target_equipment_type`.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted person.
- Annotation and answer are projected from the same generated scene trace.

## Prompt And Trace Requirements
- Prompt text comes from `prompts/illustrations/park_playground/illustrations_park_playground_v0.json`.
- Render randomness, sampled style, `target_equipment_type`, and verifier payloads are recorded in trace metadata.
