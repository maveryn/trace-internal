# `task_physics__electromagnetic_induction__induced_current_direction_count`

## Summary
- Domain: `physics`
- Scene id: `electromagnetic_induction`
- Implementation task group: `magnetism`
- Implementation source: `trace/tasks/physics/magnetism/electromagnetic_induction.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__electromagnetic_induction__induced_current_direction_count` -> `task_physics__electromagnetic_induction__induced_current_direction_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts how many of six mini-panels have the queried induced-current direction from visible magnetic-flux-change cues.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `clockwise_induced_current_count` | `count(filter(induction_panels, induced_current_direction(panel)=clockwise)); scene=electromagnetic_induction; scope=induced_current_direction_count; query_branch=clockwise_induced_current_count` |
| `counterclockwise_induced_current_count` | `count(filter(induction_panels, induced_current_direction(panel)=counterclockwise)); scene=electromagnetic_induction; scope=induced_current_direction_count; query_branch=counterclockwise_induced_current_count` |
| `no_induced_current_count` | `count(filter(induction_panels, induced_current_direction(panel)=no_current)); scene=electromagnetic_induction; scope=induced_current_direction_count; query_branch=no_induced_current_count` |

## Program Metadata
- Program signatures: `physics.electromagnetic_induction_direction_count`
- Base program contract: `count(filter(induction_panels, induced_current_direction(panel)=target_current_class)); scene=electromagnetic_induction; scope=induced_current_direction_count`
- Parameter axes: `query_id`, `target_answer`, `field_orientation`, `flux_change_mechanism`
- Arguments:
  - `induction_panels`: visual_candidate_set; allowed `six_mini_panels`; source `program_schema_concrete`
  - `target_current_class`: semantic_role; allowed `clockwise`, `counterclockwise`, `no_current`; source `query_id`
  - `field_orientation`: semantic_role; allowed `into_page`, `out_of_page`; source `program_schema_concrete`
  - `flux_change_mechanism`: semantic_role; allowed `loop_enters_field`, `loop_leaves_field`, `field_strength_increases`, `field_strength_decreases`, `loop_area_expands`, `loop_area_contracts`, `loop_slides_inside_uniform_field`, `stationary_constant_field`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `clockwise_induced_current_count`, `counterclockwise_induced_current_count`, `no_induced_current_count`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the number of mini-panels whose induced-current class matches the query. Supported answers are `0..6`.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is the unordered set of bboxes around the full matching mini-panels.
- If the answer is `0`, annotation is an empty array.
- Annotation must not mark individual field symbols, loop arrows, cue text alone, derived current arrows, decorative grid lines, or panel chrome.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics magnetism prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, target answer, panel flux-change mechanisms, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep the field orientation and flux-change cue visible in every mini-panel.
- The renderer must construct exactly six panels and support the full answer range `0..6`.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/electromagnetic_induction/task_physics__electromagnetic_induction__induced_current_direction_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
