# `task_physics__stack_stability__stability_status_label`

## Summary
- Domain: `physics`
- Scene id: `stack_stability`
- Implementation task group: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/stack_stability.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__stack_stability__stability_status_label` -> `task_physics__stack_stability__stability_status_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Chooses the labeled brick stack whose center-of-mass projection has the queried stability status relative to its support base.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids vary only the target status predicate, while the renderer, answer schema, and annotation roles remain fixed.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `stable_stack_label` | `option_letter(select(brick_stacks, center_of_mass_projection_inside_support_base=true)); scene=stack_stability; scope=stability_status_label` |
| `tipping_stack_label` | `option_letter(select(brick_stacks, center_of_mass_projection_inside_support_base=false)); scene=stack_stability; scope=stability_status_label` |

## Program Metadata
- Program signatures: `physics.stability_status_label`
- Base program contract: `option_letter(select(brick_stacks, center_of_mass_projection_inside_support_base=status_predicate)); scene=stack_stability; scope=stability_status_label`
- Parameter axes: `query_id`, `correct_option_letter`, `tip_direction`, `stack_offset_profile`
- Arguments:
  - `brick_stacks`: visual_candidate_set; allowed `six_labeled_equal_density_brick_stacks`; source `program_schema_concrete`
  - `center_of_mass_projection`: semantic_role; allowed `red_com_marker_with_vertical_projection`; source `program_schema_concrete`
  - `support_base`: semantic_role; allowed `bottom_brick_support_footprint_bracket`; source `program_schema_concrete`
  - `status_predicate`: query_operand; allowed `stable|tipping`; source `query_id`
- Argument metadata status: `curated`
- Supported query ids: `stable_stack_label`, `tipping_stack_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the label of the unique stack matching the queried stability status.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys are `center_of_mass`, `projection`, and `support_footprint`.
- Annotation must mark minimal visual witnesses from the final rendered selected stack only: the red center-of-mass marker, its dashed vertical projection, and the support-footprint bracket. Annotation must not mark option letters, unrelated candidate stacks, decorative cell panels, background grid, prompt text, or answer labels.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, stack offset profiles, brick colors, option mapping, COM locations, support bounds, and verifier payloads must be explicit in the instance trace.
- Brick color, option label, row count, and tip direction must stay non-semantic; only the COM projection relative to the support footprint determines the answer.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/stack_stability/task_physics__stack_stability__stability_status_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
