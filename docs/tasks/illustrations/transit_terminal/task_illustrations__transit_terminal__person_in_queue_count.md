# `task_illustrations__transit_terminal__person_in_queue_count`

## Summary
- Domain: `illustrations`
- Scene id: `transit_terminal`
- Implementation scene: `counting`
- Implementation source: `trace/tasks/illustrations/counting/terminal_entity_location_count.py`

## Task Contract
Counts people standing in the rendered queue relation.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `count(filter(people, in_queue(person))); scene=transit_terminal; scope=person_in_queue_count` |

## Program Metadata
- Program signatures: `count.relation_attribute`
- Base program contract: `count(filter(people, in_queue(person))); scene=transit_terminal; scope=person_in_queue_count`
- Parameter axes: `fixed_query`
- Arguments:
  - `people`: semantic_role; allowed `visible_people`; source `program_schema_concrete`
  - `person`: semantic_role; allowed `person_instance`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a non-negative integer derived from the same execution trace as the annotation.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted/selected visual witness. Do not include labels, numeric annotations, or context-only regions.
- Annotation and answer must be projected from the same generated scene trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, and verifier payloads must be explicit in the instance trace.
- Distractor/context text may be rendered only when it is part of the scene grammar and must not be treated as annotation unless it is the queried visual witness.
