# `task_charts_distribution_density_label`

## 1) Identity
1. Domain: `charts`
2. Task group: `distribution`
3. Task id: `task_charts_distribution_density_label`
4. Objective: return the label of the violin plot that matches one density-shape query.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `highest_mode`
   - `lowest_mode`
   - `bimodal_label`
2. Fixed `scene_variant`: `violin`
3. `answer_gt.type`: `option_letter`
4. `evidence_gt.type`: `integer_list`
5. Scene contract:
   - one categorical violin-plot chart per image,
   - each category uses one visible uppercase label,
   - each violin spans a support range on the vertical axis,
   - the violin shape shows where the distribution is widest, and those widest peaks indicate the modal values.
6. Generation guarantees:
   - default category-count support is `4..7`,
   - default value support is `1..20`,
   - `highest_mode` uses only unimodal violins and one unique highest mode,
   - `lowest_mode` uses only unimodal violins and one unique lowest mode,
   - `bimodal_label` uses exactly one bimodal violin and all remaining violins are unimodal.

## 3) Prompt contract
1. Bundle: `charts_distribution_v1`
2. `task_family_key`: `distribution_chart`
3. `task_key`: `density_label_query`
4. `task_variant_key`: one of `highest_mode|lowest_mode|bimodal_label`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/distribution.yaml`,
   - deterministic bundle selection from `prompts/charts/distribution/charts_distribution_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. Prompt-facing evidence is an `integer_list` of the winning mode values:
   - `highest_mode`: singleton list `[mode]`
   - `lowest_mode`: singleton list `[mode]`
   - `bimodal_label`: sorted two-value list `[lower_mode, upper_mode]`
2. `projected_evidence` includes:
   - `integer_list`
   - `pixel_point_map`
   - `pixel_point_set`
   - `bbox_set`
3. `scene_ir.entities` stores one entity per violin with:
   - visible category `label`
   - `support_min`
   - `support_max`
   - `mode_values`
   - rendered violin/label pixel geometry
4. `execution_trace` records:
   - `task_variant`
   - fixed `scene_variant = violin`
   - winning label
   - witness mode values
   - per-label support and mode summaries

## 5) Visual policy
1. Background and post-image noise use the merged charts-domain visual defaults from `configs/domains/charts/base.yaml`.
2. Violin plots render a shared y-axis with integer ticks, one vertical violin per category, and one visible category label below each violin.
3. Each violin includes explicit width peaks that make the modal positions visible.
4. All violins in one chart share one sampled fill/outline color in v1.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same generated support/mode table.
3. No semantic auto-relaxation.
