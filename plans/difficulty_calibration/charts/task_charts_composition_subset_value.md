# task_charts_composition_subset_value

## Metadata

- domain: `charts`
- status: `blocked`
- owner: `codex`
- active_calibration_model: `Qwen/Qwen3-VL-8B-Instruct`
- probe_size: `200`
- rollouts_per_prompt: `32`
- task_module: `trace/tasks/charts/composition/subset_value.py`

## Redesign Status

- pre-redesign probe results and review artifacts were retired on `2026-04-23`
- the old task semantics mixed stacked and pie/donut composition scenes and were too easy under `Qwen/Qwen3-VL-8B-Instruct`
- the task now uses stacked scenes only and the variant set has been replaced with multi-lookup arithmetic queries
- the first fresh `200 x 32` baseline for the redesigned task is complete

## Recorded Baseline Task Parameters

- config source: `configs/domains/charts/composition.yaml`
- task module source: `trace/tasks/charts/composition/subset_value.py`
- recorded baseline role: `post-redesign recorded baseline`
- working baseline role: `same as recorded baseline until new 8B probe suggests otherwise`
- scene/task balancing:
  - `task_variant_weights = {category_subset_sum: 1.0, series_across_categories_sum: 1.0, subset_margin_sum: 1.0}`
  - `scene_variant_weights = {stacked_bar: 1.0, stacked_horizontal_bar: 1.0}`
  - `balanced_task_variant_sampling = true`
  - `balanced_scene_variant_sampling = true`
- generation bounds:
  - `category_count_range = [6, 9]`
  - `series_count_range = [5, 7]`
  - `query_category_subset_size_range = [3, 4]`
  - `query_series_subset_size_range = [3, 4]`
  - `comparison_subset_size_range = [2, 3]`
  - `value_range = [4, 18]`
- variant-specific task contract:
  - `category_subset_sum`: query one category and sum `3..4` selected legend labels in that stack
  - `series_across_categories_sum`: query one legend label and sum it across `3..4` selected categories
  - `subset_margin_sum`: compare two disjoint legend subsets across all categories and sum only the positive per-category margins `(left total - right total)`
- current render size:
  - `canvas_width = 1120`
  - `canvas_height = 720`
- current complexity recipe:
  - weights: `visual_scan=0.35`, `reasoning_load=0.45`, `scene_variant_load=0.20`
  - task-variant loads: `category_subset_sum=0.42`, `series_across_categories_sum=0.62`, `subset_margin_sum=1.00`
  - scene loads: `stacked_bar=0.00`, `stacked_horizontal_bar=0.16`

## Working Baseline

- status: `evaluated`
- baseline_replacement_needed: `yes`
- rationale: `iteration 1 confirms that numeric support tuning alone is not enough: the first two variants remain too easy even after aggressive structural hardening, while subset_margin_sum is highly sensitive to scene-specific support changes`
- params_override: `{}`

## Distribution Validation

- status: `passed`
- requirement: generated calibration samples must satisfy TRACE task-distribution, answer-diversity, and answer-support checks before model evaluation
- workflow reference: `docs/workflows/BUILD_VALIDATION.md`
- exact set:
  - parquet: `out/calibration/task_charts_composition_subset_value_probe_200.parquet`
  - dataset root: `out/calibration/datasets/blake3:5a5c7e685a442695c3518fb46a806107cefd1068c28d48ca265372bda0287e29`
  - report: `out/calibration/task_charts_composition_subset_value_probe_200.parquet.distribution_report.json`
- expected checks:
  - overall distribution pass on the full `200`-sample parquet
  - per-variant distribution pass for `category_subset_sum`, `series_across_categories_sum`, and `subset_margin_sum`
  - no stale retired variants or pie/donut scenes in the review/export outputs

## Floor Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded baseline | `{"category_count_min": 6, "category_count_max": 9, "series_count_min": 5, "series_count_max": 7, "query_category_subset_size_min": 3, "query_category_subset_size_max": 4, "query_series_subset_size_min": 3, "query_series_subset_size_max": 4, "comparison_subset_size_min": 2, "comparison_subset_size_max": 3}` |
| `1` | modestly trim the easy tail by raising minimum structural load | `{"category_count_min": 7, "category_count_max": 9, "series_count_min": 6, "series_count_max": 7, "query_category_subset_size_min": 3, "query_category_subset_size_max": 4, "query_series_subset_size_min": 4, "query_series_subset_size_max": 4, "comparison_subset_size_min": 3, "comparison_subset_size_max": 3}` |
| `2` | aggressively trim the easy tail with larger charts and larger queried subsets | `{"category_count_min": 8, "category_count_max": 10, "series_count_min": 6, "series_count_max": 8, "query_category_subset_size_min": 4, "query_category_subset_size_max": 4, "query_series_subset_size_min": 4, "query_series_subset_size_max": 4, "comparison_subset_size_min": 3, "comparison_subset_size_max": 3, "scene_variant_weights": {"stacked_bar": 0.85, "stacked_horizontal_bar": 1.15}}` |

## Ceiling Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded baseline | `{"category_count_min": 6, "category_count_max": 9, "series_count_min": 5, "series_count_max": 7, "query_category_subset_size_min": 3, "query_category_subset_size_max": 4, "query_series_subset_size_min": 3, "query_series_subset_size_max": 4, "comparison_subset_size_min": 2, "comparison_subset_size_max": 3}` |
| `1` | soften the hard tail by lowering maximum structural load | `{"category_count_min": 6, "category_count_max": 8, "series_count_min": 5, "series_count_max": 6, "query_category_subset_size_min": 3, "query_category_subset_size_max": 3, "query_series_subset_size_min": 3, "query_series_subset_size_max": 3, "comparison_subset_size_min": 2, "comparison_subset_size_max": 2}` |
| `2` | aggressively soften the hard tail by narrowing both chart and subset sizes | `{"category_count_min": 5, "category_count_max": 7, "series_count_min": 4, "series_count_max": 6, "query_category_subset_size_min": 3, "query_category_subset_size_max": 3, "query_series_subset_size_min": 3, "query_series_subset_size_max": 3, "comparison_subset_size_min": 2, "comparison_subset_size_max": 2, "scene_variant_weights": {"stacked_bar": 1.15, "stacked_horizontal_bar": 0.85}}` |

## 8B Baseline Probe

- status: `complete`
- prompt_count: `200`
- rollout_count: `6400`
- hard_frac (`solve_rate == 0`): `0.1050`
- easy_frac (`solve_rate >= 0.8`): `0.6750`
- band_frac (`0 < solve_rate < 0.8`): `0.2200`
- mean_solve_rate: `0.7352`

## Operational Thresholds

- probe size is fixed at `200`
- acceptable pass:
  - `hard_frac <= 0.10`
  - `easy_frac <= 0.10`
  - `band_frac >= 0.80`
- floor-side update from `easy_frac`:
  - `<= 0.05`: `+0` floor steps
  - `0.05-0.15`: `+1` floor step
  - `> 0.15`: `+2` floor steps
- ceiling-side update from `hard_frac`:
  - `<= 0.05`: `+0` ceiling steps
  - `0.05-0.15`: `+1` ceiling step
  - `> 0.15`: `+2` ceiling steps

## Working Notes

- this task was semantically redesigned before the first 8B calibration pass because the retired variant set was dominated by direct printed-value lookup
- keep the task family stacked-only
- do not reintroduce `pie` or `donut` scenes here
- first 8B baseline failure mode:
  - overall tails are still far outside the target band (`hard_frac=0.105`, `easy_frac=0.675`, `band_frac=0.220`)
  - global threshold logic would suggest `floor +2` and `ceiling +1`, but the variant breakdown shows that one uniform move will be too blunt
- per-variant baseline stats:
  - `category_subset_sum`: `hard_frac=0.0149`, `easy_frac=0.9701`, `band_frac=0.0149`, `mean_solve_rate=0.9506`
  - `series_across_categories_sum`: `hard_frac=0.0000`, `easy_frac=0.8955`, `band_frac=0.1045`, `mean_solve_rate=0.9151`
  - `subset_margin_sum`: `hard_frac=0.3030`, `easy_frac=0.1515`, `band_frac=0.5455`, `mean_solve_rate=0.3338`
- per-variant by scene:
  - `category_subset_sum` + `stacked_bar`: `easy_frac=1.0000`
  - `category_subset_sum` + `stacked_horizontal_bar`: `easy_frac=0.9394`
  - `series_across_categories_sum` + `stacked_bar`: `easy_frac=0.9697`
  - `series_across_categories_sum` + `stacked_horizontal_bar`: `easy_frac=0.8235`
  - `subset_margin_sum` + `stacked_bar`: `hard_frac=0.1818`, `easy_frac=0.3030`, `band_frac=0.5152`
  - `subset_margin_sum` + `stacked_horizontal_bar`: `hard_frac=0.4242`, `easy_frac=0.0000`, `band_frac=0.5758`
- interpretation:
  - the two sum-style variants need much stronger floor tightening
  - `subset_margin_sum` is the right direction semantically, but it is already much harder and the horizontal scene is currently overshooting into the hard tail
- iteration 1 override mix:
  - `category_subset_sum`: `category_count=8..10`, `series_count=6..8`, `query_series_subset_size=4`
  - `series_across_categories_sum`: `category_count=8..10`, `series_count=6..8`, `query_category_subset_size=4`
  - `subset_margin_sum`: base `category_count=6..8`, `series_count=5..6`, `comparison_subset_size=2`, `target_answer=8..28`
  - `subset_margin_sum` scene overrides:
    - `stacked_bar`: `category_count=7..8`, `target_answer=12..32`
    - `stacked_horizontal_bar`: `category_count=5..6`, `target_answer=6..18`
- iteration 1 results:
  - overall `hard_frac=0.0500`, `easy_frac=0.8250`, `band_frac=0.1250`, `mean_solve_rate=0.8625`
  - `category_subset_sum`: `hard_frac=0.0149`, `easy_frac=0.9104`, `band_frac=0.0746`
  - `series_across_categories_sum`: `hard_frac=0.0448`, `easy_frac=0.8060`, `band_frac=0.1493`
  - `subset_margin_sum`: `hard_frac=0.0909`, `easy_frac=0.7576`, `band_frac=0.1515`
- iteration 1 interpretation:
  - `category_subset_sum` and `series_across_categories_sum` improved only marginally and are still fundamentally too easy for the 8B model
  - `subset_margin_sum` became much easier overall than the baseline, so the first scene-specific softening pass over-corrected it
  - this task is now showing a semantic gap, not just a support-gap: two variants are too lookup-like, while the third is highly tunable but unstable
- solve-rate by structural size:
  - redesign baseline (`iter0`) grouped by `(category_count, series_count)`:
    - `category_subset_sum`: `(6,5)->0.9688`, `(7,5)->0.9199`, `(8,5)->0.9871`, `(9,5)->0.9246`
    - `series_across_categories_sum`: `(6,6)->0.9357`, `(7,6)->0.9173`, `(8,6)->0.9668`, `(9,6)->0.8438`
    - `subset_margin_sum`: `(6,7)->0.7129`, `(7,7)->0.2610`, `(8,7)->0.3438`, `(9,7)->0.0215`
  - iteration 1 grouped support:
    - `category_subset_sum`: `(8,6)->0.9324`
    - `series_across_categories_sum`: `(9,7)->0.8386`
    - `subset_margin_sum`: `(7,5)->0.7292`, `(6,6)->0.9025`
  - size-only interpretation:
    - increasing `category_count` and `series_count` does move solve rate for `subset_margin_sum`
    - the same knob changes barely move `category_subset_sum` and only modestly move `series_across_categories_sum`
    - structural size alone is therefore not enough to pull the first two variants into the target band
- overlap guardrails:
  - do not collapse back to single-cell lookup
  - do not reduce to full-stack total lookup
  - do not duplicate `task_charts_multiseries_pairwise_comparison_count` by using only one-series-vs-one-series comparisons

## Probe Log

| Date | Model | Samples | Rollouts | Hard frac | Easy frac | Band frac | Mean solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 0 | 0 | n/a | n/a | n/a | n/a | retired the old variant set and reset calibration for the redesigned task |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.105 | 0.675 | 0.220 | 0.735 | fail: keep redesign, but move to variant-specific calibration instead of one uniform baseline update |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.050 | 0.825 | 0.125 | 0.863 | fail: iteration-1 support tuning made the task easier overall; next step should be semantic redesign of the sum-style variants |

## Next Action

- redesign `category_subset_sum` and `series_across_categories_sum` so both require stronger two-axis reasoning rather than a mostly local sum
- keep `subset_margin_sum` as the likely anchor variant, but retune it after the variant-set redesign rather than continuing blind numeric knob sweeps
- regenerate the exact `200`-sample parquet and rerun the `32`-rollout 8B probe after the semantic change
