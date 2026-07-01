# `task_symbolic__clock__hand_angle_value`

## 1) Identity
1. Domain: `symbolic`
2. Scene id: `clock`
3. Scene: `clock`
4. Task id: `task_symbolic__clock__hand_angle_value`
5. Objective: compute the smaller angle between the two hands on one analog clock.

## Program Contract
Program: `clock.hand_angle_value(scene=clock, scope=single_two_hand_analog_clock, output=integer_degrees)`

Candidate set: the hour-hand and minute-hand segments on the single visible analog clock.
Operands: the finalized clock center and both hand-tip positions.
Operation: compute the smaller angle between the two hand segments.
Output binding: `answer` is the smaller angle in degrees as an integer.
Annotation witnesses: a two-item `segment_set` containing the hour and minute hand segments.
Query ids: `single`.

## 2) Scene + Task Contract
1. Public branch metadata: `query_id`
2. Supported public `query_id`: `single`
3. Supported non-semantic visual axes:
   - `scene_variant`: `classic|minimal|outline`
   - `style_variant`: `accented|marker|studio`
   - `accent_color_name`: shared symbolic clock colors
4. `answer_gt.type`: `integer`
5. Answer schema: smaller hand-to-hand angle in degrees.
6. `annotation_gt.type`: `segment_set`
7. Annotation schema: `segment_set`
8. Scene contract:
   - one two-hand analog clock is shown,
   - the answer is the smaller angle between the hour and minute hands,
   - sampled times are constrained so the answer is an integer number of degrees,
   - annotation marks the hour and minute hand segments only.

## 3) Prompt Contract
1. Bundle: `symbolic_clock_v1`
2. `scene_key`: `clock`
3. `task_key`: `clock_hand_angle_value_query`
4. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_annotation`

## 4) Annotation + Trace Contract
1. Prompt-facing annotation is a two-item `segment_set`.
2. Segment endpoint order is not semantically meaningful.
3. `projected_annotation` includes `segment_set` and `pixel_segment_set`.
4. `render_map` includes the clock center, hand tips, hand bboxes, and face bbox.
5. `execution_trace` records the shown time, smaller angle, and resolved visual axes.

## 5) Determinism + Tests
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and annotation come from the finalized rendered clock geometry.
3. Behavior/trace/prompt tests: `tests/test_symbolic_clock_readout_tasks.py`
4. Contract/build tests: `tests/test_symbolic_clock_readout_contracts.py`
