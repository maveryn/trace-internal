# task_puzzles_spatial_cube_removal_count

## Metadata

- domain: `puzzles`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/puzzles/spatial/cube_removal_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1711`
- zero_solve_rate: `0.0781`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1711`
- mean_overall_reward: `0.2330`
- mean_format_reward: `0.7896`
- mean_prompt_length: `161.8078`
- mean_generated_tokens: `260.9675`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `559` / `0.4367`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `718` / `0.5609`
- high_count / high_frac (`solve_rate > 0.75`): `3` / `0.0023`
- omitted_count / omitted_frac: `562` / `0.4391`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1711 | 0.0781 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
