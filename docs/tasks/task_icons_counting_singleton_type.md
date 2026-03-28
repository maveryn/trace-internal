# `task_icons_counting_singleton_type`

## 1) Identity
1. Domain: `icons`
2. Task group: `counting`
3. Task id: `task_icons_counting_singleton_type`
4. Objective: count how many icons have a type that appears exactly once in the image.

## 2) Scene + task contract
1. Entities/relations: one single-panel image with `6..15` randomly placed icons in the `Scene` panel.
2. Supported `task_variant` values: one current scene variant, `singleton_type_count`.
3. Answer type: `answer_gt.type = integer`.
4. Evidence type: `evidence_gt.type = bbox_set` (scene-only boxes in final image pixel coordinates, sorted top-to-bottom then left-to-right).
5. Count policy: `target_count` is the number of singleton-type icons and is sampled from `0..5`; `object_count` is sampled from `6..15` subject to leaving at least one repeated type in the image.
6. Frequency policy: singleton icons are counted by icon type only. Colors and rotations may vary per icon, but two icons with the same `icon_id` still belong to the same type-frequency group.
7. Repeated-type policy: the non-singleton portion of the scene is partitioned into `1..4` repeated icon types, each with multiplicity `2..4`, and the exact multiplicities are recorded in trace metadata.
8. Asset policy: scene icons are drawn from the curated Prism `assets/icons/all_icons.txt` pool copied into TRACE.
9. Color/orientation policy: scene icons are tinted from one per-instance Prism-style palette sampled with anchor-aware Lab-distance separation from the panel/background chrome, and per-icon rotations are sampled from `{0, 90, 180, 270}`.
10. Placement policy: scene icons are placed randomly in the single scene panel, and any pairwise overlap is capped at `10%` of the smaller icon box area.
11. Noise policy: each scene icon may receive `0..2` subtle Prism-style edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per instance in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_counting_v1`
2. `task_family_key`: `single_scene_counting`
3. `task_key`: `counting_query`
4. Answer+evidence JSON shape: `{"evidence":[[116,128,176,188],[634,302,704,372]],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: the family stem establishes one single scene panel; task wording asks only for the count of icons whose type appears exactly once in the image.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: singleton-type icon ids are sampled first, repeated-type multiplicities are sampled second, and evidence boxes are the rendered boxes of those singleton icons.
3. Reject/resample conditions: unsupported count config, missing curated asset ids, infeasible repeated-type partitions, or overlap-constrained placement/render failures.
4. No-auto-relaxation guarantee: generation fails on unmet scene-capacity/asset/overlap constraints instead of weakening the singleton-frequency contract.
5. Evidence scope: the user-facing `bbox_set` covers only singleton-type icons; the full per-type frequency table stays in trace metadata.
6. Trace style metadata records the sampled icon palette, the icon-noise config, the full per-type frequency map, and the final per-instance `tint_rgb` assignments and rotations.
7. Balanced defaults: `resolve_selection_index(...)` balances singleton-count answers across `0..5` when `_sampling_index` is present.

## 5) Complexity + tests
1. Complexity definition/components: visible icon load + scene-internal type-grouping ambiguity + icon clutter.
2. Determinism/build tests: `tests/test_icons_counting_singleton_type_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_counting_singleton_type_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
