# `task_puzzles_arithmetic_equation_value`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `arithmetic`
3. Task id: `task_puzzles_arithmetic_equation_value`
4. Objective: answer the exact integer that should fill the explicit unknown slot in a visual arithmetic equation puzzle.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `result_unknown`
   - `operand_unknown`
2. Supported `scene_variant` values:
   - `equation_strip`
   - `equation_card`
   - `equation_outline`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one arithmetic puzzle per image,
   - exactly one equation row,
   - `2..5` boxed values on the left side of the equation by default,
   - one boxed result on the right side of the equation,
   - `3..6` visible boxed slots in total by default,
   - boxed integer slots plus operator tokens,
   - exactly one explicit unknown slot rendered as `?`,
   - arithmetic operators are sampled from `+`, `-`, and `×`,
   - `operand_unknown` hides one of the left-side operand boxes, while `result_unknown` hides the right-side result box.
6. Generation guarantees:
   - the answer is always a positive integer by default,
   - left-side operand count is sampled per instance instead of staying fixed,
   - rendered visible values stay within the configured visible-value cap,
   - the unknown slot is unique by construction,
   - the rendered expression is evaluated with standard multiplication precedence over addition/subtraction.

## 3) Prompt contract
1. Bundle: `puzzles_arithmetic_v1`
2. `task_family_key`: `arithmetic_unknown_slot_puzzle`
3. `task_key`: `equation_value_query`
4. `task_variant_key`: `result_unknown|operand_unknown`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/puzzles/arithmetic.yaml`,
   - deterministic bundle selection from `prompts/puzzles/arithmetic/puzzles_arithmetic_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the missing integer; prompt-facing evidence is the bbox for the explicit question-mark slot.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly one `bbox_set` item: the bbox of the unknown slot.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `puzzle_slot` entities for value and unknown boxes
   - `puzzle_operator` entities for `+`, `-`, and `=` tokens
4. `render_map` includes:
   - `scene_bbox_px`
   - `slot_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `equation_rows`
   - `solver_trace`
   - `query_slot_id`
   - `supporting_slot_ids`
   - `slot_count`
   - `slot_count_range`
   - `operand_count`
   - `operand_count_range`
   - `step_count`
   - final integer answer

## 5) Visual policy
1. Background and post-image noise use the merged puzzles-domain visual defaults from `configs/domains/puzzles/base.yaml`.
2. V1 arithmetic puzzles use clean light solid backgrounds only.
3. Scene variants change framing and outline style while preserving the same slot/operator geometry contract.
4. The unknown slot stays visually highlighted relative to the known numeric slots.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated equation scene.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded `query_slot_id` projection, not OCR from pixels.
