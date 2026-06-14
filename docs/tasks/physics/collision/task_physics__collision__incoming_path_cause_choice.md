# `task_physics__collision__incoming_path_cause_choice`

## Summary
- Domain: `physics`
- Scene id: `collision`
- Implementation scene: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/collision_aftermath.py`

## Task Contract
Selects the incoming path that caused a shown collision aftermath. The image shows an impact point, the target puck after impact with its motion trail, and six labeled incoming path arrows.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `incoming_path_cause_choice` | `option_letter(select(candidate_incoming_paths, incoming_path_vector=target_after_motion_vector_from_impact_point)); scene=collision; scope=incoming_path_cause_choice; query_branch=incoming_path_cause_choice` |

## Program Metadata
- Program signatures: `physics.collision_cause_from_aftermath`
- Base program contract: `option_letter(select(candidate_incoming_paths, incoming_path_vector=target_after_motion_vector_from_impact_point)); scene=collision; scope=incoming_path_cause_choice`
- Parameter axes: `fixed_query`, `final_motion_direction`, `correct_option_letter`, `scene_variant`
- Arguments:
  - `candidate_incoming_paths`: semantic_role; allowed `visible_labeled_incoming_arrows_A_F`; source `program_schema_concrete`
  - `target_after_motion_vector_from_impact_point`: semantic_role; allowed `visible_impact_point_and_target_aftermath_trail`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `incoming_path_cause_choice`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys are `impact_point` and `target_after_motion`.
- Annotation is keyed because the impact marker and target aftermath have distinct causal roles.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option arrows, decorative chrome, or derived annotations.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, answer construction, and verifier payloads must be explicit in the instance trace.
- Candidate arrows are visible answer options and must not be highlighted as the correct cause.
