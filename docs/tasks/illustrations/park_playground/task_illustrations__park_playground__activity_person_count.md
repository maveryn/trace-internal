# `task_illustrations__park_playground__activity_person_count`

## Summary
- Domain: `illustrations`
- Scene id: `park_playground`
- Implementation source: `trace/tasks/illustrations/park_playground/activity_person_count.py`

## Task Contract
Count visible people matching one sampled activity in a park/playground scene.

## Program Contract
- Program code: `count(filter(people, activity(person)=target_activity)); scene=park_playground; scope=activity_person_count`
- Program signature: `count.single_attribute_membership`
- Query ids: `single`
- Arguments:
  - `people`: semantic role; allowed `visible_people`
  - `person`: semantic role; allowed `park_person_instance`
  - `target_activity`: semantic operand; allowed `sitting`, `walking`, `standing`, `playing_ball`; source `query_spec.params.target_activity`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer is the count of people whose rendered activity equals `target_activity`.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted person.
- Annotation and answer are projected from the same generated scene trace.

## Prompt And Trace Requirements
- Prompt text comes from `prompts/illustrations/park_playground/illustrations_park_playground_v0.json`.
- Render randomness, sampled style, `target_activity`, and verifier payloads are recorded in trace metadata.
