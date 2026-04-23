# task_tables_counting_value_count

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `review`
- task_module: `trace/tasks/tables/counting/value_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5190`
- zero_solve_rate: `0.0031`
- perfect_solve_rate: `0.0141`
- mean_task_reward: `0.5190`
- mean_overall_reward: `0.5323`
- mean_format_reward: `0.6519`
- mean_prompt_length: `152.1352`
- mean_generated_tokens: `155.4795`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `71` / `0.0555`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `943` / `0.7367`
- high_count / high_frac (`solve_rate > 0.75`): `266` / `0.2078`
- omitted_count / omitted_frac: `337` / `0.2633`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5190 | 0.0031 | 0.0141 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
