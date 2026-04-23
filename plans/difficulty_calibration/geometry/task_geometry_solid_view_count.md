# task_geometry_solid_view_count

## Metadata

- domain: `geometry`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/geometry/solid/view_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.0904`
- zero_solve_rate: `0.1484`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.0904`
- mean_overall_reward: `0.1580`
- mean_format_reward: `0.7672`
- mean_prompt_length: `151.6992`
- mean_generated_tokens: `408.2194`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `885` / `0.6914`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `395` / `0.3086`
- high_count / high_frac (`solve_rate > 0.75`): `0` / `0.0000`
- omitted_count / omitted_frac: `885` / `0.6914`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.0904 | 0.1484 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
