# `task_icons__pattern_grid__size_pattern_violation_index`

## 1) Identity
1. Domain: `icons`
2. Scene id: `pattern_grid`
3. Task group: `pattern`
4. Task id: `task_icons__pattern_grid__size_pattern_violation_index`
5. Objective: identify which numbered cell breaks a 2D icon-size grid rule.

## 2) Scene + Task Contract
1. Entities/relations: one numbered `3 x 3` grid, with exactly one icon per visible cell.
2. Public `query_variant`: `default`.
3. Diagnostic `query_id`: `grid_size_violation`.
4. Answer type: `answer_gt.type = integer` (the 1-based violating grid-cell index).
5. Evidence type: `evidence_gt.type = bbox_set` (exactly one box: the violating numbered cell).
6. Rule policy: clean cells follow `level[row, col] = base + row * row_step + col * col_step` over size levels `{1,2,3,4,5}` and steps `{-1,0,1}`, with the all-zero step pair disallowed. The calibrated public mix requires the violating cell to differ from the rule by at least two size levels.
7. Asset policy: uses the full curated icon pool because only size changes across the rule.
8. Ambiguity policy: generation rejects any instance where another supported size rule would make a different violating index plausible.

## 3) Prompt Contract
1. `prompt_bundle_id`: `icons_pattern_v0`
2. `scene_key`: `structured_violation_scene`
3. `task_key`: `structured_violation_query`
4. Answer+evidence JSON shape: `{"evidence":[[540,126,654,458]],"answer":5}`
5. Answer-only JSON shape: `{"answer":5}`

## 4) Determinism + Constraints
1. The public task directly samples and renders the grid-size violation scene.
2. Unique-answer policy: the violating index is sampled first and accepted only when the observed grid has one plausible violating cell.
3. No-auto-relaxation guarantee: unsupported rule configs, missing assets, ambiguous explanations, and placement failures cause rejection instead of weakening constraints.
4. Trace metadata records `scene_variant=numbered_grid`, public `query_variant=default`, and `query_id=grid_size_violation`.

## 5) Complexity + Tests
1. Complexity definition/components: grid-size complexity based on grid rule, size-level ambiguity, answer position, and visual clutter.
2. Determinism/build tests: `tests/test_icons_pattern_structured_violation_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_pattern_structured_violation_tasks.py`
