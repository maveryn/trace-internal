# task_charts_statistics_summary_label

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/charts/statistics/summary_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.7037`
- zero_solve_rate: `0.0555`
- perfect_solve_rate: `0.4430`
- mean_task_reward: `0.7037`
- mean_overall_reward: `0.7312`
- mean_format_reward: `0.9789`
- mean_prompt_length: `151.0102`
- mean_generated_tokens: `71.6824`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `166` / `0.1297`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `327` / `0.2555`
- high_count / high_frac (`solve_rate > 0.75`): `787` / `0.6148`
- omitted_count / omitted_frac: `953` / `0.7445`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.7037 | 0.0555 | 0.4430 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
