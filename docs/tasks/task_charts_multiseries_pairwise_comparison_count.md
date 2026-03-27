# `task_charts_multiseries_pairwise_comparison_count`

## 1) Identity
1. Domain: `charts`
2. Task group: `multiseries`
3. Task id: `task_charts_multiseries_pairwise_comparison_count`
4. Objective: count how many category labels satisfy a pairwise comparison between two queried series in one multiseries chart.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `series_a_gt_b_count`
   - `series_a_lt_b_count`
2. Supported `scene_variant` values:
   - `grouped_bar`
   - `multi_line`
   - `grouped_dot_plot`
   - `grouped_lollipop`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_set`
5. Scene contract:
   - one multiseries chart per image,
   - total `series_count` is `2..3` in v1,
   - total `category_count` is `5..10` in v1,
   - every category has one visible unique uppercase label,
   - every series has one visible legend label on the right,
   - one queried pair of series is named in the prompt,
   - an optional third series can act as a distractor.
6. Generation guarantees:
   - the queried series pair is always distinct,
   - the queried series values are never tied within a category,
   - the answer count is target-balanced over the default support `0..8`,
   - `series_a_gt_b_count` uses strict `>`,
   - `series_a_lt_b_count` uses strict `<`.

## 3) Prompt contract
1. Bundle: `charts_multiseries_v1`
2. `task_family_key`: `multiseries_chart_comparison`
3. `task_key`: `pairwise_comparison_count_query`
4. `task_variant_key`: one of `series_a_gt_b_count|series_a_lt_b_count`
5. Required slots:
   - task-family: `object_description`
   - task layer: `left_series`, `right_series`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/multiseries.yaml`,
   - deterministic bundle selection from `prompts/charts/multiseries/charts_multiseries_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. Prompt-facing evidence is the deterministic `label_set` of category labels where the queried pairwise series comparison holds.
2. `projected_evidence` includes:
   - `label_set`
   - `pixel_point_map`
   - `pixel_point_set`
   - `bbox_set`
3. `scene_ir.entities` stores one entity per visible mark with:
   - `category_label`
   - `series_label`
   - integer `value`
   - category/series rank
   - rendered mark pixel geometry
   - enclosing category-group pixel geometry
4. `execution_trace` records:
   - `series_labels`
   - `category_labels`
   - `queried_series_labels`
   - nested `values_by_category`
   - target-answer range and chosen target answer
   - evidence labels

## 5) Visual policy
1. `grouped_bar` uses grouped vertical bars per category.
2. `multi_line` uses one colored line per series with visible point markers at each category.
3. `grouped_dot_plot` uses grouped colored points per category without connecting lines.
4. `grouped_lollipop` uses grouped colored lollipop stems/points per category.
5. Every multiseries chart reserves a right-side legend for the series labels/colors.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated multiseries value table.
4. No semantic auto-relaxation.
5. Empty evidence is valid when the target answer is `0`.
