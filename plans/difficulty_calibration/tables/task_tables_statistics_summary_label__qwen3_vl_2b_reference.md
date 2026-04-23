# task_tables_statistics_summary_label

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/tables/statistics/summary_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.4140`
- zero_solve_rate: `0.1578`
- perfect_solve_rate: `0.1445`
- mean_task_reward: `0.4140`
- mean_overall_reward: `0.4718`
- mean_format_reward: `0.9919`
- mean_prompt_length: `151.3320`
- mean_generated_tokens: `33.4874`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `496` / `0.3875`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `381` / `0.2977`
- high_count / high_frac (`solve_rate > 0.75`): `403` / `0.3148`
- omitted_count / omitted_frac: `899` / `0.7023`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.4140 | 0.1578 | 0.1445 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
