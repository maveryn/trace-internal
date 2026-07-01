# `task_symbolic__clock__alarm_wait_time_value`

## 1) Identity
1. Domain: `symbolic`
2. Scene id: `clock`
3. Scene: `clock`
4. Task id: `task_symbolic__clock__alarm_wait_time_value`
5. Objective: compute the forward wait time until an analog alarm-clock hour.

## Program Contract
Program: `clock.alarm_wait_time_value(scene=clock, scope=single_alarm_analog_clock, output=integer_minutes)`

Candidate set: the current hour-hand, current minute-hand, and red alarm-hand segments on the single visible analog clock.
Operands: the current time shown by the dark hands and the alarm hour shown by the red hand.
Operation: read the current time, interpret the red alarm hand on the same 1-12 hour scale as the numerals with alarm minute fixed at `:00`, and compute the forward minutes until the next alarm occurrence.
Output binding: `answer` is the wait time in minutes as an integer.
Annotation witnesses: a three-item `segment_set` containing the current hour hand, current minute hand, and red alarm hand.
Query ids: `single`.

## 2) Scene + Task Contract
1. Public branch metadata: `query_id`
2. Supported public `query_id`: `single`
3. Supported non-semantic visual axes:
   - `scene_variant`: `classic|minimal|outline`
   - `style_variant`: `accented|marker|studio`
   - `accent_color_name`: shared symbolic clock colors, with red-like accents disabled for this task
4. `answer_gt.type`: `integer`
5. Answer schema: forward wait time in minutes, `1..720`.
6. `annotation_gt.type`: `segment_set`
7. Annotation schema: `segment_set`
8. Scene contract:
   - one analog clock is shown,
   - dark hour and minute hands show the current time,
   - the red alarm hand is a distinct semantic hand and points to an hour numeral on the 1-12 hour scale,
   - the alarm minute is fixed at `:00`,
   - current hands and the red alarm hand are separated by configured angle-gap constraints,
   - annotation marks the current hour hand, current minute hand, and red alarm hand segments.

## 3) Prompt Contract
1. Bundle: `symbolic_clock_v1`
2. `scene_key`: `clock`
3. `task_key`: `clock_alarm_wait_time_value_query`
4. Query prompt key: `alarm_wait_time_value`
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Modes: `answer_only`, `answer_and_annotation`

## 4) Annotation + Trace Contract
1. Prompt-facing annotation is a three-item `segment_set`.
2. Segment endpoint order is not semantically meaningful.
3. `projected_annotation` includes `segment_set` and `pixel_segment_set`.
4. `render_map` includes the clock center, current-hand tips, alarm-hand tip, hand bboxes, and face bbox.
5. `execution_trace` records shown time, alarm hour, alarm time text, wait minutes, hand angle gaps, and resolved visual axes.

## 5) Determinism + Tests
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and annotation come from the finalized rendered clock geometry.
3. Behavior/trace/prompt tests: `tests/test_symbolic_clock_readout_tasks.py`
4. Contract/build tests: `tests/test_symbolic_clock_readout_contracts.py`
