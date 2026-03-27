# `task_charts_composition_subset_value`

## 1) Identity
1. Domain: `charts`
2. Task group: `composition`
3. Task id: `task_charts_composition_subset_value`
4. Objective: answer one integer composition query over stacked or pie-style chart parts.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `stack_total_at_label`
   - `stack_segment_value`
   - `combined_share_subset`
2. Supported `scene_variant` values:
   - `stacked_bar`
   - `stacked_horizontal_bar`
   - `pie`
   - `donut`
3. Compatibility:
   - `stack_total_at_label` -> `stacked_bar|stacked_horizontal_bar`
   - `stack_segment_value` -> `stacked_bar|stacked_horizontal_bar`
   - `combined_share_subset` -> `pie|donut`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `integer_list`
6. Scene contract:
   - stacked scenes render one stack per category with one legend label per segment color,
   - stacked scenes print the integer segment values inside the segments,
   - pie/donut scenes use positive integer percentages that sum to `100`,
   - pie/donut scenes use distinct slice colors and a right-side legend,
   - pie/donut scenes print the slice percentages on the slices.
7. Generation guarantees:
   - stacked scenes use `4..7` categories and `3..5` series by default,
   - pie/donut scenes use `3..5` slices by default,
   - stacked segment values use the default integer range `4..18`,
   - `stack_total_at_label` target-balances the full-stack total,
   - `stack_segment_value` target-balances the queried segment value,
   - `combined_share_subset` target-balances the combined percentage of the queried slice pair.

## 3) Prompt contract
1. Bundle: `charts_composition_v1`
2. `task_family_key`: `composition_chart_value`
3. `task_key`: `subset_value_query`
4. `task_variant_key`: one of `stack_total_at_label|stack_segment_value|combined_share_subset`
5. Required slots:
   - task-family: `object_description`
   - task-level: `query_category_label`, `query_series_label`, `query_label_a`, `query_label_b`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/composition.yaml`,
   - deterministic bundle selection from `prompts/charts/composition/charts_composition_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. Prompt-facing evidence is an ordered `integer_list`.
2. Evidence semantics:
   - `stack_total_at_label`: the segment values in legend order for the queried stack,
   - `stack_segment_value`: the segment values in legend order for the queried stack,
   - `combined_share_subset`: the slice percentages in legend order for the whole pie/donut chart.
3. `projected_evidence` includes:
   - `integer_list`
   - `pixel_point_map`
   - `pixel_point_set`
   - `bbox_set`
4. `scene_ir.entities` stores one entity per stack segment or pie slice with visible identity, integer value, and rendered pixel geometry.
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - series labels and optional category labels,
   - queried category / series / subset labels,
   - evidence values and answer value,
   - sampled target-answer range and chosen target answer.

## 5) Visual policy
1. Background and post-image noise use the merged charts-domain visual defaults from `configs/domains/charts/base.yaml`.
2. Stacked scenes use a clean axis scaffold plus a right-side legend.
3. Stacked scenes sample one distinct color per series and reuse it across all stacks.
4. Pie/donut scenes sample one distinct color per slice.
5. All sampled colors remain visually separated from the white/light chart background and are recorded in trace/render metadata.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level, with compatibility preserved by construction.
3. Answers and evidence come from the same generated composition table.
4. No semantic auto-relaxation.
