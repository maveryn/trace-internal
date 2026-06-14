# `task_illustrations__environment__feature_side_object_count`

## Summary
- Domain: `illustrations`
- Scene id: `environment`
- Implementation scene: `counting`
- Implementation source: `trace/tasks/illustrations/counting/feature_relation_object_count.py`

## Task Contract
Counts foreground objects on one side of a road or river feature.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `feature_side_object_count` | `count(filter(scene_objects, side_of_feature(object, target_linear_feature)=target_side)); scene=environment; scope=feature_side_object_count` |

## Program Metadata
- Program signatures: `count.relation_attribute`
- Base program contract: `count(filter(scene_objects, side_of_feature(object, target_linear_feature)=target_side)); scene=environment; scope=feature_side_object_count`
- Parameter axes: `fixed_query`
- Arguments:
  - `object`: semantic_role; allowed `scene_object`; source `program_schema_concrete`
  - `scene_objects`: semantic_role; allowed `visible_scene_objects`; source `program_schema_concrete`
  - `target_linear_feature`: semantic_role; allowed `visible_linear_feature`; source `program_schema_concrete`
  - `target_side`: semantic_role; allowed `sampled_side`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `feature_side_object_count`

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
