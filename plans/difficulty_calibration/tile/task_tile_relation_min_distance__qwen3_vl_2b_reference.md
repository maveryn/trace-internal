# task_tile_relation_min_distance

## Metadata

- domain: `tile`
- status: `not_started`
- calibration_direction: `review`
- task_module: `trace/tasks/tile/relation_min_distance.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2796`
- zero_solve_rate: `0.0242`
- perfect_solve_rate: `0.0008`
- mean_task_reward: `0.2796`
- mean_overall_reward: `0.3175`
- mean_format_reward: `0.6582`
- mean_prompt_length: `178.8398`
- mean_generated_tokens: `485.2779`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `286` / `0.2234`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `951` / `0.7430`
- high_count / high_frac (`solve_rate > 0.75`): `43` / `0.0336`
- omitted_count / omitted_frac: `329` / `0.2570`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2796 | 0.0242 | 0.0008 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
