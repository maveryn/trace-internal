# `task_icons_relation_between_two_anchors_count`

## 1) Identity
1. Domain: `icons`
2. Task group: `relation`
3. Task id: `task_icons_relation_between_two_anchors_count`
4. Objective: count how many Scene icons have centers inside the strip between two marked anchors.

## 2) Scene + task contract
1. Entities/relations: one single-panel `Scene` image of free-placed icons; exactly two Scene icons are visibly marked as `Anchor A` and `Anchor B`.
2. Supported `task_variant` values: `inside_vertical_strip`, `inside_horizontal_strip`.
3. Answer type: `answer_gt.type = integer`.
4. Evidence type: `evidence_gt.type = bbox_set` (scene-only boxes in final image pixel coordinates, sorted top-to-bottom then left-to-right).
5. Count policy: `target_count` is sampled from `0..5`, `distractor_count` is sampled from `1..10`, and `object_count = target_count + distractor_count` therefore ranges from `1..15`; the two anchors are additional and are not counted in `object_count`.
6. Anchor policy: the two anchors always share the same icon type, tint, and rotation. For `inside_vertical_strip`, the anchor centers share the same `y`; for `inside_horizontal_strip`, the anchor centers share the same `x`.
7. Candidate policy: every non-anchor Scene icon uses a different icon type from the anchors, while tint and rotation may vary per icon.
8. Match policy: candidate membership is computed from icon-center coordinates only. `inside_vertical_strip` counts candidate centers whose `x` lies between the anchor centers; `inside_horizontal_strip` counts candidate centers whose `y` lies between the anchor centers.
9. Boundary-margin rule: every candidate center must stay at least `strip_boundary_margin_px = 14` away from the strip boundary, so positives and negatives never become near-threshold ambiguous cases.
10. Placement policy: Scene icons are placed randomly under a `0.08` smaller-area overlap cap, with both anchor highlight boxes treated as occupied regions during placement.
11. Noise/color policy: each icon instance (both anchors and every Scene icon) may receive `0..2` subtle Prism-style edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; colors come from one background-safe Lab-separated palette.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_relation_v1`
2. `task_family_key`: `scene_two_anchor_relation`
3. `task_key`: `relation_query`
4. Answer+evidence JSON shape: `{"evidence":[[312,180,372,240],[540,286,612,358]],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: the family stem establishes the single Scene panel plus the two marked anchors; task wording asks only about icon centers inside the requested vertical or horizontal strip and does not draw the strip itself.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching Scene set is sampled first, then rendered; evidence boxes are the rendered boxes of those same matches.
3. Reject/resample conditions: unsupported count config, missing curated assets, anchor-pair layout failures, or strip/overlap-constrained placement failures.
4. No-auto-relaxation guarantee: generation fails on unmet strip/asset/layout constraints instead of weakening the boundary margin or anchor alignment rule.
5. Evidence scope: the user-facing `bbox_set` covers matching Scene icons only; both anchor boxes stay in trace metadata.
6. Trace style metadata records the sampled palette, anchor styling, strip boundary margin, and per-instance subtle-noise edits.
7. Balanced defaults: task-variant selection and independent target/distractor counts use deterministic balancing when `_sampling_index` is present.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + task variant.
2. Determinism/build tests: `tests/test_icons_relation_between_two_anchors_count_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_relation_between_two_anchors_count_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
