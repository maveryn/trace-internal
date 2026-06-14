# `task_physics__shadow_cause__light_source_label`

## Summary
- Domain: `physics`
- Scene id: `shadow_cause`
- Implementation scene: `optics`
- Implementation source: `trace/tasks/physics/optics/shadow_cause.py`

## Task Contract
Selects the labeled light source that would cast the visible shadow from the object.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `source_from_shadow_label` | `option_letter(select(candidate_light_sources, direction_from_object_to_light_source=opposite(direction_from_object_to_cast_shadow))); scene=shadow_cause; scope=light_source_label; query_branch=source_from_shadow_label` |

## Program Metadata
- Program signatures: `physics.shadow_cause_light_source_label`
- Base program contract: `option_letter(select(candidate_light_sources, direction_from_object_to_light_source=opposite(direction_from_object_to_cast_shadow))); scene=shadow_cause; scope=light_source_label`
- Parameter axes: `correct_option_letter`, `shadow_direction`, `object_shape`
- Arguments:
  - `candidate_light_sources`: visual_candidate_set; allowed `six_labeled_candidate_lamps`; source `program_schema_concrete`
  - `object`: semantic_role; allowed `visible_shadow_casting_object`; source `program_schema_concrete`
  - `cast_shadow`: semantic_role; allowed `visible_shadow_on_floor`; source `program_schema_concrete`
  - `shadow_direction`: query_operand; allowed `eight_compass_directions`; source `sampled_axis`
- Argument metadata status: `curated`
- Supported query ids: `source_from_shadow_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the label of the unique candidate light source opposite the shadow direction from the object.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys are `object` and `shadow`.
- Annotation must mark minimal visual witnesses from the final rendered diagram: the object and its cast shadow. Annotation must not mark option letters, lamp bboxes, decorative grid lines, title text, or hidden source-direction metadata.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, shadow direction, object shape, option mapping, and verifier payloads must be explicit in the instance trace.
- Object color, object shape, and option letter must stay non-semantic; only the relative object-to-shadow direction determines the correct light source.
