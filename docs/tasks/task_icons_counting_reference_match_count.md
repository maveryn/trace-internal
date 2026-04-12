# `task_icons_counting_reference_match_count`

## 1) Identity
1. Domain: `icons`
2. Task group: `counting`
3. Task id: `task_icons_counting_reference_match_count`
4. Objective: count how many Scene icons match the Reference icon under one selected predicate.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` icon on the left and `1..20` randomly placed Scene icons on the right.
2. Supported `task_variant` values: `match_type|match_color|match_orientation|match_attribute_binding`.
3. Supported `scene_variant` values: `reference_scene`.
4. Answer type: `answer_gt.type = integer`.
5. Evidence type: `evidence_gt.type = bbox_set` (Scene-only boxes in final image coordinates, sorted top-to-bottom then left-to-right).
6. Count policy: `target_count` is sampled independently from `0..10`, `distractor_count` from `1..10`, and `object_count = target_count + distractor_count` therefore ranges from `1..20`.
7. Asset policy:
   - `match_type|match_color` use the curated `all_icons.txt` icon pool.
   - `match_orientation|match_attribute_binding` use the asymmetric `non_symmetry.txt` pool so rotation stays meaningful.
8. Match policy:
   - `match_type`: Scene icons match only on `icon_id`.
   - `match_color`: Scene icons share one icon type and match only on `tint_rgb`.
   - `match_orientation`: Scene icons share one icon type and match only on `rotation_degrees`.
   - `match_attribute_binding`: Scene icons match jointly on `icon_id + tint_rgb + rotation_degrees`, with distractors biased toward structured partial matches.
9. Placement policy: Scene icons are placed randomly in the Scene panel, and any pairwise overlap is capped at `10%` of the smaller icon box area.
10. Noise policy: every icon instance may receive `0..2` subtle per-icon edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; those edits stay recorded per instance in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_counting_v1`
2. `task_family_key`: `reference_scene_counting`
3. `task_key`: `counting_query`
4. Answer+evidence JSON shape: `{"evidence":[[322,152,377,207],[756,318,820,382]],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt style: the family stem establishes the `Reference` + `Scene` layout; variant wording names only the active matching predicate.

## 4) Determinism + constraints
1. Seed namespaces used: one variant-selection RNG via `spawn_rng(instance_seed, "task_icons_counting_reference_match_count.task_variant")`, then the delegated legacy scene RNG.
2. Unique-answer policy: the matching Scene set is sampled first inside the legacy generator, then rendered; evidence boxes are the rendered boxes of those same matches.
3. Reject/resample conditions: unsupported count config, missing curated asset ids, no feasible distractor palette/rotation choice for the selected predicate, or overlap-constrained placement/render failures.
4. No-auto-relaxation guarantee: generation fails on unmet scene-capacity/asset/predicate constraints instead of weakening the selected match rule.
5. Consolidation policy: the wrapper preserves the legacy generator internals underneath but rewrites `scene_variant`, `task_variant`, prompt metadata, and `legacy_task_id` / `legacy_task_variant` trace slots to the broader consolidated surface.

## 5) Complexity + tests
1. Complexity definition/components: the delegated legacy complexity is preserved per predicate, so `match_attribute_binding` remains harder than the simpler single-attribute variants under matched counts.
2. Determinism/build tests: `tests/test_icons_counting_reference_match_count_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_counting_reference_match_count_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
