# `task_icons__overlap_grid__occlusion_order_count`

## 1) Identity
1. Domain: `icons`
2. Scene id: `overlap_grid`
3. Scene: `relation`
4. Task id: `task_icons__overlap_grid__occlusion_order_count`
5. Objective: count how many labeled Scene cells show the same front-to-back icon order as the Reference cell.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` overlap cell on the left and a labeled `Scene` grid of overlap cells on the right.
2. Supported `query_id` value: `same_front_to_back_order`.
3. Answer type: `answer_gt.type = integer`.
4. Annotation type: `annotation_gt.type = bbox_set` (pixel-space boxes around the matching Scene cells, sorted top-to-bottom then left-to-right).
5. Count policy: `target_count` is sampled independently from `0..5`, `distractor_count` is sampled independently from `1..6`, and `object_count = target_count + distractor_count` is capped to the feasible `2..9` range.
6. Label policy: Scene grid labels are fixed row-major as `A..F`; generation randomizes overlap content, not label positions.
7. Asset policy: the Reference and all Scene cells reuse one sampled pair of curated icons from `assets/icons/all_icons.txt`; only the front-to-back order changes between matches and distractors.
8. Occlusion policy: the Reference order is either `a_over_b` or `b_over_a`; matching cells use the same order id, while distractor cells use the opposite order id.
9. Styling policy: per cell, the two overlapping icons get distinct sampled tints from one background-safe palette and each visible pair must be Lab-separated by at least `80`; overlap ratios are sampled in the configured range (`0.40..0.60`), so the task depends on order rather than on one fixed color/offset template.
10. Noise policy: each icon instance (both icons in the Reference cell and both icons in every Scene cell) may receive `0..2` subtle per-icon edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per icon in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_relation_v0`
2. `scene_key`: `reference_grid_occlusion_relation`
3. `task_key`: `relation_query`
4. Answer+annotation JSON shape: `{"annotation":[[336,104,506,274],[532,104,702,274],[728,104,898,274]],"answer":3}`
5. Answer-only JSON shape: `{"answer":3}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
7. Variant counts (scene/task/mode): exactly 5 templates per required key.
8. Prompt style: the scene stem establishes the Reference-vs-Scene grid layout; task wording asks only about matching front-to-back order, with “which icon is on top” clarified in the task question.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching cell set is sampled first, then the Scene grid and matching-cell annotation boxes are built from that same match trace.
3. Reject/resample conditions: unsupported count config, missing curated icon assets, palette-separation failures, or overlap-grid render failures.
4. No-auto-relaxation guarantee: generation fails on unmet palette/asset/layout constraints instead of weakening the occlusion-order contract.
5. Semantic-unit rule: user-facing annotation is a pixel-space box around each matching Scene cell because the task asks about pair-level front/back ordering, not about boxing one icon within the overlap; the matching labels remain private trace metadata.
6. Trace style metadata records the sampled palette, overlap-ratio range,
   cell-grid styling, text-legibility metadata for panel headers/cell labels,
   and the per-icon subtle-noise edits.
7. Balanced defaults: `resolve_counting_target_and_distractor_triplet(...)` balances target counts across `0..5` under the normal seeded sampler, then cycles distractor counts within the feasible support left by the selected target and the `2..9` total-cell cap.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + query branch.
2. Determinism/build tests: `tests/test_icons_relation_occlusion_order_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_relation_occlusion_order_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_scene_config.py`

## 6) Current review status
Current browser-review sidecars live under
`review/task-reviews/icons/overlap_grid/task_icons__overlap_grid__occlusion_order_count/`.
