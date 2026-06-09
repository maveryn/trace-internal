# `task_icons__single_transform_options__geometric_transform_result_label`

## 1) Identity
1. Domain: `icons`
2. Scene id: `single_transform_options`
3. Task group: `transformation`
4. Task id: `task_icons__single_transform_options__geometric_transform_result_label`
5. Objective: select the labeled option that shows a Reference icon after one geometric transform.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a Reference icon and transform cue on the left, plus six labeled result options `A..F` on the right.
2. Supported `query_id` values:
   - `rotate_90_clockwise_result_label`
   - `rotate_90_counterclockwise_result_label`
   - `rotate_180_result_label`
   - `flip_horizontal_result_label`
   - `flip_vertical_result_label`
3. Answer type: `answer_gt.type = option_letter`.
4. Annotation type: `annotation_gt.type = keyed_bbox_map` with `reference_icon` and `selected_option`.
5. Option policy: the options are the identity result plus the five supported non-identity transforms of the same curated icon. Exactly one option matches the queried transform.
6. Asset policy: generation samples only from `assets/icons/non_symmetry.txt` and rejects icons whose identity/rotation/flip signatures collapse.
7. Distractor policy: distractors are the other five transform results of the same Reference icon; color, size, diagonal flips, and compound transforms are not task variants.
8. Styling policy: all options share one tint within an instance so the answer depends on geometric transformation rather than color or size.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_transformation_v0`
2. `scene_key`: `single_transform_options_transformation`
3. `task_key`: `transformation_query`
4. Answer+annotation JSON shape: `{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}`
5. Answer-only JSON shape: `{"answer":"C"}`
6. Prompt style: the question names the requested transform and asks for the labeled option. Curated icon ids are never shown.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`, plus per-icon noise namespaces.
2. Unique-answer policy: the target transform is inserted exactly once, and all six option transform signatures must be distinct for the sampled icon.
3. Reject/resample conditions: unsupported option count, unsupported query id, empty icon pool, palette-separation failures, or visually collapsed transform signatures.
4. Semantic-unit rule: keyed annotation binds the Reference icon to the selected visual option cell because the task is a role-bound option-image match.
5. Trace metadata records the sampled icon id, target transform id, option transform ids by label, visible operation cue, palette/style metadata, text-legibility metadata, and per-icon noise edits.

## 5) Complexity + tests
1. Complexity definition/components: fixed six-option scan load, transform rule load, signature ambiguity floor, and option-cell clutter.
2. Behavior/trace/prompt tests: `tests/test_icons_transformation_single_transform_options_tasks.py`
3. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_icons_task_group_config.py`
