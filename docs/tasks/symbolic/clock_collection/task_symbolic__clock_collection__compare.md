# `task_symbolic__clock_collection__compare`

## 1) Identity
1. Domain: `symbolic`
2. Scene id: `clock_collection`
3. Source scene: `clock`
4. Task id: `task_symbolic__clock_collection__compare`
5. Objective: compare several labeled analog clocks and identify the one showing the earliest or latest time.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: `earliest_time_label` or `latest_time_label`
3. Supported semantic parameter axes:
   - `extremum_direction`: `earliest|latest`
4. Supported `scene_variant` values:
   - `classic`
   - `minimal`
   - `outline`
5. Supported non-semantic visual axes:
   - `style_variant`: `studio|accented|marker`
   - `accent_color_name`: sampled from the shared named-color palette
6. `answer_gt.type`: `string`
7. `annotation_gt.type`: `bbox_set`
8. Scene contract:
   - `6..12` labeled analog 12-hour clocks per image,
   - visible labels are sampled from the global pool `A..L`,
   - clocks are arranged in a centered grid with at most four clocks per row and at most three rows,
   - no seconds hands,
   - visible hour numerals `1..12`,
   - shown minutes stay on a 5-minute grid in v0,
   - all shown times are distinct,
   - the winning earliest/latest clock is unique by construction,
   - the winning clock differs from the nearest competing clock by at least the configured comparison gap,
   - the visible winner label is sampled from the full label pool before the remaining visible labels are chosen, so answer support stays broad even when the image shows fewer than nine clocks.
9. Query contract:
   - the task asks which labeled clock shows the requested `extremum_direction` time,
   - prompt-facing answers are always one clock label such as `B`.

## 3) Prompt contract
1. Bundle: `symbolic_clock_v0`
2. `scene_key`: `multi_analog_clock`
3. `task_key`: `clock_compare_query`
4. Internal `query_key`: `time_extremum_label`
5. Required query-id slot: `extremum_direction`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
7. Slot source:
   - prompt config in `configs/domains/symbolic/clock.yaml`,
   - deterministic bundle selection from `prompts/symbolic/clock/symbolic_clock_v0.json`,
   - variant-conditioned prompt JSON examples generated in task code so the example answer matches the active compare query.
8. Modes: `answer_only`, `answer_and_annotation`
9. Prompt-facing annotation always names exactly one selected clock-face bbox.

## 4) Annotation + trace contract
1. Prompt-facing annotation is a one-item `bbox_set`:
   - selected clock-face bbox.
2. `projected_annotation` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - one `clock_face` entity per labeled clock,
   - one `clock_hand` entity for each hour hand,
   - one `clock_hand` entity for each minute hand.
4. `render_map` includes:
   - `scene_bbox_px`
   - `clocks_by_label`
   - `winning_label`
   - `winning_clock_bbox_px`
5. `execution_trace` records:
   - `query_id`
   - `extremum_direction`
   - `scene_variant`
   - `style_variant`
   - `accent_color_name`
   - `clock_count`
   - `clock_label_pool`
   - `clock_labels`
   - `shown_total_minutes_by_label`
   - `shown_time_text_by_label`
   - `winner_label`
   - `winner_total_minutes`
   - the active support ranges and minimum comparison-gap threshold

## 5) Visual policy
1. Background uses the shared puzzle panel-style defaults, and post-image noise uses the standard compare-scene default `apply_prob=0.5`.
2. The three `scene_variant` values change only the visible clock chrome.
3. The `style_variant` + `accent_color_name` axes add extra non-semantic color and bezel/tick variety while keeping the prompt unchanged.
4. The face bbox, not the whole row or both hands, is the prompt-facing witness because the answer asks for the winning labeled clock itself.
5. All clock numerals and visible clock labels use one deterministic font family sampled from the readout font pool and recorded in `render_spec.clock_style.font`.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. The public sampling unit is the task id; `extremum_direction`, `scene_variant`, `style_variant`, and `accent_color_name` are sampled internally.
3. Answers and annotation come from the same finalized set of shown times.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - empty feasible shown-time support after applying the hand-gap filter,
   - too few feasible later/earlier times to realize the sampled visible clock count under the minimum comparison gap,
   - non-unique visible clock labels.

## 7) Complexity + tests
1. Complexity definition/components: `time_reading`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_temporal_clock_compare_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_temporal_clock_compare_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_scene_config.py`
