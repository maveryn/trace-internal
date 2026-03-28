# `task_icons_sequence_rotation_violation`

## 1) Identity
1. Domain: `icons`
2. Task group: `sequence`
3. Task id: `task_icons_sequence_rotation_violation`
4. Objective: identify which numbered Scene box breaks a constant-rotation icon sequence.

## 2) Scene + task contract
1. Entities/relations: one single-panel image with a horizontal row of `5..7` numbered Scene boxes; every box contains exactly one icon.
2. Supported `task_variant` values: `constant_rotation_step_violation`.
3. Answer type: `answer_gt.type = integer` (the 1-based box index from left to right).
4. Evidence type: `evidence_gt.type = bbox_set` (exactly one box: the violating Scene box in final image pixel coordinates).
5. Sequence rule: the hidden clean row follows one constant rotation step using the asymmetric curated icon pool, with rotations drawn from `{0, 90, 180, 270}` and the base step drawn from `{90, 270}`.
6. Violation policy: exactly one cell is corrupted away from the clean rule, and generation rejects any row where more than one cell index could plausibly be the unique violation under the supported constant-step hypotheses.
7. Asset policy: the shared sequence icon is drawn from the curated Prism asymmetric subset `assets/icons/non_symmetry.txt`, and every Scene icon keeps that same icon type.
8. Visual variation: all Scene icons keep the same tint within one instance, while only rotation changes across the row.
9. Size policy: visible Scene icons are rendered at nominal sizes in `48..72` px.
10. Cell geometry policy: each instance samples one row box width in `96..136` px and one row box height in `96..136` px; the final canvas size is derived from that sampled row geometry.
11. Placement policy: each box contains exactly one icon, the box is visibly labeled with its 1-based index, and per-cell rendering still honors the shared `20%` overlap cap even though only one icon is present.
12. Noise policy: each Scene icon may receive `0..2` subtle Prism-style edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per instance in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_sequence_v1`
2. `task_family_key`: `sequence_rotation_violation`
3. `task_key`: `rotation_violation_query`
4. Answer+evidence JSON shape: `{"evidence":[[540,126,654,458]],"answer":4}`
5. Answer-only JSON shape: `{"answer":4}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: the family stem establishes the numbered single-panel sequence row; task wording asks only for the numbered box that breaks the rotation sequence.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the answer index is sampled first from the configured `1..7` support, then one feasible row length and one unambiguous `(start_rotation, step_delta, violation_rotation)` tuple are chosen so the violating index is unique by construction.
3. Reject/resample conditions: unsupported answer/length/step config, missing curated assets, ambiguous violating-index explanations, or any per-cell placement failure.
4. No-auto-relaxation guarantee: generation fails on unmet sequence or ambiguity constraints instead of weakening the constant-step rule or allowing multiple plausible violating positions.
5. Evidence scope: the user-facing `bbox_set` contains only the violating Scene box; the clean rotation rule and per-cell observed rotations stay in trace metadata.
6. Trace style metadata records the sampled single-tint palette, icon-noise config, sampled row box width/height, visible cell-label styling, and final per-instance nominal sizes/rotations/noise edits.
7. Balanced defaults: `_sampling_index` cycles evenly over the answer-index support `1..7`; sequence length is then sampled uniformly from the feasible support conditioned on that answer.

## 5) Complexity + tests
1. Complexity definition/components: sequence length + violating-cell position + violating rotation gap.
2. Determinism/build tests: `tests/test_icons_sequence_rotation_violation_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_sequence_rotation_violation_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
