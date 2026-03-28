# `task_icons_pattern_grid_size_violation`

## 1) Identity
1. Domain: `icons`
2. Task group: `pattern`
3. Task id: `task_icons_pattern_grid_size_violation`
4. Objective: identify which numbered grid box breaks a 2D icon-size pattern.

## 2) Scene + task contract
1. Entities/relations: one single-panel image with a `3 x 3` grid of numbered boxes; every box contains exactly one icon.
2. Supported `task_variant` values: `row_col_size_grid_violation`.
3. Answer type: `answer_gt.type = integer` (the 1-based box index in row-major order).
4. Evidence type: `evidence_gt.type = bbox_set` (exactly one box: the violating grid box in final image pixel coordinates).
5. Pattern rule: the clean grid follows one row/column size-level rule `size_level[row, col] = base + row * row_step + col * col_step`, using symbolic levels `{1,2,3,4,5}` and row/column step supports `{-1,0,1}` with the all-zero step pair disallowed.
6. Size policy: symbolic size levels map to one strictly increasing nominal-size ladder with a fixed per-instance level gap of `8` px; the ladder is resolved after sampling grid-cell geometry so every level fits the visible content boxes.
7. Violation policy: exactly one cell is corrupted away from the clean rule, and generation rejects any grid where more than one cell index could plausibly be the unique violation under the supported size-rule family.
8. Asset policy: the shared grid icon is drawn from the curated `assets/icons/all_icons.txt` pool, and every Scene icon keeps that same icon type.
9. Visual variation: all Scene icons keep the same tint and the same rotation within one instance; only nominal size changes across the grid.
10. Size band: the resolved nominal icon sizes stay within the configured `34..82` px band, clipped downward only when a sampled cell content area would otherwise be too small.
11. Cell geometry policy: each instance samples one cell-box width in `116..152` px and one cell-box height in `116..152` px; the final canvas size is derived from that sampled grid geometry.
12. Placement policy: each box contains exactly one centered icon; user-facing evidence points to the violating box rather than the icon itself.
13. Noise policy: each Scene icon may receive `0..1` subtle Prism-style edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per instance in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_pattern_v1`
2. `task_family_key`: `numbered_grid_rotation_pattern`
3. `task_key`: `grid_size_violation_query`
4. Answer+evidence JSON shape: `{"evidence":[[540,126,654,458]],"answer":5}`
5. Answer-only JSON shape: `{"answer":5}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: the family stem establishes the numbered 2D grid; task wording asks only for the numbered box that breaks the size pattern.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the answer index is sampled first from the configured `1..9` support, then one feasible `(base_size_level, row_step_levels, col_step_levels, violation_size_level)` tuple is chosen so that the violating index is unique under the supported rule family.
3. Reject/resample conditions: unsupported answer/rule config, missing curated assets, ambiguous violating-index explanations, too-repetitive clean patterns with fewer than 3 distinct size levels, or any per-cell rendering failure.
4. No-auto-relaxation guarantee: generation fails on unmet rule or ambiguity constraints instead of weakening the rule family or allowing multiple plausible violating positions.
5. Evidence scope: the user-facing `bbox_set` contains only the violating grid box; the clean pattern parameters, symbolic size levels, and per-cell nominal sizes stay in trace metadata.
6. Trace style metadata records the sampled single-tint palette, icon-noise config, sampled cell width/height, size-level ladder, and final per-instance nominal sizes/rotations/noise edits.
7. Balanced defaults: `_sampling_index` cycles evenly over the answer-index support `1..9`.

## 5) Complexity + tests
1. Complexity definition/components: fixed grid scan load + two-axis size-rule load + violating-cell ambiguity + icon clutter.
2. Determinism/build tests: `tests/test_icons_pattern_grid_size_violation_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_pattern_grid_size_violation_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
