# `task_illustrations__environment__lit_window_count`

## Summary
- Domain: `illustrations`
- Scene id: `environment`
- Implementation scene: `environment`
- Implementation source: `trace/tasks/illustrations/environment/lit_window_count.py`

## Task Contract
Counts lit windows in rendered environment buildings.

## Program Contract
`count(filter(building_windows, is_lit(window))); scene=environment; scope=lit_window_count`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `count(filter(building_windows, is_lit(window))); scene=environment; scope=lit_window_count` |

## Program Metadata
- Program signatures: `count.single_attribute_membership`
- Base program contract: `count(filter(building_windows, is_lit(window))); scene=environment; scope=lit_window_count`
- Parameter axes: `fixed_query`
- Arguments:
  - `building_windows`: semantic_role; allowed `visible_building_windows`; source `program_schema_concrete`
  - `window`: semantic_role; allowed `window_instance`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is an integer in the default range `1..6`, derived from the same execution trace as the annotation.

## Annotation Contract
- Annotation schema: `point_set`
- Generator `annotation_gt.type`: `point_set`
- Annotation is an unordered set of final-image pixel points, one near the center of each counted/selected visual witness. Do not include labels, numeric annotations, or context-only regions.
- Annotation and answer must be projected from the same generated scene trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, and verifier payloads must be explicit in the instance trace.
- Distractor/context text may be rendered only when it is part of the scene grammar and must not be treated as annotation unless it is the queried visual witness.
