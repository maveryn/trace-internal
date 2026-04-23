# task_geometry_measurement_value

## Metadata

- domain: `geometry`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/geometry/measurement/value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2344`
- zero_solve_rate: `0.1961`
- perfect_solve_rate: `0.0039`
- mean_task_reward: `0.2344`
- mean_overall_reward: `0.2815`
- mean_format_reward: `0.7054`
- mean_prompt_length: `127.6359`
- mean_generated_tokens: `289.8283`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `583` / `0.4555`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `613` / `0.4789`
- high_count / high_frac (`solve_rate > 0.75`): `84` / `0.0656`
- omitted_count / omitted_frac: `667` / `0.5211`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2344 | 0.1961 | 0.0039 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
