# `task_icons_counting_size_relation`

## 1) Identity
1. Domain: `icons`
2. Task group: `counting`
3. Task id: `task_icons_counting_size_relation`
4. Objective: count how many scene icons are smaller or larger than the reference icon.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` icon on the left and `1..16` randomly placed scene icons on the right.
2. Supported `task_variant` values: `size_smaller`, `size_larger`.
3. Answer type: `answer_gt.type = integer`.
4. Evidence type: `evidence_gt.type = bbox_set` (scene-only boxes in final image pixel coordinates, sorted top-to-bottom then left-to-right).
5. Count policy: `target_count` is sampled independently from `0..8`, `distractor_count` is sampled independently from `1..8`, and `object_count = target_count + distractor_count` therefore ranges from `1..16`.
6. Asset policy: the reference icon is drawn from the curated `assets/icons/all_icons.txt` icon pool, and the scene keeps that same icon type throughout so the task isolates size relation instead of identity.
7. Size policy: the reference icon nominal size is sampled from `64..96` px, scene icon nominal sizes are sampled from `40..120` px, and every scene icon is forced to satisfy `|scene_size - reference_size| >= 12` px so there are no borderline same-size cases.
8. Match policy: `size_smaller` counts scene icons whose nominal size is at least `12` px smaller than the reference; `size_larger` counts scene icons whose nominal size is at least `12` px larger than the reference. Same-type distractors are forced into the opposite relation band.
9. Visual variation: scene icons keep the same icon type as the reference but randomize tint and rotation independently from the same per-instance palette/rotation support.
10. Placement policy: scene icons are placed randomly in the scene panel, and any pairwise overlap is capped at `10%` of the smaller icon box area.
11. Noise policy: each icon instance (reference + scene) may receive `0..2` subtle per-icon edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per instance in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_counting_v1`
2. `task_family_key`: `reference_scene_counting`
3. `task_key`: `counting_query`
4. Answer+evidence JSON shape: `{"evidence":[[318,148,370,200],[572,322,632,382]],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: the family stem establishes the `Reference` + `Scene` layout; task wording asks only about icons that are smaller or larger than the reference icon.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching size-relation set is sampled first, then rendered; evidence boxes are the rendered boxes of those same matches.
3. Reject/resample conditions: unsupported count config, missing curated asset ids, no feasible reference-size band, no feasible target/distractor size band for the selected relation, or overlap-constrained placement/render failures.
4. No-auto-relaxation guarantee: generation fails on unmet scene-capacity/asset/size/overlap constraints instead of weakening the size-relation contract.
5. Evidence scope: the user-facing `bbox_set` covers scene matches only; the reference icon bbox and nominal sizes are stored in trace metadata instead of the evidence payload.
6. Trace style metadata records the sampled icon palette, icon-noise config, task-local reference/scene size bands, and final per-instance nominal sizes/tints.
7. Balanced defaults: `resolve_counting_target_and_distractor_triplet(...)` balances both target and distractor counts across feasible support, and variant sampling cycles evenly across `smaller` / `larger` when `_sampling_index` is present.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + task variant.
2. Determinism/build tests: `tests/test_icons_counting_size_relation_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_counting_size_relation_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
