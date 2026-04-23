# task_icons_counting_size_relation

## Metadata

- domain: `icons`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/icons/counting/size_relation.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1520`
- zero_solve_rate: `0.3867`
- perfect_solve_rate: `0.0016`
- mean_task_reward: `0.1520`
- mean_overall_reward: `0.2254`
- mean_format_reward: `0.8856`
- mean_prompt_length: `136.2328`
- mean_generated_tokens: `28.1833`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `846` / `0.6609`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `391` / `0.3055`
- high_count / high_frac (`solve_rate > 0.75`): `43` / `0.0336`
- omitted_count / omitted_frac: `889` / `0.6945`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1520 | 0.3867 | 0.0016 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
