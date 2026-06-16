# `task_illustrations__park_playground__person_count`

## Summary
- Domain: `illustrations`
- Scene id: `park_playground`
- Implementation source: `trace/tasks/illustrations/park_playground/person_count.py`

## Task Contract
Count every visible person in one rendered park/playground illustration.

## Program Contract
- Program code: `count(visible_people); scene=park_playground; scope=person_count`
- Program signature: `count.total_instances`
- Query ids: `single`
- Arguments:
  - `visible_people`: semantic role; allowed `all_visible_park_people`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer is the number of rendered people in the scene.

## Annotation Contract
- Annotation schema: `point_set`
- Generator `annotation_gt.type`: `point_set`
- Annotation is an unordered set of final-image pixel points, one near the center of each visible person.
- Annotation and answer are projected from the same generated scene trace.

## Prompt And Trace Requirements
- Prompt text comes from `prompts/illustrations/park_playground/illustrations_park_playground_v0.json`.
- The prompt scene layer must not disclose the sampled person count.
- Render randomness, sampled style, activity mix, person count, and verifier payloads are recorded in trace metadata.
