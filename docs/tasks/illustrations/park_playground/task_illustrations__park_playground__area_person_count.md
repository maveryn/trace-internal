# `task_illustrations__park_playground__area_person_count`

## Summary
- Domain: `illustrations`
- Scene id: `park_playground`
- Implementation source: `trace/tasks/illustrations/park_playground/area_person_count.py`

## Task Contract
Count visible people placed inside one sampled semantic park/playground area.

## Program Contract
- Program code: `count(filter(people, area(person)=target_zone)); scene=park_playground; scope=area_person_count`
- Program signature: `count.scoped_attribute`
- Query ids: `single`
- Arguments:
  - `people`: semantic role; allowed `visible_people`
  - `person`: semantic role; allowed `park_person_instance`
  - `target_zone`: semantic operand; allowed `playground`, `garden`; source `query_spec.params.target_zone`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer is the count of people whose rendered final placement zone equals `target_zone`.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted person.
- Annotation and answer are projected from the same generated scene trace.

## Prompt And Trace Requirements
- Prompt text comes from `prompts/illustrations/park_playground/illustrations_park_playground_v0.json`.
- Render randomness, sampled style, `target_zone`, and verifier payloads are recorded in trace metadata.
