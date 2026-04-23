# task_tile_count_color_components

## Metadata

- domain: `tile`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/tile/count_color_components.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1368`
- zero_solve_rate: `0.2477`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1368`
- mean_overall_reward: `0.1479`
- mean_format_reward: `0.2481`
- mean_prompt_length: `165.2305`
- mean_generated_tokens: `841.9640`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `693` / `0.5414`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `573` / `0.4477`
- high_count / high_frac (`solve_rate > 0.75`): `14` / `0.0109`
- omitted_count / omitted_frac: `707` / `0.5523`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1368 | 0.2477 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
