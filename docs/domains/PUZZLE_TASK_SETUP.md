# Puzzle Task Setup

## Purpose
Capture the active v1 contract for the `puzzles` domain.

## Active family
1. Current active `task_group`: `arithmetic`
2. Current active task:
   - `task_puzzles_arithmetic_equation_value`

## Family contract
1. Puzzle families are hidden-rule / hidden-variable reasoning families, not generic icon grids or mini tables.
2. The active arithmetic family centers on explicit unknown-slot puzzles so the prompt-facing evidence can stay local and simple.
3. Arithmetic puzzle variants should widen `task_variant` before creating a new task id when the same scene grammar and one-box evidence contract still hold.

## `task_puzzles_arithmetic_equation_value`
1. Supported `task_variant` values:
   - `result_unknown`
   - `operand_unknown`
2. Supported `scene_variant` values:
   - `equation_strip`
   - `equation_card`
   - `equation_outline`
3. Answer contract:
   - `answer_gt.type = integer`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the explicit question-mark slot
5. Scene contract:
   - one arithmetic puzzle per image,
   - exactly one equation row,
   - `2..5` boxed values on the left side of the equation by default,
   - one boxed result on the right side of the equation,
   - `3..6` visible boxed slots in total by default,
   - every variant includes exactly one explicit unknown slot rendered as `?`,
   - visible operands and result values are integers,
   - arithmetic operators are sampled from `+`, `-`, and `×`,
   - the answer is the integer that belongs in the unknown slot.
6. Trace contract:
   - `scene_ir.entities` includes slot and operator entities,
   - `render_map.slot_bboxes_px` stores each slot bbox keyed by slot id,
   - `execution_trace` stores `equation_rows`, `solver_trace`, `query_slot_id`, `slot_count`, `slot_count_range`, `operand_count`, `operand_count_range`, and `step_count`,
   - prompt-facing evidence is projected from `query_slot_id`, not inferred from pixels.

## Prompt contract
1. Bundle: `puzzles_arithmetic_v1`
2. `task_family_key`: `arithmetic_unknown_slot_puzzle`
3. `task_key`: `equation_value_query`
4. `task_variant_key`: `result_unknown|operand_unknown`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the question-mark slot.

## Visual policy
1. Puzzles use the same light solid background baseline as the other clean synthetic domains.
2. Arithmetic scene variants vary panel chrome and outline treatment, not the semantic slot/operator layout.
3. The unknown slot should stay visually salient relative to known value slots.

## Determinism + review
1. Deterministic generation/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the task policy level.
3. No semantic auto-relaxation: every generated puzzle has exactly one valid integer answer.
4. Review/sample overlays should use `render_map.slot_bboxes_px[query_slot_id]` for the prompt-facing witness.
