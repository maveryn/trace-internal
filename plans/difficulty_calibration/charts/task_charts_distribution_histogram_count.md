# task_charts_distribution_histogram_count

## Metadata

- domain: `charts`
- status: `baseline_measured`
- owner: ``
- active_calibration_model: `Qwen/Qwen3-VL-8B-Instruct`
- probe_size: `200`
- rollouts_per_prompt: `32`
- task_module: `trace/tasks/charts/distribution/histogram_count.py`
- 2b_reference_file: [task_charts_distribution_histogram_count__qwen3_vl_2b_reference.md](task_charts_distribution_histogram_count__qwen3_vl_2b_reference.md)

## Reference Context

- the linked 2B reference file records the historical `Qwen/Qwen3-VL-2B-Instruct` probe numbers
- use it only as context for task behavior and tail shape
- the active baseline for calibration must come from a fresh `Qwen/Qwen3-VL-8B-Instruct` probe on newly generated `200` samples

## Recorded Baseline Task Parameters

- scene_variant: `histogram`
- task_variants: `modal_bin_count | interval_mass | cumulative_count_to_bin`
- bin_count_range: `4..7`
- bin_width_range: `2..4`
- bin_start_range: `0..12`
- bin_frequency_range: `1..12`
- balanced_task_variant_sampling: `true`
- task_variant_weights:
  - `modal_bin_count: 1.0`
  - `interval_mass: 1.0`
  - `cumulative_count_to_bin: 1.0`

## Working Baseline

- status: `recorded_baseline`
- baseline_replacement_needed: `yes`
- rationale: `fresh 8B baseline is overwhelmingly saturated; all variants have easy_frac >= 0.89 and no hard tail`
- params_override: `{}`

## Distribution Validation

- status: `pass`
- requirement: generated calibration samples must satisfy TRACE task-distribution and answer-support checks before model evaluation
- workflow reference: `docs/workflows/BUILD_VALIDATION.md`
- suggested command: `PYTHONPATH=. python scripts/run_task_review.py --tasks task_charts_distribution_histogram_count --mode distribution`
- notes:
  - fresh `200`-sample exact set passed overall distribution checks
  - overall answer support: `unique=21`, `max_answer_freq=23/200 (0.115)`
  - report: [task_charts_distribution_histogram_count_probe_200.parquet.distribution_report.json](/home/jovyan/work/trace/out/calibration/task_charts_distribution_histogram_count_probe_200.parquet.distribution_report.json)

## Floor Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded or working baseline | pending |
| `1` | raise minimum difficulty | pending |
| `2` | aggressively raise minimum difficulty | pending |

## Ceiling Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded or working baseline | pending |
| `1` | lower maximum difficulty | pending |
| `2` | aggressively lower maximum difficulty | pending |

## 8B Baseline Probe

- status: `completed`
- prompt_count: `200`
- rollout_count: `6400`
- hard_frac (`solve_rate == 0`): `0.0000`
- easy_frac (`solve_rate >= 0.8`): `0.9300`
- band_frac (`0 < solve_rate < 0.8`): `0.0700`
- mean_solve_rate: `0.9558`
- probe summary: [summary.json](/home/jovyan/work/trace/rlvr/outputs/curriculum_probe/task_charts_distribution_histogram_count_probe_200_qwen3vl8b_iter0/summary.json)

### Per-variant 8B baseline

- `modal_bin_count`
  - `n=67`
  - `hard_frac=0.0000`
  - `easy_frac=0.9701`
  - `band_frac=0.0299`
  - `mean_solve_rate=0.9795`
- `interval_mass`
  - `n=67`
  - `hard_frac=0.0000`
  - `easy_frac=0.9254`
  - `band_frac=0.0746`
  - `mean_solve_rate=0.9380`
- `cumulative_count_to_bin`
  - `n=66`
  - `hard_frac=0.0000`
  - `easy_frac=0.8939`
  - `band_frac=0.1061`
  - `mean_solve_rate=0.9498`

### By realized bin count

- `4`: `n=48`, `easy_frac=0.9375`, `band_frac=0.0625`, `mean_solve_rate=0.9583`
- `5`: `n=47`, `easy_frac=0.8723`, `band_frac=0.1277`, `mean_solve_rate=0.9355`
- `6`: `n=52`, `easy_frac=0.9423`, `band_frac=0.0577`, `mean_solve_rate=0.9579`
- `7`: `n=53`, `easy_frac=0.9623`, `band_frac=0.0377`, `mean_solve_rate=0.9693`

## Working Notes

- start from a fresh `200 x 32` `Qwen/Qwen3-VL-8B-Instruct` probe
- baseline is saturated across all variants and bin counts:
  - no low-solve/hard tail
  - easy tail is `0.93` overall
  - increasing bin count within the current `4..7` support does not appear to be an effective standalone lever
- this task likely needs stronger query semantics, not only larger histograms
- update this file after every iteration; keep the 2B reference file unchanged

## Probe Log

| Date | Model | Samples | Rollouts | Hard frac | Easy frac | Band frac | Mean solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2026-04-23 | `Qwen/Qwen3-VL-8B-Instruct` | 200 | 32 | 0.0000 | 0.9300 | 0.0700 | 0.9558 | baseline measured; task is too easy across all variants |

## Next Action

- define a hardening/redesign pass:
  - retire or downweight `modal_bin_count` unless it becomes relational rather than direct max lookup
  - make `interval_mass` and `cumulative_count_to_bin` require more bins and less obvious arithmetic
  - consider new variants that combine histogram evidence with a threshold or comparison instead of direct readout/sum
