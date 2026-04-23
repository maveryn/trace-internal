# task_physics_mechanics_lever_balance

## Metadata

- domain: `physics`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/physics/mechanics/lever_balance.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2056`
- zero_solve_rate: `0.0930`
- perfect_solve_rate: `0.0008`
- mean_task_reward: `0.2056`
- mean_overall_reward: `0.2661`
- mean_format_reward: `0.8102`
- mean_prompt_length: `156.0258`
- mean_generated_tokens: `269.4668`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `497` / `0.3883`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `763` / `0.5961`
- high_count / high_frac (`solve_rate > 0.75`): `20` / `0.0156`
- omitted_count / omitted_frac: `517` / `0.4039`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2056 | 0.0930 | 0.0008 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
