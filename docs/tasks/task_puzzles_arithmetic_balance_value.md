# `task_puzzles_arithmetic_balance_value`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `arithmetic`
3. Task id: `task_puzzles_arithmetic_balance_value`
4. Objective: answer the exact integer that replaces the question mark in the final query row of an arithmetic equality-panel puzzle.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `sum_pair_unknown`
   - `two_panel_chain_unknown`
   - `three_panel_chain_unknown`
2. Supported `scene_variant` values:
   - `balance_strip`
   - `balance_card`
   - `balance_outline`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one arithmetic equality puzzle per image,
   - `2..3` equality panels stacked vertically,
   - each panel shows boxed symbols and/or boxed integers on a left side and a right side,
   - explicit plus signs appear between multiple boxed items on the same side,
   - an explicit equals sign appears between the two sides of each panel,
   - one final query row appears below the panels in the form `symbol = ?`,
   - the query-row symbol always matches one symbol that already appears in the equality panels,
   - numeric boxes always contain visible positive integers,
   - symbol boxes never print their numeric value directly.
6. Generation guarantees:
   - the answer is always a positive integer by default,
   - every panel is numerically balanced by construction,
   - the queried symbol value is unique by construction,
   - all visible numeric totals stay within the configured visible-value cap,
   - the question-mark query box is local and unique.

## 3) Prompt contract
1. Bundle: `puzzles_arithmetic_v1`
2. `task_family_key`: `arithmetic_balance_query_puzzle`
3. `task_key`: `balance_value_query`
4. `task_variant_key`: `sum_pair_unknown|two_panel_chain_unknown|three_panel_chain_unknown`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/puzzles/arithmetic.yaml`,
   - deterministic bundle selection from `prompts/puzzles/arithmetic/puzzles_arithmetic_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the integer value that replaces the question mark; prompt-facing evidence is the bbox for the question-mark query box.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly one `bbox_set` item: the bbox of the question-mark query box.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `puzzle_balance_box` entities for panel boxes and the two query-row boxes,
   - `puzzle_balance_operator` entities for explicit plus signs inside panels,
   - `puzzle_balance_equals` entities for the explicit equality markers in panels and the final query row,
   - `puzzle_balance_panel` entities for each equality panel.
4. `render_map` includes:
   - `scene_bbox_px`
   - `box_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `panel_specs`
   - `solver_trace`
   - `query_box_id`
   - `query_object_box_id`
   - `query_object_type`
   - `supporting_box_ids`
   - `panel_count`
   - `panel_count_range`
   - `total_box_count`
   - `total_box_count_range`
   - final integer answer

## 5) Visual policy
1. Background and post-image noise use the merged puzzles-domain visual defaults from `configs/domains/puzzles/base.yaml`.
2. V1 equality-panel puzzles use clean light solid backgrounds only.
3. Scene variants change framing and outline style while preserving the same equality-panel and query-box geometry contract.
4. The question-mark query box should remain visually distinct from the other panel and query-row boxes.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated equality scene.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded `query_box_id` projection for the final question-mark box, not OCR from pixels.
