# task_geometry_comparison_value

## Metadata

- domain: `geometry`
- status: `not_started`
- calibration_direction: `review`
- task_module: `trace/tasks/geometry/comparison/value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2738`
- zero_solve_rate: `0.0375`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.2738`
- mean_overall_reward: `0.3264`
- mean_format_reward: `0.8001`
- mean_prompt_length: `121.9867`
- mean_generated_tokens: `498.7179`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `285` / `0.2227`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `969` / `0.7570`
- high_count / high_frac (`solve_rate > 0.75`): `26` / `0.0203`
- omitted_count / omitted_frac: `311` / `0.2430`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2738 | 0.0375 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
