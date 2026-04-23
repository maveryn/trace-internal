# `task_charts_composition_subset_value`

## 1) Identity
1. Domain: `charts`
2. Task group: `composition`
3. Task id: `task_charts_composition_subset_value`
4. Objective: answer one integer stacked-composition arithmetic query that requires multiple legend/category lookups plus aggregation.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `category_subset_sum`
   - `series_across_categories_sum`
   - `subset_margin_sum`
2. Supported `scene_variant` values:
   - `stacked_bar`
   - `stacked_horizontal_bar`
3. Compatibility:
   - all supported `task_variant` values are valid on both stacked scene variants
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `integer_list`
6. Scene contract:
   - stacked scenes render one stack per category with one legend label per segment color,
   - stacked scenes print the integer segment values inside the segments and omit numeric axis tick labels,
   - both stacked scenes use a right-side legend that maps each color to one visible series label.
7. Generation guarantees:
   - stacked scenes use `6..9` categories and `5..7` series by default,
   - all segment values are positive integers in the default support `4..18`,
   - `category_subset_sum` queries one category and `3..4` legend labels,
   - `series_across_categories_sum` queries one legend label and `3..4` categories,
   - `subset_margin_sum` compares two disjoint legend subsets of size `2..3` across all categories and sums only the positive per-category margins.

## 3) Prompt contract
1. Bundle: `charts_composition_v2`
2. `task_family_key`: `composition_chart_value`
3. `task_key`: `stacked_composition_query`
4. `task_variant_key`: one of `category_subset_sum|series_across_categories_sum|subset_margin_sum`
5. Required slots:
   - task-family: `object_description`
   - task-variant `category_subset_sum`: `query_category_label`, `query_series_subset_labels`
   - task-variant `series_across_categories_sum`: `query_series_label`, `query_category_subset_labels`
   - task-variant `subset_margin_sum`: `left_series_subset_labels`, `right_series_subset_labels`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/composition.yaml`,
   - deterministic bundle selection from `prompts/charts/composition/charts_composition_v2.json`.
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. Prompt-facing evidence is an ordered `integer_list`.
2. Evidence semantics:
   - `category_subset_sum`: the selected segment values in legend order for the queried stack,
   - `series_across_categories_sum`: the selected segment values in category order for the queried legend label,
   - `subset_margin_sum`: the per-category margins `sum(left subset) - sum(right subset)` in category order.
3. `projected_evidence` includes:
   - `integer_list`
   - `pixel_point_set`
   - `bbox_set`
4. `scene_ir.entities` stores one entity per stack segment with visible category label, series label, integer value, and rendered pixel geometry.
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - category labels and series labels,
   - queried category / category-subset / series / legend-subset labels,
   - `values_by_category`,
   - evidence values and answer value.

## 5) Visual policy
1. Background and post-image noise use the merged charts-domain visual defaults from `configs/domains/charts/base.yaml`.
2. Stacked scenes use a clean axis scaffold plus a right-side legend.
3. Stacked scenes sample one distinct color per series and reuse it across all stacks.
4. All sampled colors remain visually separated from the white/light chart background and are recorded in trace/render metadata.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated stacked value table.
4. No semantic auto-relaxation.
