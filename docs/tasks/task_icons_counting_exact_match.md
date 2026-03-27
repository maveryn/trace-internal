# `task_icons_counting_exact_match`

## 1) Identity
1. Domain: `icons`
2. Task group: `counting`
3. Task id: `task_icons_counting_exact_match`
4. Objective: count how many icons in the scene panel match the reference icon exactly in icon type, color, and orientation.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` icon on the left and `1..20` randomly placed scene icons on the right.
2. Supported `task_variant` values: one current scene variant, `exact_match_type_color_orientation`.
3. Answer type: `answer_gt.type = integer`.
4. Evidence type: `evidence_gt.type = bbox_set` (scene-only boxes in final image pixel coordinates, sorted top-to-bottom then left-to-right).
5. Count policy: `target_count` is sampled independently from `0..10`, `distractor_count` is sampled independently from `1..10`, and `object_count = target_count + distractor_count` therefore ranges from `1..20`.
6. Asset policy: reference + scene icons are drawn from the curated asymmetric Prism subset `assets/icons/non_symmetry.txt` so orientation remains visually meaningful.
7. Color policy: reference + scene icons are tinted from one per-instance palette with anchor-aware Lab-distance separation from the panel/background chrome; this task keeps a stricter threshold of `60` and samples palettes from `4..6` colors.
8. Orientation policy: v1 uses rotation-based orientation with candidates `{0, 90, 180, 270}`.
9. Binding policy: positives match the reference on all three queried attributes (`icon_id`, `tint_rgb`, `rotation_degrees`), while distractors are sampled mostly from structured partial-match classes (`2-of-3` and `1-of-3` attribute overlaps) so the task tests binding rather than only marginal filtering.
10. Placement policy: scene icons are placed randomly in the scene panel, and any pairwise overlap is capped at `10%` of the smaller icon box area.
11. Noise policy: each icon instance (reference + scene) may receive `0..2` subtle Prism-style edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per instance in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_counting_v1`
2. `task_family_key`: `reference_scene_counting`
3. `task_key`: `counting_query`
4. Answer+evidence JSON shape: `{"evidence":[[322,150,392,220],[584,320,654,390]],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: family wording establishes the Reference-vs-Scene layout; task wording explicitly asks for icons that match the Reference exactly in type, color, and orientation, and clarifies that orientation refers to rotation.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the exact-match set is sampled first, then rendered; evidence boxes are the rendered boxes of those same matches.
3. Reject/resample conditions: unsupported count config, missing curated asset ids, missing non-reference colors or rotations, or overlap-constrained placement/render failures.
4. No-auto-relaxation guarantee: generation fails on unmet scene-capacity/asset/color/orientation/overlap constraints instead of weakening the exact-match rule.
5. Evidence scope: the user-facing `bbox_set` covers scene matches only; the reference icon bbox is stored in trace metadata instead of the evidence payload.
6. Trace metadata records the sampled palette, per-instance `icon_id` / `tint_rgb` / `rotation_degrees`, per-instance noise edits, and one `attribute_match_category` per scene icon so review can distinguish exact matches from partial-match distractors.
7. Balanced defaults: `resolve_counting_target_and_distractor_triplet(...)` balances both target and distractor counts across feasible support when `_sampling_index` is present.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + task variant.
2. Determinism/build tests: `tests/test_icons_counting_exact_match_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_counting_exact_match_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
