# `task_charts_trend_structure_value`

## 1) Identity
1. Domain: `charts`
2. Task group: `trend`
3. Task id: `task_charts_trend_structure_value`
4. Objective: compute one ordered-sequence trend statistic from a labeled single-series chart.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `peak_count`
   - `trough_count`
   - `longest_increasing_streak`
   - `longest_decreasing_streak`
2. Supported `scene_variant` values:
   - `area`
   - `bar`
   - `horizontal_bar`
   - `line`
   - `dot_plot`
   - `lollipop`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_set`
5. Scene contract:
   - one ordered single-series chart per image,
   - every visible mark has one unique uppercase label,
   - the chart is read in displayed order,
   - `line`, `area`, `dot_plot`, and `lollipop` use left-to-right point order,
   - `bar` uses left-to-right bar order,
   - `horizontal_bar` uses top-to-bottom bar order,
   - axis-based chart values are integers in the default range `1..20`.
6. Generation guarantees:
   - charts use `6..10` labeled marks by default,
   - adjacent values are always different, so every step is strictly increasing or strictly decreasing,
   - answers are target-balanced over the feasible support for the selected variant,
   - streak variants always have one unique winning streak by construction,
   - streak length counts labels, not gaps or segments.

## 3) Prompt contract
1. Bundle: `charts_trend_v1`
2. `task_family_key`: `ordered_chart_trend`
3. `task_key`: `structure_value_query`
4. `task_variant_key`: one of `peak_count|trough_count|longest_increasing_streak|longest_decreasing_streak`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/trend.yaml`,
   - deterministic bundle selection from `prompts/charts/trend/charts_trend_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. Prompt-facing evidence is the deterministic `label_set` witnessing the requested trend structure.
2. Evidence semantics:
   - `peak_count`: labels of all local peaks,
   - `trough_count`: labels of all local troughs,
   - `longest_increasing_streak`: labels in the unique longest strictly increasing streak,
   - `longest_decreasing_streak`: labels in the unique longest strictly decreasing streak.
3. `projected_evidence` includes:
   - `label_set`
   - `pixel_point_map`
   - `pixel_point_set`
   - `bbox_set`
4. `execution_trace` records:
   - ordered labels and values,
   - the step directions between consecutive labels,
   - evidence labels,
   - ordered evidence labels in chart order,
   - evidence point indices,
   - target-answer range and chosen target answer.

## 5) Visual policy
1. Background and post-image noise use the merged charts-domain visual defaults from `configs/domains/charts/base.yaml`.
2. V1 trend charts use clean light solid backgrounds only.
3. `line` and `area` keep visible point markers so turning points and streaks stay anchored to discrete labels.
4. `dot_plot` and `lollipop` keep one discrete point per label in left-to-right order.
5. `horizontal_bar` uses top-to-bottom order and states that ordering in the prompt-facing chart description.
6. Axis-based variants sample one chart color per instance and keep it consistent across the rendered marks.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same ordered value table.
4. No semantic auto-relaxation.
5. Empty evidence is valid for `peak_count` or `trough_count` when the answer is `0`.
