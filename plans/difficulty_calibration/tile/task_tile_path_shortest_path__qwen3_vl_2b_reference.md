# task_tile_path_shortest_path

## Metadata

- domain: `tile`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/tile/path_shortest_path.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.0513`
- zero_solve_rate: `0.6172`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.0513`
- mean_overall_reward: `0.0825`
- mean_format_reward: `0.3631`
- mean_prompt_length: `183.0727`
- mean_generated_tokens: `696.1081`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `1072` / `0.8375`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `208` / `0.1625`
- high_count / high_frac (`solve_rate > 0.75`): `0` / `0.0000`
- omitted_count / omitted_frac: `1072` / `0.8375`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.0513 | 0.6172 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
