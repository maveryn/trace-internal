# task_tables_statistics_summary_value

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/tables/statistics/summary_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1987`
- zero_solve_rate: `0.2328`
- perfect_solve_rate: `0.0281`
- mean_task_reward: `0.1987`
- mean_overall_reward: `0.2455`
- mean_format_reward: `0.6672`
- mean_prompt_length: `145.8516`
- mean_generated_tokens: `82.9710`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `690` / `0.5391`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `515` / `0.4023`
- high_count / high_frac (`solve_rate > 0.75`): `75` / `0.0586`
- omitted_count / omitted_frac: `765` / `0.5977`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1987 | 0.2328 | 0.0281 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
