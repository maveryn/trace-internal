# `task_symbolic__clock__elapsed_time_value`

## 1) Identity
1. Domain: `symbolic`
2. Scene id: `clock`
3. Scene: `clock`
4. Task id: `task_symbolic__clock__elapsed_time_value`
5. Objective: compute the forward elapsed minutes from clock A to clock B.

## Program Contract
Program: `clock.elapsed_time_value(scene=clock, scope=two_labeled_analog_clocks, output=integer_minutes)`

Candidate set: the two visible analog clock faces labeled `A` and `B`.
Operands: the displayed start time on clock `A` and displayed end time on clock `B`.
Operation: compute the forward elapsed time from `A` to `B` around the 12-hour clock.
Output binding: `answer` is the elapsed time in minutes as an integer.
Annotation witnesses: a `bbox_map` with `start_clock` and `end_clock` face bboxes.
Query ids: `single`.

## 2) Scene + Task Contract
1. Public branch metadata: `query_id`
2. Supported public `query_id`: `single`
3. Supported non-semantic visual axes:
   - `scene_variant`: `classic|minimal|outline`
   - `style_variant`: `accented|marker|studio`
   - `accent_color_name`: shared symbolic clock colors
4. `answer_gt.type`: `integer`
5. Answer schema: elapsed minutes as an integer.
6. `annotation_gt.type`: `bbox_map`
7. Annotation schema: `bbox_map` with roles `start_clock` and `end_clock`
8. Scene contract:
   - two labeled analog clocks are shown side by side,
   - clock A is the starting time and clock B is the ending time,
   - the prompt explicitly asks for the forward elapsed time around the 12-hour clock,
   - the configured elapsed-minute support excludes zero and full-cycle ambiguities.

## 3) Prompt Contract
1. Bundle: `symbolic_clock_v1`
2. `scene_key`: `clock`
3. `task_key`: `clock_elapsed_time_value_query`
4. Query prompt key: `elapsed_time_value`
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Modes: `answer_only`, `answer_and_annotation`

## 4) Annotation + Trace Contract
1. Prompt-facing annotation is a role-bound `bbox_map`.
2. `start_clock` marks the clock A face; `end_clock` marks the clock B face.
3. Clock labels and caption text are not prompt-facing annotation.
4. `projected_annotation` includes `bbox_map` and `pixel_bbox_map`.
5. `execution_trace` records both displayed times, elapsed minutes, and resolved visual axes.

## 5) Determinism + Tests
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and annotation come from the finalized rendered start/end clocks.
3. Behavior/trace/prompt tests: `tests/test_symbolic_clock_elapsed_sequence_tasks.py`
4. Scene-package migration tests: `tests/test_scene_package_migration_contracts.py`, `tests/test_scene_package_review_candidate_contracts.py`
