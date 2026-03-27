# `task_icons_transformation_pair_count`

## 1) Identity
1. Domain: `icons`
2. Task group: `transformation`
3. Task id: `task_icons_transformation_pair_count`
4. Objective: count how many labeled Scene cells apply the same icon transformation as the Reference pair.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` pair on the left and a labeled `Scene` grid of icon pairs on the right.
2. Supported `task_variant` values: one current scene variant, `same_pair_transform`.
3. Answer type: `answer_gt.type = integer`.
4. Evidence type: `evidence_gt.type = label_set` (sorted labels of the matching Scene cells).
5. Count policy: `target_count` is sampled independently from `0..6`, `distractor_count` is sampled independently from `1..6`, and `object_count = target_count + distractor_count` therefore ranges from `2..12`.
6. Asset policy: reference + scene pairs use the curated Prism `assets/icons/non_symmetry.txt` pool copied into TRACE.
7. Transform policy: the reference transform is sampled from the 7 non-identity canonical square-symmetry transforms (`rot90`, `rot180`, `rot270`, `flip_h`, `flip_v`, `flip_diag_main`, `flip_diag_anti`); candidate scene icons are accepted only when the chosen transform and at least one distractor transform remain visually distinct from identity and from each other.
8. Color policy: all icons in one instance share one sampled tint that is kept Lab-separated from the panel/background chrome.
9. Layout policy: the Scene panel renders a labeled grid of pair cells; each cell shows `icon -> transformed icon`, and the matching set is determined from the cell labels rather than pixel boxes.
10. Noise policy: each icon instance (both halves of every pair, including the Reference pair) may receive `0..2` subtle Prism-style edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per icon in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_transformation_v1`
2. `task_family_key`: `reference_pair_grid_transformation`
3. `task_key`: `transformation_query`
4. Answer+evidence JSON shape: `{"evidence":["B","E","G"],"answer":3}`
5. Answer-only JSON shape: `{"answer":3}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: the family stem establishes the Reference-vs-Scene grid layout; task wording asks only about matching the transformation rule.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching cell set is sampled first, then the Scene grid is built from that same match trace; evidence labels are the sorted labels of those matching cells.
3. Reject/resample conditions: unsupported count config, missing curated asset ids, transform-ambiguity failures, or pair-grid render failures.
4. No-auto-relaxation guarantee: generation fails on unmet asset/transform-distinctness/layout constraints instead of weakening the transformation contract.
5. Visual distinctness rule: scene/reference icons are filtered through cached transform signatures so the chosen transform never visually collapses to identity for that icon, and distractor transforms stay visually distinct from the reference transform.
6. Trace style metadata records the sampled tint palette, cell-grid styling, canonical transform ids, and the per-icon subtle-noise edits.
7. Balanced defaults: `resolve_counting_target_and_distractor_triplet(...)` balances both target and distractor counts across feasible support when `_sampling_index` is present.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + task variant.
2. Determinism/build tests: `tests/test_icons_transformation_pair_count_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_transformation_pair_count_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
