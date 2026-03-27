# `task_icons_relation_occlusion_order`

## 1) Identity
1. Domain: `icons`
2. Task group: `relation`
3. Task id: `task_icons_relation_occlusion_order`
4. Objective: count how many labeled Scene cells show the same front-to-back icon order as the Reference cell.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` overlap cell on the left and a labeled `Scene` grid of overlap cells on the right.
2. Supported `task_variant` values: one current scene variant, `same_front_to_back_order`.
3. Answer type: `answer_gt.type = integer`.
4. Evidence type: `evidence_gt.type = label_set` (sorted labels of the matching Scene cells).
5. Count policy: `target_count` is sampled independently from `0..6`, `distractor_count` is sampled independently from `1..6`, and `object_count = target_count + distractor_count` therefore ranges from `2..12`.
6. Asset policy: the Reference and all Scene cells reuse one sampled pair of curated Prism icons from `assets/icons/all_icons.txt`; only the front-to-back order changes between matches and distractors.
7. Occlusion policy: the Reference order is either `a_over_b` or `b_over_a`; matching cells use the same order id, while distractor cells use the opposite order id.
8. Styling policy: per cell, the two overlapping icons get distinct sampled tints from one background-safe palette and each visible pair must be Lab-separated by at least `80`; overlap ratios are sampled in the configured range (`0.40..0.60`), so the task depends on order rather than on one fixed color/offset template.
9. Noise policy: each icon instance (both icons in the Reference cell and both icons in every Scene cell) may receive `0..2` subtle Prism-style edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per icon in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_relation_v1`
2. `task_family_key`: `reference_grid_occlusion_relation`
3. `task_key`: `relation_query`
4. Answer+evidence JSON shape: `{"evidence":["B","E","G"],"answer":3}`
5. Answer-only JSON shape: `{"answer":3}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: the family stem establishes the Reference-vs-Scene grid layout; task wording asks only about matching front-to-back order, with “which icon is on top” clarified in the task question.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching cell set is sampled first, then the Scene grid is built from that same match trace; evidence labels are the sorted labels of those matching cells.
3. Reject/resample conditions: unsupported count config, missing curated icon assets, palette-separation failures, or overlap-grid render failures.
4. No-auto-relaxation guarantee: generation fails on unmet palette/asset/layout constraints instead of weakening the occlusion-order contract.
5. Semantic-unit rule: user-facing evidence stays at the cell-label level because the task asks about pair-level front/back ordering, not about boxing one icon within the overlap.
6. Trace style metadata records the sampled palette, overlap-ratio range, cell-grid styling, and the per-icon subtle-noise edits.
7. Balanced defaults: `resolve_counting_target_and_distractor_triplet(...)` balances both target and distractor counts across feasible support when `_sampling_index` is present.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + task variant.
2. Determinism/build tests: `tests/test_icons_relation_occlusion_order_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_relation_occlusion_order_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
