# task_charts_distribution_density_label

## Metadata

- domain: `charts`
- status: `baseline_measured`
- owner: ``
- active_calibration_model: `Qwen/Qwen3-VL-8B-Instruct`
- probe_size: `200`
- rollouts_per_prompt: `32`
- task_module: `trace/tasks/charts/distribution/density_label.py`
- 2b_reference_file: [task_charts_distribution_density_label__qwen3_vl_2b_reference.md](task_charts_distribution_density_label__qwen3_vl_2b_reference.md)

## Reference Context

- the linked 2B reference file records the historical `Qwen/Qwen3-VL-2B-Instruct` probe numbers
- use it only as context for task behavior and tail shape
- the active baseline for calibration must come from a fresh `Qwen/Qwen3-VL-8B-Instruct` probe on newly generated `200` samples

## Recorded Baseline Task Parameters

- scene_variant: `violin`
- task_variants: `highest_mode | lowest_mode | bimodal_label`
- category_count_range: `4..7`
- value_range: `1..20`
- balanced_task_variant_sampling: `true`
- task_variant_weights:
  - `highest_mode: 1.0`
  - `lowest_mode: 1.0`
  - `bimodal_label: 1.0`

## Working Baseline

- status: `recorded_baseline`
- baseline_replacement_needed: `yes`
- rationale: `the fresh 8B baseline has a split-tail failure: highest_mode and lowest_mode are overwhelmingly easy, while bimodal_label is too hard; the next pass should tune both sides separately from the recorded baseline`
- params_override: `{}`

## Distribution Validation

- status: `pass`
- requirement: generated calibration samples must satisfy TRACE task-distribution and answer-support checks before model evaluation
- workflow reference: `docs/workflows/BUILD_VALIDATION.md`
- suggested command: `PYTHONPATH=. python scripts/run_task_review.py --tasks task_charts_distribution_density_label --mode distribution`
- notes:
  - fresh `200`-sample exact set passed overall distribution checks
  - overall answer support: `unique=24`, `max_answer_freq=15/200 (0.075)`
  - report: [task_charts_distribution_density_label_probe_200.parquet.distribution_report.json](/home/jovyan/work/trace/out/calibration/task_charts_distribution_density_label_probe_200.parquet.distribution_report.json)

## Floor Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded or working baseline | `{}` |
| `1` | first split-tail pass: harden `highest_mode` / `lowest_mode`, soften `bimodal_label` | `{"task_variant_overrides":{"highest_mode":{"violin_category_count_min":6,"violin_category_count_max":7,"mode_window_size_min":7,"mode_window_size_max":7,"extreme_winner_gap_min":1,"extreme_winner_gap_max":1},"lowest_mode":{"violin_category_count_min":6,"violin_category_count_max":7,"mode_window_size_min":7,"mode_window_size_max":7,"extreme_winner_gap_min":1,"extreme_winner_gap_max":1},"bimodal_label":{"violin_category_count_min":4,"violin_category_count_max":5,"bimodal_mode_separation_min":5,"bimodal_mode_separation_max":7,"bimodal_distractor_clearance_min":2,"bimodal_distractor_clearance_max":3}}}` |
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
- hard_frac (`solve_rate == 0`): `0.2350`
- easy_frac (`solve_rate >= 0.8`): `0.6300`
- band_frac (`0 < solve_rate < 0.8`): `0.1350`
- mean_solve_rate: `0.6641`
- probe summary: [summary.json](/home/jovyan/work/trace/rlvr/outputs/curriculum_probe/task_charts_distribution_density_label_probe_200_qwen3vl8b_iter0/summary.json)

### Per-variant 8B baseline

- `bimodal_label`
  - `n=66`
  - `hard_frac=0.4091`
  - `easy_frac=0.3485`
  - `band_frac=0.2424`
  - `mean_solve_rate=0.3958`
- `highest_mode`
  - `n=67`
  - `hard_frac=0.2090`
  - `easy_frac=0.7612`
  - `band_frac=0.0299`
  - `mean_solve_rate=0.7743`
- `lowest_mode`
  - `n=67`
  - `hard_frac=0.0896`
  - `easy_frac=0.7761`
  - `band_frac=0.1343`
  - `mean_solve_rate=0.8181`

## Working Notes

- start from a fresh `200 x 32` `Qwen/Qwen3-VL-8B-Instruct` probe
- baseline tail shape is split:
  - `highest_mode` and `lowest_mode` are much too easy
  - `bimodal_label` is too hard
- this task should not get a uniform harder/easier pass first; it needs variant-specific floor and ceiling tuning
- first split-tail pass did not help:
  - `bimodal_label` over-corrected from too hard to too easy
  - `highest_mode` is still heavily saturated
- second split-tail pass targeted only `highest_mode` / `lowest_mode`
  - this reduced the easy tail materially
  - but it raised the hard tail too much, so it is not a clean retained checkpoint either
- current best checkpoint remains the recorded baseline (`iter0`)
- update this file after every iteration; keep the 2B reference file unchanged

## Probe Log

| Date | Model | Samples | Rollouts | Hard frac | Easy frac | Band frac | Mean solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2026-04-23 | `Qwen/Qwen3-VL-8B-Instruct` | 200 | 32 | 0.2350 | 0.6300 | 0.1350 | 0.6641 | baseline measured; next pass must harden `highest_mode` / `lowest_mode` and soften `bimodal_label` |
| 2026-04-23 | `Qwen/Qwen3-VL-8B-Instruct` + split-tail iter1 | 200 | 32 | 0.1850 | 0.7150 | 0.1000 | 0.7380 | reject; softened `bimodal_label` too much and did not reduce `highest_mode` enough |
| 2026-04-23 | `Qwen/Qwen3-VL-8B-Instruct` + split-tail iter2 | 200 | 32 | 0.3400 | 0.5200 | 0.1400 | 0.5469 | reject as retained checkpoint; reduced easy tail, but hard tail rose too much |

## Next Action

- if we continue on this task:
  - keep `bimodal_label` at or near the recorded baseline
  - focus only on `highest_mode` / `lowest_mode`
  - avoid pure count/window tightening, since iter2 mainly converted easy mass into hard mass
  - next likely move is a semantic redesign of the extreme-mode queries rather than more structural squeezing
