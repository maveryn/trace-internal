# `task_charts_readout_subset_value`

## 1) Identity
1. Domain: `charts`
2. Task group: `readout`
3. Task id: `task_charts_readout_subset_value`
4. Objective: read out one derived integer from the values of exactly two queried chart labels.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `sum_two`
   - `difference_two_abs`
   - `max_two`
   - `min_two`
   - `mean_two`
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
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `integer_list`
5. Scene contract:
   - one chart per image,
   - one series only in v1,
   - one visible unique label per mark,
   - axis-based scenes use one random chart color sampled per instance and reused across all rendered marks,
   - pie/donut scenes use one distinct sampled color per slice plus a legend on the right that maps slice colors to labels,
   - axis-based chart values are integers in the default range `1..20`,
   - pie/donut chart values are positive integer percentages that sum to `100`,
   - area charts read plotted point `y` values,
   - vertical bar charts read bar heights,
   - pie/donut charts read the percentages printed on the slices,
   - horizontal bar charts read bar lengths on the horizontal axis,
   - line/scatter/dot-plot/lollipop charts read plotted point `y` values.
6. Generation guarantees:
   - charts use `5..10` labeled marks by default,
   - pie/donut charts tighten the effective mark-count support to `5..8` for readability,
   - exactly two queried labels are chosen per instance,
   - query-label order is explicit and semantically meaningful,
   - labels are sampled from a random uppercase subset and shuffled independently of value and x-position.

## 3) Prompt contract
1. Bundle: `charts_readout_v1`
2. `task_family_key`: `labeled_chart_readout`
3. `task_key`: `subset_value_query`
4. `task_variant_key`: one of `sum_two|difference_two_abs|max_two|min_two|mean_two`
5. Required slots:
   - task-family: `object_description`
   - task-level: `query_label_a`, `query_label_b`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/readout.yaml`,
   - deterministic bundle selection from `prompts/charts/readout/charts_readout_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing evidence is the ordered list of queried numeric values, not the queried labels.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an ordered `integer_list` containing the two queried values in the same order the queried labels appear in the prompt.
2. Evidence semantics:
   - `sum_two`: the two queried values whose sum is requested
   - `difference_two_abs`: the two queried values whose absolute difference is requested
   - `max_two`: the two queried values whose maximum is requested
   - `min_two`: the two queried values whose minimum is requested
   - `mean_two`: the two queried values whose mean is requested
3. `projected_evidence` includes:
   - `integer_list`
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
   - ordered `query_labels`
   - ordered `query_values`
   - target-answer range and chosen target answer

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
5. Evidence order is defined by prompt label order and must not be alphabetized or otherwise re-sorted.
