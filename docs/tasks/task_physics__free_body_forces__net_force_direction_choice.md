# `task_physics__free_body_forces__net_force_direction_choice`

## Summary
- Domain: `physics`
- Scene id: `free_body_forces`
- Implementation scene: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/free_body_forces.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__free_body_forces__net_force_direction_choice` -> `task_physics__free_body_forces__net_force_direction_choice`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the candidate arrow showing the net-force direction for one object from visible applied-force arrows and magnitude labels.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `net_force_direction_choice` | `option_letter(direction(sum(applied_force_vectors))); scene=free_body_forces; scope=net_force_direction_choice; query_branch=net_force_direction_choice` |

## Program Metadata
- Program signatures: `physics.net_force_direction_choice`
- Base program contract: `option_letter(direction(sum(applied_force_vectors))); scene=free_body_forces; scope=net_force_direction_choice`
- Parameter axes: `fixed_query`, `scene_variant`, `net_force_direction`, `correct_option_letter`, `accent_color_name`
- Arguments:
  - `applied_force_vectors`: visual_input_set; allowed `visible_cardinal_force_arrows_with_magnitude_labels`; source `program_schema_concrete`
  - `candidate_net_force_arrows`: visual_candidate_set; allowed `eight_labeled_direction_arrows_A_H`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `net_force_direction_choice`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the visible option letter whose candidate arrow matches the direction of the summed applied-force vector.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation marks each applied force arrow together with its magnitude label.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not option arrows, option letters, the object body alone, decorative panel chrome, or any derived resultant annotation.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Prompts must ask for the net-force direction, not the object's subsequent motion direction.
- Render randomness, sampled fonts/styles, force magnitudes, option mapping, answer construction, and verifier payloads must be explicit in the instance trace.
- Option letters, colors, scene variants, and canceling-force distractors must stay non-semantic; only the summed applied-force vectors determine the answer.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/free_body_forces/task_physics__free_body_forces__net_force_direction_choice/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
