# task_tables_statistics_filtered_subset_value

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/tables/statistics/filtered_subset_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2653`
- zero_solve_rate: `0.0477`
- perfect_solve_rate: `0.0008`
- mean_task_reward: `0.2653`
- mean_overall_reward: `0.3034`
- mean_format_reward: `0.6458`
- mean_prompt_length: `162.9719`
- mean_generated_tokens: `179.5024`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `352` / `0.2750`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `897` / `0.7008`
- high_count / high_frac (`solve_rate > 0.75`): `31` / `0.0242`
- omitted_count / omitted_frac: `383` / `0.2992`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2653 | 0.0477 | 0.0008 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
