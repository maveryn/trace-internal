# task_geometry_counting_value

## Metadata

- domain: `geometry`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/geometry/counting/value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.3228`
- zero_solve_rate: `0.0797`
- perfect_solve_rate: `0.0117`
- mean_task_reward: `0.3228`
- mean_overall_reward: `0.3638`
- mean_format_reward: `0.7329`
- mean_prompt_length: `120.3883`
- mean_generated_tokens: `390.7657`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `373` / `0.2914`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `754` / `0.5891`
- high_count / high_frac (`solve_rate > 0.75`): `153` / `0.1195`
- omitted_count / omitted_frac: `526` / `0.4109`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.3228 | 0.0797 | 0.0117 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
