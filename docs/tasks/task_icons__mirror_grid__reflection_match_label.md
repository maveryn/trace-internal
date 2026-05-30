# `task_icons__mirror_grid__reflection_match_label`

## 1) Identity
1. Domain: `icons`
2. Scene id: `mirror_grid`
3. Task group: `relation`
4. Task id: `task_icons__mirror_grid__reflection_match_label`
5. Objective: select the labeled Scene cell that is the requested mirror reflection of the Reference cell.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` cell on the left and a labeled `Scene` grid of option cells on the right.
2. Query id: `reflection_match_label`.
3. Supported `query_id` values: `vertical_reflection_match`, `horizontal_reflection_match`, `diagonal_main_reflection_match`, `diagonal_anti_reflection_match`.
4. Answer type: `answer_gt.type = option_letter`.
5. Evidence type: `evidence_gt.type = keyed_bbox_map` with `reference_cell` and `selected_option` pixel-space boxes.
6. Option policy: Scene cell count is fixed at `6` with labels `A..F`; exactly one cell is the requested reflection of the Reference, and calibration exports balance answer labels and answer positions.
7. Distractor policy: the calibrated mix includes one wrong-axis reflection distractor, the unreflected Reference pattern, and altered reflections with an extra unmatched icon. Distractors are rejected if they are pixel-identical to the requested reflection.
8. Asset policy: cells use the curated asymmetric icon subset from `assets/icons/non_symmetry.txt`; the Reference patch uses 2 or 3 icons and is sampled to have no supported mirror symmetry so wrong-axis reflections remain visually distinct.
9. Cell styling: the Reference cell and Scene cells use centered square patches so vertical, horizontal, and diagonal reflections share one consistent frame.
10. Noise policy: subtle per-icon edits are sampled before reflection, so the correct option is the rendered reflection of the exact visible Reference patch.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_relation_v0`
2. `scene_key`: `reference_grid_mirror_symmetry_relation`
3. `task_key`: `relation_query`
4. Answer+evidence JSON shape: `{"evidence":{"reference_cell":[72,132,252,312],"selected_option":[360,120,560,320]},"answer":"B"}`
5. Answer-only JSON shape: `{"answer":"B"}`
6. Required slots:
   - shared: `object_description`, one query-specific `question_text_*`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (scene/task/mode): exactly 5 templates per required key.
8. Prompt style: task wording names the requested left-right, top-bottom, top-left-to-bottom-right diagonal, or top-right-to-bottom-left diagonal reflection.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the answer index is sampled first, the correct reflected patch is inserted into exactly one labeled Scene cell, and every distractor is checked against that exact patch.
3. Reject/resample conditions: unsupported object count, empty icon pool, palette-separation failures, inability to render a non-symmetric Reference patch, or insufficient unique distractor patches.
4. No-auto-relaxation guarantee: generation fails on unmet layout/reflection constraints instead of accepting ambiguous options.
5. Semantic-unit rule: evidence uses role-keyed boxes for the Reference cell and matching Scene option cell, not the individual icons inside either cell.
6. Trace style metadata records the sampled palette, square patch placement, grid styling, validated text-legibility metadata, and reflection axis.

## 5) Complexity + tests
1. Complexity definition/components: calibrated 6-option count + reflection axis + rendered cell clutter.
2. Behavior/trace/prompt tests: `tests/test_icons_relation_reflection_match_label_tasks.py`
3. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
