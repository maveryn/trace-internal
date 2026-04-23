# task_physics_mechanics_force_diagram

## Metadata

- domain: `physics`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/physics/mechanics/force_diagram.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.3654`
- zero_solve_rate: `0.1078`
- perfect_solve_rate: `0.0055`
- mean_task_reward: `0.3654`
- mean_overall_reward: `0.4143`
- mean_format_reward: `0.8544`
- mean_prompt_length: `146.4039`
- mean_generated_tokens: `216.8620`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `372` / `0.2906`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `751` / `0.5867`
- high_count / high_frac (`solve_rate > 0.75`): `157` / `0.1227`
- omitted_count / omitted_frac: `529` / `0.4133`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.3654 | 0.1078 | 0.0055 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
