# `task_icons__two_anchor__between_anchors_count`

## 1) Identity
1. Domain: `icons`
2. Scene id: `two_anchor`
3. Scene: `relation`
4. Task id: `task_icons__two_anchor__between_anchors_count`
5. Objective: count how many Scene icons have centers inside the strip between two marked anchors.

## 2) Scene + task contract
1. Entities/relations: one single-panel image of free-placed icons; exactly two Scene icons are visibly marked as `Anchor A` and `Anchor B`.
2. Supported `query_id` values: `single`.
3. Supported semantic parameter axis: `strip_axis=vertical|horizontal`.
4. Answer type: `answer_gt.type = integer`.
5. Annotation type: `annotation_gt.type = bbox_set` (scene-only boxes in final image pixel coordinates, sorted top-to-bottom then left-to-right).
6. Count policy: `target_count` is sampled from `0..5`, `distractor_count` is sampled from `1..10`, and `object_count = target_count + distractor_count` therefore ranges from `1..15`; the two anchors are additional and are not counted in `object_count`.
7. Anchor policy: the two anchors always share the same icon type, tint, and rotation. For `strip_axis=vertical`, the anchor centers share the same `y`; for `strip_axis=horizontal`, the anchor centers share the same `x`.
8. Candidate policy: every non-anchor Scene icon uses a different icon type from the anchors, while tint and rotation may vary per icon.
9. Match policy: candidate membership is computed from icon-center coordinates only. `strip_axis=vertical` counts candidate centers whose `x` lies between the anchor centers; `strip_axis=horizontal` counts candidate centers whose `y` lies between the anchor centers.
10. Boundary-margin rule: every candidate center must stay at least `strip_boundary_margin_px = 14` away from the strip boundary, so positives and negatives never become near-threshold ambiguous cases.
11. Placement policy: Scene icons are placed randomly under a `0.08` smaller-area overlap cap, with both anchor highlight boxes treated as occupied regions during placement.
12. Noise/color policy: each icon instance (both anchors and every Scene icon) may receive `0..2` subtle per-icon edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; colors come from one background-safe Lab-separated palette.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_relation_v0`
2. `scene_key`: `scene_two_anchor_relation`
3. `task_key`: `relation_query`
4. Answer+annotation JSON shape: `{"annotation":[[312,180,372,240],[540,286,612,358]],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
7. Variant counts (scene/task/mode): exactly 5 templates per required key.
8. Prompt style: the scene stem establishes the single panel plus the two icons marked A and B; task wording asks only about other icon centers inside the requested vertical or horizontal strip.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching Scene set is sampled first, then rendered; annotation boxes are the rendered boxes of those same matches.
3. Reject/resample conditions: unsupported count config, missing curated assets, anchor-pair layout failures, or strip/overlap-constrained placement failures.
4. No-auto-relaxation guarantee: generation fails on unmet strip/asset/layout constraints instead of weakening the boundary margin or anchor alignment rule.
5. Annotation scope: the user-facing `bbox_set` covers matching Scene icons only; both anchor boxes stay in trace metadata.
6. Trace style metadata records the sampled palette, anchor styling, strip boundary margin, panel text-legibility metadata, anchor-label text draw records, and per-instance subtle-noise edits.
7. Balanced defaults: seeded sampling balances the vertical/horizontal strip axis and target-count support using the same generator used for normal dataset generation.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + query branch.
2. Determinism/build tests: `tests/test_icons_relation_between_two_anchors_count_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_relation_between_two_anchors_count_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_scene_config.py`
