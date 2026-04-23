# task_icons_relation_mirror_symmetry

## Metadata

- domain: `icons`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/icons/relation/mirror_symmetry.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1573`
- zero_solve_rate: `0.2258`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1573`
- mean_overall_reward: `0.2099`
- mean_format_reward: `0.6835`
- mean_prompt_length: `158.1687`
- mean_generated_tokens: `476.9625`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `796` / `0.6219`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `470` / `0.3672`
- high_count / high_frac (`solve_rate > 0.75`): `14` / `0.0109`
- omitted_count / omitted_frac: `810` / `0.6328`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1573 | 0.2258 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
