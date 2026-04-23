# task_charts_counting_value_count

## Metadata

- domain: `charts`
- status: `in_progress`
- owner: `codex`
- active_calibration_model: `Qwen/Qwen3-VL-8B-Instruct`
- probe_size: `200`
- rollouts_per_prompt: `32`
- task_module: `trace/tasks/charts/counting/value_count.py`
- 2b_reference_file: [task_charts_counting_value_count__qwen3_vl_2b_reference.md](task_charts_counting_value_count__qwen3_vl_2b_reference.md)

## Reference Context

- the linked 2B reference file records the historical `Qwen/Qwen3-VL-2B-Instruct` probe numbers
- use it only as context for task behavior and tail shape
- the active baseline for calibration must come from a fresh `Qwen/Qwen3-VL-8B-Instruct` probe on newly generated `200` samples

## Recorded Baseline Task Parameters

- config source: `configs/domains/charts/counting.yaml`
- task module source: `trace/tasks/charts/counting/value_count.py`
- recorded baseline role: `fresh 8B baseline`
- working baseline role: `same as recorded baseline until a first hardening pass is defined`
- scene/task balancing:
  - `task_variant_weights = {above_threshold: 1.0, below_threshold: 1.0, in_interval: 1.0}`
  - `scene_variant_weights = {area: 1.0, bar: 1.0, line: 1.0, scatter: 1.0, radar: 1.0, pie: 1.0, donut: 1.0, horizontal_bar: 1.0, dot_plot: 1.0, lollipop: 1.0}`
  - `balanced_task_variant_sampling = true`
  - `balanced_scene_variant_sampling = true`
- generation bounds:
  - `mark_count_range = [5, 10]`
  - `value_range = [1, 20]`
  - `target_answer_range = [0, 10]`
- variant-specific task contract:
  - `above_threshold`: count labels with values strictly greater than a threshold
  - `below_threshold`: count labels with values strictly less than a threshold
  - `in_interval`: count labels with values in an inclusive interval
- current render size:
  - `canvas_width = 800`
  - `canvas_height = 600`
- current complexity recipe:
  - weights: `visual_scan=0.50`, `reasoning_load=0.30`, `scene_variant_load=0.20`
  - task-variant loads: `above_threshold=0.00`, `below_threshold=0.00`, `in_interval=1.00`
  - scene loads: `bar=0.00`, `horizontal_bar=0.08`, `line=0.18`, `area=0.24`, `pie=0.28`, `donut=0.34`, `dot_plot=0.44`, `lollipop=0.52`, `scatter=0.62`, `radar=1.00`

## Working Baseline

- status: `evaluated`
- baseline_replacement_needed: `no`
- rationale: `the fresh 8B baseline is neither trivial nor fully saturated; it is a valid starting point for targeted hardening`
- params_override: `{}`

## Distribution Validation

- status: `passed`
- requirement: generated calibration samples must satisfy TRACE task-distribution and answer-support checks before model evaluation
- workflow reference: `docs/workflows/BUILD_VALIDATION.md`
- exact set:
  - parquet: `out/calibration/task_charts_counting_value_count_probe_200.parquet`
  - dataset root: `out/calibration/datasets/blake3:0cf207555504f56a8849e345f2f1f331e9c00cdf155273d0e9edd68cb37f3578`
  - report: `out/calibration/task_charts_counting_value_count_probe_200.parquet.distribution_report.json`
- notes:
  - overall pass: `unique=11`, `max_answer=25/200 (0.125)`
  - per-variant all passed:
    - `above_threshold`: `unique=11`, `max_answer=12/67 (0.179)`
    - `below_threshold`: `unique=11`, `max_answer=10/67 (0.149)`
    - `in_interval`: `unique=11`, `max_answer=10/66 (0.152)`

## Floor Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded or working baseline | `{"mark_count_min": 5, "mark_count_max": 10, "target_answer_min": 0, "target_answer_max": 10}` |
| `1` | raise minimum difficulty by removing trivial answer extremes and increasing the minimum mark count | `{"mark_count_min": 7, "mark_count_max": 10, "target_answer_min": 2, "target_answer_max": 8}` |
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
- hard_frac (`solve_rate == 0`): `0.0750`
- easy_frac (`solve_rate >= 0.8`): `0.3850`
- band_frac (`0 < solve_rate < 0.8`): `0.5400`
- mean_solve_rate: `0.5492`

## Working Notes

- fresh `200 x 32` `Qwen/Qwen3-VL-8B-Instruct` baseline is complete
- this task is too easy overall, but unlike `task_charts_composition_subset_value` it is not saturated enough to justify immediate redesign
- per-variant baseline stats:
  - `above_threshold`: `hard_frac=0.0896`, `easy_frac=0.4776`, `band_frac=0.4328`, `mean_solve_rate=0.5993`
  - `below_threshold`: `hard_frac=0.1194`, `easy_frac=0.3582`, `band_frac=0.5224`, `mean_solve_rate=0.5070`
  - `in_interval`: `hard_frac=0.0152`, `easy_frac=0.3182`, `band_frac=0.6667`, `mean_solve_rate=0.5412`
- scene notes from the baseline:
  - easiest scene/variant combinations include `above_threshold` on `donut`, `dot_plot`, and `horizontal_bar`
  - strongest mixed-signal combinations include `below_threshold` on `donut`, `scatter`, and `horizontal_bar`, plus `in_interval` on `pie`, `donut`, `radar`, and `lollipop`
  - `bar` and `area` scenes are not uniformly easy; some are already close to the desired regime
- mark-count notes from the baseline:
  - solve rate is not monotonic in `mark_count`
  - simple global size changes are unlikely to be enough by themselves
  - threshold/interval construction and scene weighting are likely to be stronger first-pass hardening knobs than only raising `mark_count_min`
- iteration 1 support hardening:
  - params override: `{"mark_count_min": 7, "mark_count_max": 10, "target_answer_min": 2, "target_answer_max": 8}`
  - exact set:
    - parquet: `out/calibration/task_charts_counting_value_count_probe_200_iter1.parquet`
    - dataset root: `out/calibration/datasets/blake3:518a3495c5ec29b20357a25959cd02cd6b379dfb4fb32904477801c2410f7b14`
    - distribution report: `out/calibration/task_charts_counting_value_count_probe_200_iter1.parquet.distribution_report.json`
  - overall result:
    - `hard_frac=0.0350`
    - `easy_frac=0.3400`
    - `band_frac=0.6250`
    - `mean_solve_rate=0.5166`
  - by variant:
    - `above_threshold`: `hard_frac=0.0299`, `easy_frac=0.3433`, `band_frac=0.6269`, `mean_solve_rate=0.4837`
    - `below_threshold`: `hard_frac=0.0597`, `easy_frac=0.3582`, `band_frac=0.5821`, `mean_solve_rate=0.5317`
    - `in_interval`: `hard_frac=0.0152`, `easy_frac=0.3182`, `band_frac=0.6667`, `mean_solve_rate=0.5346`
  - interpretation:
    - this pass clearly helped overall: the easy tail dropped from `0.385` to `0.340`, the hard tail dropped from `0.075` to `0.035`, and the band rose from `0.540` to `0.625`
    - `above_threshold` benefited the most
    - `below_threshold` improved more modestly and is now the main remaining problem variant
    - `in_interval` was already the healthiest variant and stayed roughly stable
- attempted iter2 answer-range hardening:
  - params override: `{"mark_count_min": 7, "mark_count_max": 10, "target_answer_min": 2, "target_answer_max": 8, "task_variant_overrides": {"above_threshold": {"target_answer_min": 3, "target_answer_max": 8}, "below_threshold": {"target_answer_min": 4, "target_answer_max": 8, "scene_variant_overrides": {"area": {"target_answer_min": 6, "target_answer_max": 8}, "bar": {"target_answer_min": 6, "target_answer_max": 8}, "dot_plot": {"target_answer_min": 6, "target_answer_max": 8}, "lollipop": {"target_answer_min": 6, "target_answer_max": 8}}}}}`
  - result: rejected before probing because distribution failed
  - failure summary:
    - overall `unique=7`, `max_answer=57/200 (0.285)`
    - `above_threshold`: `unique=3`, `max_answer=33/67 (0.493)`
    - `below_threshold`: `unique=4`, `max_answer=34/67 (0.507)`
  - interpretation:
    - direct answer-range narrowing is too strong for this task because it collapses answer diversity before it improves rollout behavior
- iteration 2b scene-specific mark-count hardening:
  - params override: `{"mark_count_min": 7, "mark_count_max": 10, "target_answer_min": 2, "target_answer_max": 8, "task_variant_overrides": {"above_threshold": {"scene_variant_overrides": {"donut": {"mark_count_min": 8, "mark_count_max": 8}, "dot_plot": {"mark_count_min": 9, "mark_count_max": 10}, "horizontal_bar": {"mark_count_min": 9, "mark_count_max": 10}}}, "below_threshold": {"scene_variant_overrides": {"area": {"mark_count_min": 9, "mark_count_max": 10}, "bar": {"mark_count_min": 9, "mark_count_max": 10}, "dot_plot": {"mark_count_min": 9, "mark_count_max": 10}, "lollipop": {"mark_count_min": 9, "mark_count_max": 10}}}}}`
  - exact set:
    - parquet: `out/calibration/task_charts_counting_value_count_probe_200_iter2b.parquet`
    - dataset root: `out/calibration/datasets/blake3:b534605b252c44c748d419962932140a94500e147e1803291d01df0a2c66e4e0`
    - distribution report: `out/calibration/task_charts_counting_value_count_probe_200_iter2b.parquet.distribution_report.json`
  - overall result:
    - `hard_frac=0.0550`
    - `easy_frac=0.3150`
    - `band_frac=0.6300`
    - `mean_solve_rate=0.5119`
  - by variant:
    - `above_threshold`: `hard_frac=0.0448`, `easy_frac=0.3433`, `band_frac=0.6119`, `mean_solve_rate=0.4879`
    - `below_threshold`: `hard_frac=0.1045`, `easy_frac=0.3134`, `band_frac=0.5821`, `mean_solve_rate=0.5452`
    - `in_interval`: `hard_frac=0.0152`, `easy_frac=0.2879`, `band_frac=0.6970`, `mean_solve_rate=0.5024`
  - interpretation:
    - this pass slightly improved the easy tail and total band fraction relative to iter1
    - it also pushed the hard tail back up, mainly by hurting `below_threshold`
    - scene-specific mark-count hardening is therefore not a robust next lever for this task
- iteration 3 threshold-equality hardening:
  - params override: `{"mark_count_min": 7, "mark_count_max": 10, "target_answer_min": 2, "target_answer_max": 8, "task_variant_overrides": {"above_threshold": {"threshold_equal_count_min": 1, "threshold_equal_count_max": 2, "threshold_opposite_count_min": 1}, "below_threshold": {"threshold_equal_count_min": 1, "threshold_equal_count_max": 2, "threshold_opposite_count_min": 1}}}`
  - exact set:
    - parquet: `out/calibration/task_charts_counting_value_count_probe_200_iter3.parquet`
    - dataset root: `out/calibration/datasets/blake3:24bda011d1059e8a70390ecbcf66c43426c6aeab34a6063bd681eb4a1d7ab7a3`
    - distribution report: `out/calibration/task_charts_counting_value_count_probe_200_iter3.parquet.distribution_report.json`
  - overall result:
    - `hard_frac=0.0600`
    - `easy_frac=0.3350`
    - `band_frac=0.6050`
    - `mean_solve_rate=0.5156`
  - by variant:
    - `above_threshold`: `hard_frac=0.0448`, `easy_frac=0.3134`, `band_frac=0.6418`, `mean_solve_rate=0.4701`
    - `below_threshold`: `hard_frac=0.1045`, `easy_frac=0.4030`, `band_frac=0.4925`, `mean_solve_rate=0.5569`
    - `in_interval`: `hard_frac=0.0303`, `easy_frac=0.2879`, `band_frac=0.6818`, `mean_solve_rate=0.5199`
  - interpretation:
    - the stricter threshold construction helped `above_threshold` a little by lowering its easy tail
    - it hurt `below_threshold` enough that the task got worse overall than iter1
    - the current best checkpoint therefore remains iter1, not iter3
- iteration 4 `below_threshold`-specific near-threshold clutter:
  - params override: `{"mark_count_min": 7, "mark_count_max": 10, "target_answer_min": 2, "target_answer_max": 8, "task_variant_overrides": {"below_threshold": {"threshold_equal_count_min": 1, "threshold_equal_count_max": 1, "threshold_adjacent_below_count_min": 1, "threshold_adjacent_below_count_max": 2, "threshold_opposite_count_min": 1}}}`
  - exact set:
    - parquet: `out/calibration/task_charts_counting_value_count_probe_200_iter4.parquet`
    - dataset root: `out/calibration/datasets/blake3:475e20ac2026824761e97379eddc51d5909e2ea35846a4b5056323b0acfa2f69`
    - distribution report: `out/calibration/task_charts_counting_value_count_probe_200_iter4.parquet.distribution_report.json`
  - overall result:
    - `hard_frac=0.0550`
    - `easy_frac=0.3500`
    - `band_frac=0.5950`
    - `mean_solve_rate=0.5320`
  - by variant:
    - `above_threshold`: `hard_frac=0.0746`, `easy_frac=0.4328`, `band_frac=0.4925`, `mean_solve_rate=0.5630`
    - `below_threshold`: `hard_frac=0.0758`, `easy_frac=0.3485`, `band_frac=0.5758`, `mean_solve_rate=0.5388`
    - `in_interval`: `hard_frac=0.0149`, `easy_frac=0.2687`, `band_frac=0.7164`, `mean_solve_rate=0.4944`
  - query-trace note for `below_threshold`:
    - `mean_threshold_equal_count=0.5455`
    - `mean_threshold_adjacent_below_count=1.0909`
  - interpretation:
    - this redesign did not fix `below_threshold`; it only traded a small amount of easy-tail mass for more hard-tail mass
    - it also left `above_threshold` softer than the current best iter1 checkpoint
    - the current best checkpoint therefore still remains iter1, not iter4
- iteration 5 widened mark-count support to `12`:
  - params override: `{"mark_count_min": 7, "mark_count_max": 12, "target_answer_min": 2, "target_answer_max": 8}`
  - exact set:
    - parquet: `out/calibration/task_charts_counting_value_count_probe_200_iter5_mark12.parquet`
    - dataset root: `out/calibration/datasets/blake3:e1090a49c07694c68febbe0553ab946b88a03484a429e92146e120ec1925d217`
    - distribution report: `out/calibration/task_charts_counting_value_count_probe_200_iter5_mark12.parquet.distribution_report.json`
  - overall result:
    - `hard_frac=0.0600`
    - `easy_frac=0.3750`
    - `band_frac=0.5650`
    - `mean_solve_rate=0.5484`
  - by variant:
    - `above_threshold`: `hard_frac=0.0435`, `easy_frac=0.4348`, `band_frac=0.5217`, `mean_solve_rate=0.5856`
    - `below_threshold`: `hard_frac=0.1129`, `easy_frac=0.3871`, `band_frac=0.5000`, `mean_solve_rate=0.5585`
    - `in_interval`: `hard_frac=0.0290`, `easy_frac=0.3043`, `band_frac=0.6667`, `mean_solve_rate=0.5023`
  - by realized `mark_count`:
    - `7`: `hard_frac=0.0893`, `easy_frac=0.3214`, `band_frac=0.5893`
    - `8`: `hard_frac=0.0816`, `easy_frac=0.3265`, `band_frac=0.5918`
    - `9`: `hard_frac=0.0476`, `easy_frac=0.3810`, `band_frac=0.5714`
    - `10`: `hard_frac=0.0357`, `easy_frac=0.5000`, `band_frac=0.4643`
    - `11`: `hard_frac=0.0500`, `easy_frac=0.5000`, `band_frac=0.4500`
    - `12`: `hard_frac=0.0000`, `easy_frac=0.3462`, `band_frac=0.6538`
  - interpretation:
    - widening the maximum support beyond `10` did not improve the task overall; it raised both mean solve rate and easy-tail mass relative to iter1
    - higher `mark_count` is not a clean monotonic hardness knob here: `10` and `11` were actually among the easiest settings in this run, while `12` looked healthier
    - the current best checkpoint therefore still remains iter1, not iter5
- update this file after every iteration; keep the 2B reference file unchanged

## Probe Log

| Date | Model | Samples | Rollouts | Hard frac | Easy frac | Band frac | Mean solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.075 | 0.385 | 0.540 | 0.549 | fail: valid baseline, but too easy overall; next step is targeted hardening rather than immediate redesign |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.035 | 0.340 | 0.625 | 0.517 | fail, but improved materially: keep the task and move to a second pass focused on `below_threshold` and the easiest scene combinations |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 0 | n/a | n/a | n/a | n/a | attempted answer-range-focused iter2 failed TRACE distribution, so the task set was rejected before model probing |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.055 | 0.315 | 0.630 | 0.512 | mixed: modest easy-tail improvement over iter1, but hard tail regressed; next step should change threshold construction rather than keep pushing mark counts |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.060 | 0.335 | 0.605 | 0.516 | mixed-negative: threshold-equality hardening helped `above_threshold` slightly but hurt `below_threshold`; iter1 remains the best working baseline |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.055 | 0.350 | 0.595 | 0.532 | mixed-negative: `below_threshold`-specific near-threshold clutter passed distribution but still did not beat iter1; keep iter1 as the best checkpoint |
| 2026-04-23 | Qwen/Qwen3-VL-8B-Instruct | 200 | 32 | 0.060 | 0.375 | 0.565 | 0.548 | mixed-negative: widening `mark_count_max` to `12` did not help overall; keep iter1 as the best checkpoint |

## Next Action

- define the first hardening pass with variant/scene-aware knobs:
  - freeze the task at the iter1 code/config state for now and move to the next charts task
  - preserve the iteration 1 global answer-range hardening as the current best working baseline
  - do not keep narrowing answer ranges directly unless distribution is checked first; the first iter2 attempt showed that answer-diversity collapse becomes the limiting factor
  - stop using scene-specific `mark_count` increases as the main lever; iter2b showed that they move tails inconsistently and can hurt `below_threshold`
  - the symmetric threshold-equality hardening from iter3 is not the right next lever because it hurts `below_threshold`
  - the `below_threshold`-specific near-threshold clutter from iter4 is also not sufficient; it does not improve the task beyond iter1
  - simply increasing `mark_count_max` beyond `10` is also not a reliable fix; iter5 with `[7,12]` got worse overall and showed non-monotonic difficulty by realized `mark_count`
  - if we continue on this task, the next change should be a stronger semantic redesign of `above_threshold` and `below_threshold`, not another small threshold-allocation tweak
  - keep `in_interval` as the anchor variant because it consistently has the healthiest band fraction
