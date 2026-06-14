# `task_physics__wave_interference__interference_point_choice`

## Summary
- Domain: `physics`
- Scene id: `wave_interference`
- Implementation scene: `waves`
- Implementation source: `trace/tasks/physics/waves/interference_tank.py`

## Task Contract
Selects the candidate point satisfying the requested constructive/destructive interference condition.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `interference_point_choice` | `option_letter(select(candidate_points, interference_condition(path_difference_parity, phase_relation)=target_condition)); scene=wave_interference; scope=interference_point_choice` |

## Program Metadata
- Program signatures: `physics.wave_interference_condition_choice`
- Base program contract: `option_letter(select(candidate_points, interference_condition(path_difference_parity, phase_relation)=target_condition)); scene=wave_interference; scope=interference_point_choice`
- Parameter axes: `phase_relation`, `target_condition`
- Arguments:
  - `candidate_points`: semantic_role; allowed `visible_candidate_points`; source `program_schema_concrete`
  - `path_difference_parity`: semantic_role; allowed `candidate_path_difference_parity`; source `program_schema_concrete`
  - `phase_relation`: semantic_role; allowed `in_phase`, `opposite_phase`; source `program_schema_concrete`
  - `target_condition`: semantic_role; allowed `constructive`, `destructive`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `interference_point_choice`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

## Annotation Contract
- Annotation schema: `point_set`
- Generator `annotation_gt.type`: `point_set | unordered`
- Annotation is an unordered set of final-image pixel points over the queried event/target centers.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.
