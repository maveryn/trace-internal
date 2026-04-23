# task_physics_circuits_equivalent_resistance

## Metadata

- domain: `physics`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/physics/circuits/equivalent_resistance.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2325`
- zero_solve_rate: `0.0922`
- perfect_solve_rate: `0.0008`
- mean_task_reward: `0.2325`
- mean_overall_reward: `0.2731`
- mean_format_reward: `0.6388`
- mean_prompt_length: `173.5586`
- mean_generated_tokens: `411.4973`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `455` / `0.3555`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `809` / `0.6320`
- high_count / high_frac (`solve_rate > 0.75`): `16` / `0.0125`
- omitted_count / omitted_frac: `471` / `0.3680`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2325 | 0.0922 | 0.0008 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
