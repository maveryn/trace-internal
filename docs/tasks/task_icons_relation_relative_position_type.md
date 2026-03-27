# `task_icons_relation_relative_position_type`

## 1) Identity
1. Domain: `icons`
2. Task group: `relation`
3. Task id: `task_icons_relation_relative_position_type`
4. Objective: count how many Scene icons match the Reference icon's type and lie on one requested side of the marked Anchor icon.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` icon on the left and a `Scene` panel of icons on the right; exactly one Scene icon is marked as the `Anchor` with a visible outline and `Anchor` label.
2. Supported `task_variant` values: `left_of_anchor`, `right_of_anchor`, `above_anchor`, `below_anchor`.
3. Answer type: `answer_gt.type = integer`.
4. Evidence type: `evidence_gt.type = bbox_set` (scene-only boxes in final image pixel coordinates, sorted top-to-bottom then left-to-right).
5. Count policy: `target_count` is sampled from `0..5`, `distractor_count` is sampled from the feasible support `max(1, target_count + 1)..10`, and `object_count = target_count + distractor_count` therefore ranges from `1..15`; the Anchor icon is additional and is not counted in `object_count`.
6. Asset policy: reference, anchor, and scene icons are drawn from the curated Prism `assets/icons/all_icons.txt` pool copied into TRACE.
7. Match policy: scene matches share the Reference icon type and strictly satisfy the requested side relation to the Anchor bbox; distractors are mixed across both spatially matching and spatially non-matching cases so the scene cannot be solved from side occupancy alone. When `distractor_count >= 2`, generation guarantees at least one same-type distractor on the wrong side and at least one different-type distractor on the queried side.
8. Same-type distractor margin rule: same-type wrong-side distractors follow the Prism-style relaxed spatial rule — they must lie mostly outside the queried region, with at least `75%` of their bbox area on the non-target side, so near-miss same-type distractors do not visually look like positives.
9. Placement policy: scene icons are placed randomly under a stricter spatial overlap cap (`0.05` of the smaller icon box area), with directional clearance `anchor_gap_px_directional = 8` between candidate boxes and the Anchor bbox.
10. Anchor policy: the Anchor is sampled from a distinct icon type and placed so both the queried side and the opposite side retain sufficient usable area; the Anchor highlight bbox is recorded in trace metadata.
11. Noise policy: each icon instance (Reference, Anchor, and every Scene icon) may receive `0..2` subtle Prism-style edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per icon in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_relation_v1`
2. `task_family_key`: `reference_scene_anchor_relation`
3. `task_key`: `relation_query`
4. Answer+evidence JSON shape: `{"evidence":[[438,162,498,222],[602,302,670,370]],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: the family stem establishes the Reference-vs-Scene layout and the marked Anchor; task wording asks only about the requested directional relation to that Anchor.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching scene set is sampled first, then placed/rendered; evidence boxes are the rendered boxes of those same matches.
3. Reject/resample conditions: unsupported count config, missing curated assets, anchor-placement failures, or directional overlap-constrained placement failures.
4. No-auto-relaxation guarantee: generation fails on unmet spatial-capacity/asset/overlap constraints instead of weakening the Anchor relation contract.
5. Evidence scope: the user-facing `bbox_set` covers matching Scene icons only; the Reference and Anchor boxes stay in trace metadata.
6. Trace style metadata records the sampled icon palette, overlap/noise config, anchor highlight styling, and final per-instance `tint_rgb` assignments.
7. Balanced defaults: both task-variant selection and independent target/distractor counts use deterministic balancing when `_sampling_index` is present.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + task variant.
2. Determinism/build tests: `tests/test_icons_relation_relative_position_type_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_relation_relative_position_type_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
