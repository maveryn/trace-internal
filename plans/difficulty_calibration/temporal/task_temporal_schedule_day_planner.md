# task_temporal_schedule_day_planner

## Metadata

- domain: `temporal`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/temporal/schedule/day_planner.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1031`
- zero_solve_rate: `0.1742`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1031`
- mean_overall_reward: `0.1596`
- mean_format_reward: `0.6690`
- mean_prompt_length: `147.5875`
- mean_generated_tokens: `419.9134`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `853` / `0.6664`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `427` / `0.3336`
- high_count / high_frac (`solve_rate > 0.75`): `0` / `0.0000`
- omitted_count / omitted_frac: `853` / `0.6664`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1031 | 0.1742 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
