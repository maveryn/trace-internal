# `task_illustrations__pixel_village__object_type_count`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation scene package: `pixel_village`
- Implementation source: `trace/tasks/illustrations/pixel_village/object_type_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__pixel_village__object_type_count` -> `task_illustrations__pixel_village__object_type_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts visible village entities for one approved public target category.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `object_type_count` | `count(filter(pixel_village_entities, target_entity_type(entity)=target_object)); scene=pixel_village; scope=object_type_count; query_branch=object_type_count` |

## Program Metadata
- Program signatures: `count.single_attribute_membership`
- Base program contract: `count(filter(pixel_village_entities, target_entity_type(entity)=target_object)); scene=pixel_village; scope=object_type_count`
- Parameter axes: `target_object`
- Arguments:
  - `entity`: semantic_role; allowed `pixel_village_entity`; source `program_schema_concrete`
  - `pixel_village_entities`: semantic_role; allowed `visible_pixel_village_entities`; source `program_schema_concrete`
  - `target_object`: semantic_role; allowed `building`, `person`, `tree`, `lamp_post`, `well`, `pond`; source `parameter_axes`
- Argument metadata status: `curated`
- Supported query ids: `object_type_count`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a positive integer derived from the same execution trace as the annotation.
- Generated instances must keep the selected target count at or below the configured cap, currently `8`.
- Tree-count instances suppress cemetery territory so cemetery dead-tree decor is not an ambiguous non-counted witness.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted entity.
- Annotation must not include paths, labels, whole territories, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations counting prompt bundle.
- Public prompts use `people` or `person`, not the internal renderer label `villager`.
- Render-only attributes such as gender, facing, tree subtype, door state, roof style, season, and territory styling must not be queried.
- Landmark building variants are optional scene variety; the renderer must not force all building types into each instance.
- When `target_object == "tree"`, the trace records the task-layer render constraint that disables cemetery territory.
- Counted entity ids, target object, target public name, renderer metadata, and projected bboxes must be recorded in the trace.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/pixel_village/task_illustrations__pixel_village__object_type_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
