# `task_charts_statistics_summary_value`

## 1) Identity
1. Domain: `charts`
2. Task group: `statistics`
3. Task id: `task_charts_statistics_summary_value`
4. Objective: return one requested summary statistic over the labeled chart values.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `max`
   - `min`
   - `range`
   - `mean`
   - `median`
   - `sum`
   - `mode`
2. Supported `scene_variant` values:
   - `bar`
   - `pie`
   - `donut`
   - `horizontal_bar`
   - `line`
   - `scatter`
   - `dot_plot`
   - `lollipop`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_set`
5. Scene contract:
   - one chart per image,
   - one series only in v1,
   - one visible unique label per mark,
   - one random chart color sampled per instance and reused across all rendered marks,
   - chart values are integers in the default range `1..20`,
   - vertical bar charts summarize bar heights,
   - pie/donut charts summarize the printed integer values shown next to the slice labels,
   - horizontal bar charts summarize bar lengths on the horizontal axis,
   - line/scatter/dot-plot/lollipop charts summarize plotted point `y` values.
6. Generation guarantees:
   - charts use `5..10` labeled marks by default,
   - pie/donut charts tighten the effective mark-count support to `5..8` for readability,
   - all statistic answers are integers by construction,
    - `max` / `min` use unique extremum marks,
    - `range` uses unique minimum and maximum marks,
   - `median` uses an odd number of marks with a unique median mark, so its effective default counts are `5|7|9`,
    - `mode` uses one unique modal value,
    - `sum` uses the full feasible support implied by the active mark-count and per-mark value bounds rather than an extra narrow cap,
    - labels are sampled from a random uppercase subset and shuffled independently of value and x-position.

## 3) Prompt contract
1. Bundle: `charts_statistics_v1`
2. `task_family_key`: `labeled_chart_statistics`
3. `task_key`: `summary_value_query`
4. `task_variant_key`: one of `max|min|range|mean|median|sum|mode`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/statistics.yaml`,
   - deterministic bundle selection from `prompts/charts/statistics/charts_statistics_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing evidence always uses visible mark labels rather than pixel boxes or coordinates.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the deterministic `label_set` of marks that directly witness the statistic.
2. Evidence semantics:
   - `max` / `min`: the unique winning label
   - `range`: the unique min-label and max-label
   - `mean` / `sum`: all chart labels
   - `median`: the median mark label
   - `mode`: all labels whose value equals the unique modal value
3. `projected_evidence` includes:
   - `label_set`
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
   - sampled labels and per-label values
   - target-answer range and chosen target answer
   - evidence labels
   - statistic-specific supporting fields (`winning_label`, `min_label`, `max_label`, `median_label`, `mode_frequency`, `computed_sum`)

## 5) Visual policy
1. Background and post-image noise use the merged charts-domain visual defaults from `configs/domains/charts/base.yaml`.
2. V1 charts use clean light solid backgrounds only.
3. Axis-based chart variants render an explicit integer-valued axis scaffold; `pie` and `donut` render slice geometry with printed per-slice values instead of axes.
4. Labels are drawn on bars, near points, or beside pie/donut slices, depending on `scene_variant`.
5. The chart frame is rectangular and uses a fixed canvas in v1 rather than dynamic canvas sizing.
6. Mark fill/outline colors are sampled once per instance, constrained to stay visually separated from the white/light chart background, and recorded in trace/render metadata.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level, with compatibility preserved by construction.
3. Answers and evidence come from the same generated mark table.
4. No semantic auto-relaxation.
5. If a second chart family needs richer chart-grounded evidence, add a chart-native evidence type explicitly rather than overloading this task's `label_set` contract.
