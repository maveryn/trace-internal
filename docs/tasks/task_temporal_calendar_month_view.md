# `task_temporal_calendar_month_view`

## 1) Identity
1. Domain: `temporal`
2. Task group: `calendar`
3. Task id: `task_temporal_calendar_month_view`
4. Objective: answer numeric month-calendar questions from one single-month calendar view.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `date_of_weekday_occurrence`
   - `count_marked_weekend_days`
   - `days_between_marked_dates`
2. Supported `scene_variant` values:
   - `classic`
   - `minimal`
   - `outline`
3. Supported non-semantic visual axes:
   - `style_variant`: `studio|accented|marker`
   - `accent_color_name`: sampled from the shared named-color palette
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - one Gregorian month-view calendar per image,
   - one sampled real month/year in the configured support,
   - weekday headers are Monday-first (`Mon..Sun`),
   - the calendar may render `4`, `5`, or `6` visible week rows depending on the sampled month,
   - empty spillover cells may appear before day `1` or after the last day of the month,
   - marked dates appear only for the marked-date variants,
   - prompt-facing evidence is always built from valid date-cell bboxes, never from headers or decorative chrome.
7. Query contract:
   - `date_of_weekday_occurrence` asks for the date number of one requested nth weekday in the month,
   - `count_marked_weekend_days` asks how many marked dates fall on Saturday or Sunday,
   - `days_between_marked_dates` asks for the absolute day difference between the two marked dates.

## 3) Prompt contract
1. Bundle: `temporal_calendar_v1`
2. `task_family_key`: `month_calendar`
3. `task_key`: `calendar_month_query`
4. `task_variant_key`: `date_of_weekday_occurrence|count_marked_weekend_days|days_between_marked_dates`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `ordinal`, `weekday_name` for `date_of_weekday_occurrence`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/temporal/calendar.yaml`,
   - deterministic bundle selection from `prompts/temporal/calendar/temporal_calendar_v1.json`,
   - variant-conditioned prompt JSON examples generated in task code so the example answer/evidence shape matches the active calendar question.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is always one integer, while prompt-facing evidence always names one or more relevant date-cell bboxes.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` over date cells:
   - exactly one date-cell bbox for `date_of_weekday_occurrence`,
   - the marked weekend date-cell bboxes for `count_marked_weekend_days`,
   - exactly two marked date-cell bboxes for `days_between_marked_dates`.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - one `calendar_date_cell` entity per valid day in the month.
4. `render_map` includes:
   - `scene_bbox_px`
   - `calendar_title_text`
   - `date_cells_by_day`
   - `marked_dates`
   - `evidence_dates`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `style_variant`
   - `accent_color_name`
   - `year`
   - `month`
   - `month_name`
   - `days_in_month`
   - `start_weekday_index`
   - `row_count`
   - `marked_dates`
   - `evidence_dates`
   - `answer_value`
   - any active query-specific metadata such as `query_weekday_index`, `query_occurrence`, or `target_day_gap`

## 5) Visual policy
1. Background and post-image noise use the merged temporal-domain visual defaults from `configs/domains/temporal/base.yaml`.
2. `classic`, `minimal`, and `outline` vary the panel/grid chrome only; they do not change calendar semantics.
3. `style_variant` + `accent_color_name` add non-semantic month-view diversity through panel/header/marker styling while keeping the same answer/evidence contract.
4. Date-cell bboxes, not full rows or title/header regions, stay as the prompt-facing witness because every current variant reasons over specific day cells.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `task_variant`, `scene_variant`, `style_variant`, and `accent_color_name` are sampled independently at the policy level.
3. Answers and evidence come from the same finalized month metadata and date-cell geometry.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - empty feasible nth-weekday support for the sampled month,
   - empty feasible marked-weekend or weekday-distractor support for the sampled month,
   - empty feasible day-gap support for the sampled month.

## 7) Complexity + tests
1. Complexity definition/components: `calendar_lookup`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_temporal_calendar_month_view_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_temporal_calendar_month_view_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
