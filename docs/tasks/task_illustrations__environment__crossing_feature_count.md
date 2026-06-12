# `task_illustrations__environment__crossing_feature_count`

## Summary
- Domain: `illustrations`
- Scene id: `environment`
- Implementation scene: `counting`
- Implementation source: `trace/tasks/illustrations/counting/feature_relation_object_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__environment__crossing_feature_count` -> `task_illustrations__environment__crossing_feature_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts visible features that cross a queried road or river feature.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `crossing_feature_count` | `count(filter(environment_features, crosses(feature, target_linear_feature))); scene=environment; scope=crossing_feature_count` |

## Program Metadata
- Program signatures: `count.relation_attribute`
- Base program contract: `count(filter(environment_features, crosses(feature, target_linear_feature))); scene=environment; scope=crossing_feature_count`
- Parameter axes: `fixed_query`
- Arguments:
  - `environment_features`: semantic_role; allowed `visible_environment_features`; source `program_schema_concrete`
  - `feature`: semantic_role; allowed `environment_feature_instance`; source `program_schema_concrete`
  - `target_linear_feature`: semantic_role; allowed `visible_linear_feature`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `crossing_feature_count`

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

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/environment/task_illustrations__environment__crossing_feature_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
