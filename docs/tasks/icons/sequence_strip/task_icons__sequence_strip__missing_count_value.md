# `task_icons__sequence_strip__missing_count_value`

## 1) Identity
1. Domain: `icons`
2. Scene id: `sequence_strip`
3. Scene: `sequence`
4. Task id: `task_icons__sequence_strip__missing_count_value`
5. Objective: infer how many icons should appear in one missing Scene box so the visible count sequence continues.

## 2) Scene + task contract
1. Entities/relations: one single-panel image with a horizontal row of `4..6` boxes; one box is missing and marked with `?`.
2. Branch metadata: `query_id`
3. Diagnostic `query_id`: `arithmetic_progression`.
4. Answer type: `answer_gt.type = integer`.
5. Annotation type: `annotation_gt.type = bbox_set` (exactly one box: the missing box in final image pixel coordinates).
6. Sequence policy: the hidden counts follow one arithmetic progression with integer step `±1..±3`; the missing answer is sampled from `0..10`, and every visible count stays in `0..10`.
7. Missing-position policy: the missing box may appear at any sequence position, including either end; default sampling cycles across feasible missing positions instead of favoring the leftmost box.
8. Asset policy: the shared sequence icon is drawn from the curated `assets/icons/all_icons.txt` icon pool, and every visible icon keeps that same icon type.
9. Visual variation: all visible icons keep the same tint within one instance, while icon rotation may vary independently across instances.
10. Size policy: visible icons are rendered at nominal sizes in `24..40` px.
11. Cell geometry policy: each instance samples one row box width in `112..160` px and one row box height in `96..144` px; the final canvas size is derived from that sampled row geometry instead of stretching boxes into a fixed global canvas.
12. Placement policy: icons are placed randomly within their own box, and any pairwise overlap inside one box is capped at `20%` of the smaller icon box area.
13. Noise policy: each rendered visible icon may receive `0..2` subtle per-icon edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; edits are recorded per instance in trace metadata.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_sequence_v0`
2. `scene_key`: `sequence_missing_count`
3. `task_key`: `missing_count_query`
4. Answer+annotation JSON shape: `{"annotation":[[540,126,654,458]],"answer":5}`
5. Answer-only JSON shape: `{"answer":5}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
7. Variant counts (scene/task/mode): exactly 5 templates per required key.
8. Prompt style: the scene stem establishes the sequence-row layout; task wording asks only for the missing count that continues the sequence.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the hidden count is sampled first from the configured support, then one feasible `(missing_index, step_delta)` combination is chosen so the full arithmetic progression is uniquely determined.
3. Reject/resample conditions: unsupported count/length/step config, missing curated assets, or per-cell placement failures under the overlap cap.
4. No-auto-relaxation guarantee: generation fails on unmet sequence/placement constraints instead of weakening the arithmetic rule or overlap threshold.
5. Annotation scope: the user-facing `bbox_set` contains only the missing box; the full sequence counts and visible per-cell icon placements stay in trace metadata.
6. Trace style metadata records the sampled single-tint palette, icon-noise config, sampled row box width/height, sequence-cell styling, panel text-legibility metadata, and final per-instance nominal sizes/rotations/noise edits.
7. Balanced defaults: seeded sampling balances the missing answer support `0..10`, row length support `4..6`, feasible missing positions, and arithmetic-step support.

## 5) Complexity + tests
1. Complexity definition/components: sequence length + missing answer + absolute step size.
2. Determinism/build tests: `tests/test_icons_sequence_missing_count_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_sequence_missing_count_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_scene_config.py`
