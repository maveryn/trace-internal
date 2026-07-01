# `task_symbolic__clock__full_time_readout`

## 1) Identity
1. Domain: `symbolic`
2. Scene id: `clock`
3. Scene: `clock`
4. Task id: `task_symbolic__clock__full_time_readout`
5. Objective: read the exact time from one three-hand analog clock.

## Program Contract
Program: `clock.full_time_readout(scene=clock, scope=single_three_hand_analog_clock, output=string_hhmmss)`

Candidate set: the hour-hand, minute-hand, and second-hand segments on the single visible analog clock.
Operands: the finalized clock center and the three hand-tip positions.
Operation: read the displayed hour, minute, and second values from the analog clock.
Output binding: `answer` is the displayed time as zero-padded `HH:MM:SS`.
Annotation witnesses: a three-item `segment_set` containing the hour, minute, and second hand segments.
Query ids: `single`.

## 2) Scene + Task Contract
1. Public branch metadata: `query_id`
2. Supported public `query_id`: `single`
3. Supported non-semantic visual axes:
   - `scene_variant`: `classic|minimal|outline`
   - `style_variant`: `accented|marker|studio`
   - `accent_color_name`: shared symbolic clock colors
4. `answer_gt.type`: `string`
5. Answer schema: zero-padded 12-hour `HH:MM:SS`.
6. `annotation_gt.type`: `segment_set`
7. Annotation schema: `segment_set`
8. Scene contract:
   - one three-hand analog clock is shown,
   - the answer is the exact displayed hour, minute, and second time,
   - sampled times are constrained so the three hands are separated by at least the configured angle gap,
   - annotation marks the hour, minute, and second hand segments only.

## 3) Prompt Contract
1. Bundle: `symbolic_clock_v1`
2. `scene_key`: `clock`
3. `task_key`: `clock_full_time_readout_query`
4. Query prompt key: `full_time_readout`
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Modes: `answer_only`, `answer_and_annotation`

## 4) Annotation + Trace Contract
1. Prompt-facing annotation is a three-item `segment_set`.
2. Segment endpoint order is not semantically meaningful.
3. `projected_annotation` includes `segment_set` and `pixel_segment_set`.
4. `render_map` includes the clock center, hand tips, hand bboxes, and face bbox.
5. `execution_trace` records the displayed time, hand angle gaps, second support, and resolved visual axes.

## 5) Determinism + Tests
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and annotation come from the finalized rendered clock geometry.
3. Behavior/trace/prompt tests: `tests/test_symbolic_clock_readout_tasks.py`
4. Contract/build tests: `tests/test_symbolic_clock_readout_contracts.py`
