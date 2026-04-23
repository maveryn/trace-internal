# task_icons_counting_singleton_type

## Metadata

- domain: `icons`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/icons/counting/singleton_type.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1412`
- zero_solve_rate: `0.3570`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1412`
- mean_overall_reward: `0.1764`
- mean_format_reward: `0.4934`
- mean_prompt_length: `129.2391`
- mean_generated_tokens: `35.5040`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `742` / `0.5797`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `534` / `0.4172`
- high_count / high_frac (`solve_rate > 0.75`): `4` / `0.0031`
- omitted_count / omitted_frac: `746` / `0.5828`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1412 | 0.3570 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
