# `task_illustrations__source_scene_edit__object_count_after_edit`

## Summary
- Domain: `illustrations`
- Scene id: `source_scene_edit`
- Implementation scene package: `source_scene_edit`
- Implementation source: `trace/tasks/illustrations/source_scene_edit/object_count_after_edit.py`

## Task Contract
Applies a specified add/remove edit to a source scene and counts the target objects in the edited state.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `after_added_k_objects_count` | `count(filter(apply_scene_edit(scene_objects, edit_operation, edit_count), object_type(object)=target_object_type)); scene=source_scene_edit; scope=object_count_after_edit; query_branch=after_added_k_objects_count` |
| `after_removed_k_objects_count` | `count(filter(apply_scene_edit(scene_objects, edit_operation, edit_count), object_type(object)=target_object_type)); scene=source_scene_edit; scope=object_count_after_edit; query_branch=after_removed_k_objects_count` |

## Program Metadata
- Program signatures: `count.counterfactual`
- Base program contract: `count(filter(apply_scene_edit(scene_objects, edit_operation, edit_count), object_type(object)=target_object_type)); scene=source_scene_edit; scope=object_count_after_edit`
- Parameter axes: `fixed_query`
- Arguments:
  - `edit_count`: semantic_role; allowed `sampled_edit_count`; source `program_schema_concrete`
  - `edit_operation`: semantic_role; allowed `add_objects`, `remove_objects`; source `program_schema_concrete`
  - `object`: semantic_role; allowed `scene_object`; source `program_schema_concrete`
  - `scene_objects`: semantic_role; allowed `visible_scene_objects`; source `program_schema_concrete`
  - `target_object_type`: semantic_role; allowed `sampled_object_type`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `after_added_k_objects_count`, `after_removed_k_objects_count`

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
