# `task_charts_distribution_boxplot_label`

## 1) Identity
1. Domain: `charts`
2. Task group: `distribution`
3. Task id: `task_charts_distribution_boxplot_label`
4. Objective: return the label of the boxplot that matches one requested distribution summary property.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `median_above_reference_q3`
   - `largest_iqr`
   - `smallest_iqr`
2. Fixed `scene_variant`: `boxplot`
3. `answer_gt.type`: `option_letter`
4. `evidence_gt.type`: `integer`
5. Scene contract:
   - one categorical boxplot chart per image,
   - each category uses one visible uppercase label,
   - each box spans `Q1..Q3`,
   - the line inside the box marks the median,
   - whiskers show the minimum and maximum shown for that category,
   - all categories share one sampled chart color per instance.
6. Generation guarantees:
   - default category-count support is `4..7`,
   - default value support is `1..20`,
   - `median_above_reference_q3` chooses one reference label and uses one unique largest positive margin between a candidate median and the reference label's upper quartile,
   - `largest_iqr` uses one unique largest interquartile range,
   - `smallest_iqr` uses one unique smallest interquartile range,
   - optional task params may tighten the winner-vs-runner-up margin for the reference-Q3 median or IQR variants while preserving uniqueness.

## 3) Prompt contract
1. Bundle: `charts_distribution_v1`
2. `task_family_key`: `distribution_chart`
3. `task_key`: `boxplot_label_query`
4. `task_variant_key`: one of `median_above_reference_q3|largest_iqr|smallest_iqr`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/distribution.yaml`,
   - deterministic bundle selection from `prompts/charts/distribution/charts_distribution_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. Prompt-facing evidence is one integer witness value:
   - `median_above_reference_q3`: the winning positive margin above the reference label's upper quartile
   - `largest_iqr`: the winning IQR
   - `smallest_iqr`: the winning IQR
2. `projected_evidence` includes:
   - `integer`
   - `pixel_point_map`
   - `pixel_point_set`
   - `bbox_set`
3. `scene_ir.entities` stores one entity per boxplot with:
   - visible category `label`
   - `whisker_min`, `q1`, `median`, `q3`, `whisker_max`
   - rendered boxplot/label pixel geometry
4. `execution_trace` records:
   - `task_variant`
   - fixed `scene_variant = boxplot`
   - per-label quartile/whisker summaries
   - reference-label metadata when the relational median variant is active
   - winning label
   - witness value

## 5) Visual policy
1. Background and post-image noise use the merged charts-domain visual defaults from `configs/domains/charts/base.yaml`.
2. Boxplots render a shared y-axis with integer ticks, one vertical boxplot per category, and one visible category label below each boxplot.
3. Boxes use one shared sampled fill/outline color per instance; the median line is drawn inside each box.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same generated quartile table.
3. No semantic auto-relaxation.
