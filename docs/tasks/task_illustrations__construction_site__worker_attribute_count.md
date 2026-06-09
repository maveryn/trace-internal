# `task_illustrations__construction_site__worker_attribute_count`

## Summary
- Domain: `illustrations`
- Scene id: `construction_site`
- Implementation task group: `counting`
- Implementation source: `trace/tasks/illustrations/counting/worker_safety_gear_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__construction_site__worker_attribute_count` -> `task_illustrations__construction_site__worker_attribute_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts visible workers matching one sampled safety-gear or held-tool attribute.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `hard_hat_color_worker_count` | `count(filter(workers, worker_selector(worker, target_attribute, target_attribute_value))); scene=construction_site; scope=worker_attribute_count; query_branch=hard_hat_color_worker_count` |
| `tool_holding_worker_count` | `count(filter(workers, worker_selector(worker, target_attribute, target_attribute_value))); scene=construction_site; scope=worker_attribute_count; query_branch=tool_holding_worker_count` |
| `vest_color_worker_count` | `count(filter(workers, worker_selector(worker, target_attribute, target_attribute_value))); scene=construction_site; scope=worker_attribute_count; query_branch=vest_color_worker_count` |

## Program Metadata
- Program signatures: `count.single_attribute_membership`
- Base program contract: `count(filter(workers, worker_selector(worker, target_attribute, target_attribute_value))); scene=construction_site; scope=worker_attribute_count`
- Parameter axes: `target_attribute`
- Arguments:
  - `target_attribute`: object_attribute; allowed `hard_hat_color`, `held_tool`, `vest_color`; source `program_schema_concrete|query_id|parameter_axes`
  - `target_attribute_value`: object_attribute; allowed `sampled_color`, `sampled_tool_type`; source `program_schema_concrete`
  - `worker`: semantic_role; allowed `worker_instance`; source `program_schema_concrete`
  - `workers`: semantic_role; allowed `visible_workers`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `hard_hat_color_worker_count`, `tool_holding_worker_count`, `vest_color_worker_count`

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
- Task review artifacts: `review/task-reviews/illustrations/construction_site/task_illustrations__construction_site__worker_attribute_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
