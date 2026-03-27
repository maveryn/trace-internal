# `task_charts_statistics_summary_label`

## 1) Identity
1. Domain: `charts`
2. Task group: `statistics`
3. Task id: `task_charts_statistics_summary_label`
4. Objective: return the label of the mark that matches the requested chart statistic.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `argmax`
   - `argmin`
   - `median_label`
2. Supported `scene_variant` values:
   - `area`
   - `bar`
   - `pie`
   - `donut`
   - `horizontal_bar`
   - `line`
   - `scatter`
   - `dot_plot`
   - `lollipop`
3. `answer_gt.type`: `option_letter`
4. `evidence_gt.type`: `integer`
5. Scene contract:
   - one chart per image,
   - one series only in v1,
   - one visible unique uppercase label per mark,
   - axis-based scenes use one random chart color sampled per instance and reused across all rendered marks,
   - pie/donut scenes use one distinct sampled color per slice plus a legend on the right that maps slice colors to labels,
   - axis-based chart values are integers in the default range `1..20`,
   - pie/donut chart values are positive integer percentages that sum to `100`,
   - area charts summarize plotted point `y` values,
   - vertical bar charts summarize bar heights,
   - pie/donut charts summarize the percentages printed on the slices,
   - horizontal bar charts summarize bar lengths on the horizontal axis,
   - line/scatter/dot-plot/lollipop charts summarize plotted point `y` values.
6. Generation guarantees:
   - charts use `5..10` labeled marks by default,
   - pie/donut charts tighten the effective mark-count support to `5..8` for readability,
   - `argmax` uses a unique maximum mark,
   - `argmin` uses a unique minimum mark,
   - `median_label` uses an odd number of marks with a unique median mark, so its effective default counts are `5|7|9`,
   - the evidence integer is the corresponding winning statistic value,
   - labels are sampled from a random uppercase subset and shuffled independently of value and x-position.

## 3) Prompt contract
1. Bundle: `charts_statistics_v1`
2. `task_family_key`: `labeled_chart_statistics`
3. `task_key`: `summary_label_query`
4. `task_variant_key`: one of `argmax|argmin|median_label`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/statistics.yaml`,
   - deterministic bundle selection from `prompts/charts/statistics/charts_statistics_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is always the winning visible label; prompt-facing evidence is the winning numeric statistic value.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the numeric winning value for the requested statistic.
2. Evidence semantics:
   - `argmax`: the unique maximum value
   - `argmin`: the unique minimum value
   - `median_label`: the median value
3. `projected_evidence` includes:
   - `integer`
   - `pixel_point_map`
   - `pixel_point_set`
   - `bbox_set`
4. `scene_ir.entities` stores one entity per mark with:
   - visible `label`
   - integer `value`
   - `x_rank`
   - rendered mark/label pixel geometry
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `statistic_kind`
   - sampled labels and per-label values
   - answer label and evidence value
   - target-answer range and chosen target answer
   - statistic-specific supporting fields (`winning_label`, `median_label`, `sorted_values`)

## 5) Visual policy
1. Background and post-image noise use the merged charts-domain visual defaults from `configs/domains/charts/base.yaml`.
2. V1 charts use clean light solid backgrounds only.
3. Axis-based chart variants render an explicit integer-valued axis scaffold; `pie` and `donut` render multicolor slice geometry with a legend on the right and printed percentages on the slices instead of axes.
4. Labels are drawn on bars, near points, or in the pie/donut legend, depending on `scene_variant`.
5. The chart frame is rectangular and uses a fixed canvas in v1 rather than dynamic canvas sizing.
6. Mark fill/outline colors are sampled once per instance, constrained to stay visually separated from the white/light chart background, and recorded in trace/render metadata.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level, with compatibility preserved by construction.
3. Answers and evidence come from the same generated mark table.
4. No semantic auto-relaxation.
5. V1 uses `option_letter` answers because the active chart label pool stays within one uppercase character per mark at the current `5..10` mark-count range.
