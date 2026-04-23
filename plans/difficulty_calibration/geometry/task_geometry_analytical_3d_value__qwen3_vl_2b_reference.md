# task_geometry_analytical_3d_value

## Metadata

- domain: `geometry`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/geometry/analytical_3d/value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.4974`
- zero_solve_rate: `0.1437`
- perfect_solve_rate: `0.0133`
- mean_task_reward: `0.4974`
- mean_overall_reward: `0.5220`
- mean_format_reward: `0.7435`
- mean_prompt_length: `141.2102`
- mean_generated_tokens: `354.3323`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `258` / `0.2016`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `692` / `0.5406`
- high_count / high_frac (`solve_rate > 0.75`): `330` / `0.2578`
- omitted_count / omitted_frac: `588` / `0.4594`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.4974 | 0.1437 | 0.0133 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
