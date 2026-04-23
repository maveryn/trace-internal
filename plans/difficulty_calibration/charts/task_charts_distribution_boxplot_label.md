# task_charts_distribution_boxplot_label

## Metadata

- domain: `charts`
- status: `in_progress`
- owner: `codex`
- active_calibration_model: `Qwen/Qwen3-VL-8B-Instruct`
- probe_size: `200`
- rollouts_per_prompt: `32`
- task_module: `trace/tasks/charts/distribution/boxplot_label.py`
- 2b_reference_file: [task_charts_distribution_boxplot_label__qwen3_vl_2b_reference.md](task_charts_distribution_boxplot_label__qwen3_vl_2b_reference.md)

## Reference Context

- the linked 2B reference file is historical only and predates the current boxplot semantic redesign
- active calibration should use only the fresh `Qwen/Qwen3-VL-8B-Instruct` `200 x 32` results recorded below
- the old `highest_median` iterations are stale and should not be used as the current baseline

## Recorded Baseline Task Parameters

- config source: `configs/domains/charts/distribution.yaml`
- task module source: `trace/tasks/charts/distribution/boxplot_label.py`
- recorded baseline role: `fresh 8B baseline after semantic redesign`
- working baseline role: `same as recorded baseline until a first hardening pass is defined`
- scene/task balancing:
  - `task_variant_weights = {median_above_reference_q3: 1.0, largest_iqr: 1.0, smallest_iqr: 1.0}`
  - `scene_variant = boxplot` (fixed)
  - `balanced_task_variant_sampling = true`
- generation bounds:
  - `category_count_range = [4, 7]`
  - `value_range = [1, 20]`
- variant-specific task contract:
  - `median_above_reference_q3`: return the label whose median is furthest above a named reference label's upper quartile
  - `largest_iqr`: return the label with the largest interquartile range
  - `smallest_iqr`: return the label with the smallest interquartile range
- current render size:
  - `canvas_width = 860`
  - `canvas_height = 620`
- current complexity recipe:
  - weights: `visual_scan=0.40`, `reasoning_load=0.60`, `scene_variant_load=0.0`
  - task-variant loads: `median_above_reference_q3=1.0`, `largest_iqr=1.0`, `smallest_iqr=1.0`
  - scene load: fixed `boxplot`

## Working Baseline

- status: `evaluated`
- baseline_replacement_needed: `no`
- rationale: `the redesigned relational-median baseline is valid and meaningfully harder than the retired highest-median variant, but it still has too many easy samples`
- params_override: `{}`

## Distribution Validation

- status: `passed`
- requirement: generated calibration samples must satisfy TRACE task-distribution and answer-support checks before model evaluation
- workflow reference: `docs/workflows/BUILD_VALIDATION.md`
- exact set:
  - parquet: `out/calibration/task_charts_distribution_boxplot_label_probe_200.parquet`
  - dataset root: `out/calibration/datasets/blake3:297adeac54d545b429894cf7fcff56130450557d51b2311f4912f9416d0d8e41`
  - report: `out/calibration/task_charts_distribution_boxplot_label_probe_200.parquet.distribution_report.json`
- notes:
  - overall pass: `unique=24`, `max_answer=16/200 (0.080)`
  - per-variant all passed:
    - `largest_iqr`: `unique=23`, `max_answer=7/67 (0.104)`
    - `median_above_reference_q3`: `unique=24`, `max_answer=5/66 (0.076)`
    - `smallest_iqr`: `unique=22`, `max_answer=6/67 (0.090)`

## Floor Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded or working baseline | `{"category_count_min": 4, "category_count_max": 7, "value_min": 1, "value_max": 20}` |
| `1` | raise minimum difficulty | pending |
| `2` | aggressively raise minimum difficulty | pending |

## Ceiling Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded or working baseline | pending |
| `1` | lower maximum difficulty | pending |
| `2` | aggressively lower maximum difficulty | pending |

## 8B Baseline Probe

- status: `complete`
- prompt_count: `200`
- rollout_count: `6400`
- hard_frac (`solve_rate == 0`): `0.1050`
- easy_frac (`solve_rate >= 0.8`): `0.5550`
- band_frac (`0 < solve_rate < 0.8`): `0.3400`
- mean_solve_rate: `0.6541`

## Working Notes

- `highest_median` has been retired and replaced with `median_above_reference_q3`
- the redesign helped materially compared with the old median-ranking semantics:
  - the new relational median variant is no longer near-complete saturation
  - answer-support diversity remains healthy after the redesign
- baseline by variant:
  - `median_above_reference_q3`: `hard_frac=0.0000`, `easy_frac=0.7576`, `band_frac=0.2424`, `mean_solve_rate=0.8561`
  - `largest_iqr`: `hard_frac=0.1791`, `easy_frac=0.4179`, `band_frac=0.4030`, `mean_solve_rate=0.5420`
  - `smallest_iqr`: `hard_frac=0.1343`, `easy_frac=0.4925`, `band_frac=0.3731`, `mean_solve_rate=0.5672`
- category-count notes from the redesigned baseline:
  - `4`: `hard_frac=0.1200`, `easy_frac=0.6000`, `band_frac=0.2800`, `mean_solve_rate=0.6813`
  - `5`: `hard_frac=0.1000`, `easy_frac=0.6000`, `band_frac=0.3000`, `mean_solve_rate=0.6831`
  - `6`: `hard_frac=0.0800`, `easy_frac=0.5000`, `band_frac=0.4200`, `mean_solve_rate=0.6381`
  - `7`: `hard_frac=0.1200`, `easy_frac=0.5200`, `band_frac=0.3600`, `mean_solve_rate=0.6138`
- interpretation:
  - the redesign moved the task in the right direction, but `median_above_reference_q3` is still the dominant easy-tail source
  - both IQR variants already have meaningful mixed-signal mass, so they should not be hardened globally until the median variant is under control
  - larger category counts help somewhat but are still not enough on their own
- iteration 1 median-only hardening:
  - params override: `{"task_variant_overrides":{"median_above_reference_q3":{"category_count_min":6,"category_count_max":6,"median_reference_above_count_min":4,"median_reference_above_count_max":4,"median_reference_winner_gap_min":1,"median_reference_winner_gap_max":1}}}`
  - exact set:
    - parquet: `out/calibration/task_charts_distribution_boxplot_label_probe_200_iter1.parquet`
    - dataset root: `out/calibration/datasets/blake3:8f5e349b87563edafeee39ae3766c6dafd93898102bc74a03cf2f1d64b282009`
    - distribution report: `out/calibration/task_charts_distribution_boxplot_label_probe_200_iter1.parquet.distribution_report.json`
  - overall result:
    - `hard_frac=0.1000`
    - `easy_frac=0.5400`
    - `band_frac=0.3600`
    - `mean_solve_rate=0.6528`
  - by variant:
    - `median_above_reference_q3`: `hard_frac=0.0000`, `easy_frac=0.7164`, `band_frac=0.2836`, `mean_solve_rate=0.8405`
    - `largest_iqr`: `hard_frac=0.1493`, `easy_frac=0.4179`, `band_frac=0.4328`, `mean_solve_rate=0.5420`
    - `smallest_iqr`: `hard_frac=0.1515`, `easy_frac=0.4848`, `band_frac=0.3636`, `mean_solve_rate=0.5748`
  - interpretation:
    - this is a real but modest improvement over the redesign baseline
    - the median variant is still too easy, but forcing it into the `category_count=6`, `above_count=4`, `winner_gap=1` regime reduced the easy tail and increased mixed-signal mass
    - this is the current best checkpoint for the redesigned task
- iteration 2 all-candidate-above-reference hardening:
  - params override: `{"task_variant_overrides":{"median_above_reference_q3":{"category_count_min":6,"category_count_max":6,"median_reference_above_count_min":5,"median_reference_above_count_max":5,"median_reference_winner_gap_min":1,"median_reference_winner_gap_max":1}}}`
  - exact set:
    - parquet: `out/calibration/task_charts_distribution_boxplot_label_probe_200_iter2.parquet`
    - dataset root: `out/calibration/datasets/blake3:28e0998f15dadecd9d596a948adbfd757e15357c87a1b706854e29e9ad0fc22d`
    - distribution report: `out/calibration/task_charts_distribution_boxplot_label_probe_200_iter2.parquet.distribution_report.json`
  - overall result:
    - `hard_frac=0.1100`
    - `easy_frac=0.5700`
    - `band_frac=0.3200`
    - `mean_solve_rate=0.6456`
  - by variant:
    - `median_above_reference_q3`: `hard_frac=0.0000`, `easy_frac=0.8333`, `band_frac=0.1667`, `mean_solve_rate=0.8740`
    - `largest_iqr`: `hard_frac=0.1571`, `easy_frac=0.4143`, `band_frac=0.4286`, `mean_solve_rate=0.5393`
    - `smallest_iqr`: `hard_frac=0.1571`, `easy_frac=0.5000`, `band_frac=0.3429`, `mean_solve_rate=0.5563`
  - interpretation:
    - this made the relational median variant easier, not harder
    - forcing all five non-reference categories above the reference `Q3` reduced distractor diversity and made the winner more obvious
    - iter1 remains the current best checkpoint

## Probe Log

| Date | Model | Samples | Rollouts | Hard frac | Easy frac | Band frac | Mean solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.105 | 0.555 | 0.340 | 0.654 | redesign baseline: valid and clearly better than the retired median-ranking variant, but still too easy overall; next pass should target `median_above_reference_q3` specifically |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.100 | 0.540 | 0.360 | 0.653 | positive: median-only hardening improved the redesigned task modestly; keep as the current best checkpoint |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.110 | 0.570 | 0.320 | 0.646 | negative: making all five non-reference categories valid candidates made the relational median variant easier; keep iter1 as the current best checkpoint |

## Next Action

- preserve iter1 as the current best checkpoint
- continue focusing first on `median_above_reference_q3`, since it remains the dominant easy-tail source
- avoid global hardening of the IQR variants until their hard tails are lower
- next hardening pass should change the relational median construction before changing the whole task:
  - keep `category_count=6` as the working median regime for now
  - keep `above_count=4`; `above_count=5` made the variant easier
  - consider biasing the reference `Q3` upward, since low reference quartiles are still the easiest subregime
  - keep the reference category visually plausible rather than making its `Q3` extreme
