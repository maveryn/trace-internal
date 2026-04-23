# task_tables_relation_extremum_transfer_value

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `review`
- task_module: `trace/tasks/tables/relation/extremum_transfer_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.4499`
- zero_solve_rate: `0.0242`
- perfect_solve_rate: `0.0547`
- mean_task_reward: `0.4499`
- mean_overall_reward: `0.4778`
- mean_format_reward: `0.7288`
- mean_prompt_length: `161.5398`
- mean_generated_tokens: `65.3877`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `186` / `0.1453`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `833` / `0.6508`
- high_count / high_frac (`solve_rate > 0.75`): `261` / `0.2039`
- omitted_count / omitted_frac: `447` / `0.3492`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.4499 | 0.0242 | 0.0547 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
