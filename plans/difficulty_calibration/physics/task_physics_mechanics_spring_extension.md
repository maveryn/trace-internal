# task_physics_mechanics_spring_extension

## Metadata

- domain: `physics`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/physics/mechanics/spring_extension.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1790`
- zero_solve_rate: `0.1672`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1790`
- mean_overall_reward: `0.2434`
- mean_format_reward: `0.8237`
- mean_prompt_length: `168.8336`
- mean_generated_tokens: `260.7037`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `653` / `0.5102`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `624` / `0.4875`
- high_count / high_frac (`solve_rate > 0.75`): `3` / `0.0023`
- omitted_count / omitted_frac: `656` / `0.5125`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1790 | 0.1672 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
