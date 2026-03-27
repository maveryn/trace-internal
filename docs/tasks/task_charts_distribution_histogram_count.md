# `task_charts_distribution_histogram_count`

## 1) Identity
1. Domain: `charts`
2. Task group: `distribution`
3. Task id: `task_charts_distribution_histogram_count`
4. Objective: answer integer-count questions over one histogram with contiguous numeric bins.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `modal_bin_count`
   - `interval_mass`
   - `cumulative_count_to_bin`
2. Fixed `scene_variant`: `histogram`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_set`
5. Scene contract:
   - one histogram per image,
   - one ordered sequence of contiguous numeric interval bins on the horizontal axis,
   - each bar height encodes the count for that interval,
   - bin labels use numeric interval strings such as `0-2` or `9-11`,
   - bars use one sampled chart color per instance.
6. Generation guarantees:
   - default bin-count support is `4..7`,
   - default bin-width support is `2..4`,
   - default bin-frequency support is `1..12`,
   - `modal_bin_count` uses one unique highest-count bin,
   - `interval_mass` queries one contiguous multi-bin interval,
   - `cumulative_count_to_bin` queries the cumulative sum from the first bin through one named bin.

## 3) Prompt contract
1. Bundle: `charts_distribution_v1`
2. `task_family_key`: `distribution_chart`
3. `task_key`: `histogram_count_query`
4. `task_variant_key`: one of `modal_bin_count|interval_mass|cumulative_count_to_bin`
5. Required slots:
   - task-family: `object_description`
   - task layer: `query_interval_label`, `query_bin_label`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/charts/distribution.yaml`,
   - deterministic bundle selection from `prompts/charts/distribution/charts_distribution_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. Prompt-facing evidence is the deterministic `label_set` of bins used to compute the answer.
2. Evidence semantics:
   - `modal_bin_count`: the unique highest-count bin
   - `interval_mass`: all bins included in the queried interval
   - `cumulative_count_to_bin`: all bins from the first bin through the queried bin
3. `projected_evidence` includes:
   - `label_set`
   - `pixel_point_map`
   - `pixel_point_set`
   - `bbox_set`
4. `scene_ir.entities` stores one entity per bin with:
   - visible interval `label`
   - integer `count`
   - bin rank
   - interval start/end
   - rendered bar/label pixel geometry
5. `execution_trace` records:
   - `task_variant`
   - fixed `scene_variant = histogram`
   - ordered bin labels and bin counts
   - the queried interval or queried end-bin label when applicable
   - target-answer range and chosen target answer
   - evidence labels

## 5) Visual policy
1. Background and post-image noise use the merged charts-domain visual defaults from `configs/domains/charts/base.yaml`.
2. Histograms render an explicit y-axis count scaffold with contiguous bars and numeric interval labels on the x-axis.
3. Histogram bins are intentionally adjacent so the scene reads as a real numeric-bin histogram rather than a categorical bar chart alias.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. The answer is unique by the queried histogram operation, not by hidden visual tie-breaking.
3. Answers and evidence come from the same generated bin table.
4. No semantic auto-relaxation.
