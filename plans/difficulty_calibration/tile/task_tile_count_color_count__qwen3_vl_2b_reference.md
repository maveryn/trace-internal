# task_tile_count_color_count

## Metadata

- domain: `tile`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/tile/count_color_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2470`
- zero_solve_rate: `0.0813`
- perfect_solve_rate: `0.0094`
- mean_task_reward: `0.2470`
- mean_overall_reward: `0.2950`
- mean_format_reward: `0.7268`
- mean_prompt_length: `149.9406`
- mean_generated_tokens: `359.6286`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `449` / `0.3508`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `772` / `0.6031`
- high_count / high_frac (`solve_rate > 0.75`): `59` / `0.0461`
- omitted_count / omitted_frac: `508` / `0.3969`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2470 | 0.0813 | 0.0094 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
