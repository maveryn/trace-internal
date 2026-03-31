# `task_icons_pattern_structured_violation`

## 1) Identity
1. Domain: `icons`
2. Task group: `pattern`
3. Task id: `task_icons_pattern_structured_violation`
4. Objective: identify which numbered box breaks one structured icon rule.

## 2) Scene + task contract
1. Entities/relations: one single-panel numbered row or grid, with exactly one icon per visible box.
2. Supported `task_variant` values: `row_rotation_violation|grid_rotation_violation|grid_size_violation`.
3. Supported `scene_variant` values:
   - `row_rotation_violation` -> `sequence_row`
   - `grid_rotation_violation|grid_size_violation` -> `numbered_grid`
4. Answer type: `answer_gt.type = integer` (the 1-based violating box index).
5. Evidence type: `evidence_gt.type = bbox_set` (exactly one box: the violating numbered box in final image coordinates).
6. Rule families:
   - `row_rotation_violation`: a horizontal row of `5..7` numbered boxes follows one constant rotation step over `{0, 90, 180, 270}` with step support `{90, 270}`.
   - `grid_rotation_violation`: a numbered `3 x 3` grid follows `rotation[row, col] = base + row * row_step + col * col_step (mod 360)` with rotations `{0, 90, 180, 270}` and row/column step support `{90, 180, 270}`.
   - `grid_size_violation`: a numbered `3 x 3` grid follows one symbolic size-level rule `level[row, col] = base + row * row_step + col * col_step` over levels `{1,2,3,4,5}` and steps `{-1,0,1}` with the all-zero pair disallowed.
7. Violation policy: exactly one box is corrupted, and generation rejects any instance where another supported rule hypothesis would make a different violating index plausible.
8. Asset policy:
   - `row_rotation_violation|grid_rotation_violation` use the asymmetric Prism subset so orientation stays meaningful.
   - `grid_size_violation` uses the full Prism pool because only size changes across the rule.
9. Visual policy:
   - rotation variants keep one shared icon type and tint within the instance;
   - size variant keeps one shared icon type, tint, and rotation, and changes only symbolic size levels.
10. Geometry policy: row instances fit the canvas to sampled row-box geometry, while grid instances fit the canvas to sampled numbered-grid cell geometry.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_pattern_v1`
2. `task_family_key`: `structured_violation_scene`
3. `task_key`: `structured_violation_query`
4. Answer+evidence JSON shape: `{"evidence":[[540,126,654,458]],"answer":5}`
5. Answer-only JSON shape: `{"answer":5}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt style: the family stem establishes the numbered row/grid layout, and variant wording asks only which numbered box breaks the active rule.

## 4) Determinism + constraints
1. Seed namespaces used: one variant-selection RNG via `spawn_rng(instance_seed, "task_icons_pattern_structured_violation.task_variant")`, then the delegated legacy rule generator.
2. Unique-answer policy: the violating index is sampled first inside the delegated row/grid generator, then one feasible clean-rule / corruption tuple is chosen so that only that numbered box remains plausible.
3. Reject/resample conditions: unsupported answer/rule config, missing curated assets, ambiguous violating-index explanations, or any per-cell rendering failure.
4. No-auto-relaxation guarantee: generation fails on unmet rule or ambiguity constraints instead of weakening the rule family or allowing multiple plausible violating boxes.
5. Consolidation policy: the wrapper preserves the legacy row/grid generators underneath but rewrites `scene_variant`, `task_variant`, prompt metadata, and `legacy_task_id` / `legacy_task_variant` trace slots to the broader consolidated surface.

## 5) Complexity + tests
1. Complexity definition/components: the delegated legacy complexity is preserved per rule family, so `grid_size_violation` and `grid_rotation_violation` stay harder than the row-rotation variant when the visual load is matched.
2. Determinism/build tests: `tests/test_icons_pattern_structured_violation_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_pattern_structured_violation_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
