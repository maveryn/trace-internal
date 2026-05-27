# `task_icons__sequence_strip__rotation_sequence_violation_index`

## 1) Identity
1. Domain: `icons`
2. Scene id: `sequence_strip`
3. Task group: `pattern`
4. Task id: `task_icons__sequence_strip__rotation_sequence_violation_index`
5. Objective: identify which numbered box breaks a constant-rotation icon sequence.

## 2) Scene + Task Contract
1. Entities/relations: one horizontal row of 10 numbered boxes, each containing one icon.
2. Branch metadata: `query_id`
3. Diagnostic `query_id`: `row_rotation_violation`.
4. Answer type: `answer_gt.type = integer` (the 1-based violating box index).
5. Evidence type: `evidence_gt.type = bbox_set` (exactly one box: the violating numbered box).
6. Rule policy: the row follows one constant rotation step over `{0, 90, 180, 270}` until exactly one box is corrupted.
7. Asset policy: uses the asymmetric icon subset so orientation remains meaningful.
8. Ambiguity policy: generation rejects any instance where another supported rotation rule would make a different violating index plausible.

## 3) Prompt Contract
1. `prompt_bundle_id`: `icons_pattern_v0`
2. `scene_key`: `structured_violation_scene`
3. `task_key`: `structured_violation_query`
4. Answer+evidence JSON shape: `{"evidence":[[540,126,654,458]],"answer":5}`
5. Answer-only JSON shape: `{"answer":5}`

## 4) Determinism + Constraints
1. The public task directly samples and renders the sequence-rotation violation scene.
2. Unique-answer policy: the violating index is sampled first and accepted only when the observed row has one plausible violating box.
3. No-auto-relaxation guarantee: unsupported rule configs, missing assets, ambiguous explanations, and placement failures cause rejection instead of weakening constraints.
4. Trace metadata records `scene_variant=sequence_row` and `query_id=row_rotation_violation`.

## 5) Complexity + Tests
1. Complexity definition/components: row-rotation complexity based on the calibrated 10-cell sequence length, rotation step, answer position, and visual clutter.
2. Determinism/build tests: `tests/test_icons_pattern_structured_violation_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_pattern_structured_violation_tasks.py`
