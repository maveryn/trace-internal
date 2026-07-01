# `task_symbolic__clock__offset_readout`

## 1) Identity
1. Domain: `symbolic`
2. Scene id: `clock`
3. Scene: `clock`
4. Task id: `task_symbolic__clock__offset_readout`
5. Objective: read one analog clock and apply a minute offset.

## Program Contract
Program: `clock.offset_readout(scene=clock, scope=single_two_hand_clock, query=minutes_after|minutes_before, output=string_hhmm)`

Candidate set: the hour-hand and minute-hand segments on the single visible analog clock.
Operands: the displayed time, sampled minute offset, and offset direction.
Operation: read the displayed time and add or subtract the requested offset in 12-hour time.
Output binding: `answer` is the resulting time as zero-padded `HH:MM`.
Annotation witnesses: a two-item `segment_set` containing the hour and minute hand segments.
Query ids: `minutes_after`, `minutes_before`.

## 2) Scene + Task Contract
1. Public branch metadata: `query_id`
2. Supported public `query_id`: `minutes_after`, `minutes_before`
3. Supported non-semantic visual axes:
   - `scene_variant`: `classic|minimal|outline`
   - `style_variant`: `accented|marker|studio`
   - `accent_color_name`: shared symbolic clock colors
4. `answer_gt.type`: `string`
5. Answer schema: zero-padded 12-hour `HH:MM`.
6. `annotation_gt.type`: `segment_set`
7. Annotation schema: `segment_set`
8. Scene contract:
   - one two-hand analog clock is shown,
   - the answer is the displayed time plus or minus `delta_minutes`,
   - annotation marks the hour and minute hand segments only.

## 3) Prompt Contract
1. Bundle: `symbolic_clock_v1`
2. `scene_key`: `clock`
3. `task_key`: `clock_offset_readout_query`
4. Required slots:
   - scene: `object_description`
   - query: `delta_minutes`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_annotation`

## 4) Annotation + Trace Contract
1. Prompt-facing annotation is a two-item `segment_set`.
2. Segment endpoint order is not semantically meaningful.
3. `projected_annotation` includes `segment_set` and `pixel_segment_set`.
4. `render_map` includes the clock center, hand tips, hand bboxes, and face bbox.
5. `execution_trace` records shown time, offset direction, offset value, answer time, and resolved visual axes.

## 5) Determinism + Tests
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and annotation come from the finalized rendered clock geometry.
3. Behavior/trace/prompt tests: `tests/test_symbolic_clock_readout_tasks.py`
4. Contract/build tests: `tests/test_symbolic_clock_readout_contracts.py`
