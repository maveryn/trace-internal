# task_tables_temporal_value

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/tables/temporal/value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5406`
- zero_solve_rate: `0.0523`
- perfect_solve_rate: `0.2172`
- mean_task_reward: `0.5406`
- mean_overall_reward: `0.5664`
- mean_format_reward: `0.7983`
- mean_prompt_length: `163.6687`
- mean_generated_tokens: `52.6214`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `222` / `0.1734`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `585` / `0.4570`
- high_count / high_frac (`solve_rate > 0.75`): `473` / `0.3695`
- omitted_count / omitted_frac: `695` / `0.5430`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5406 | 0.0523 | 0.2172 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
