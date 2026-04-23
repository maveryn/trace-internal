# task_graph_path_shortest_path_length

## Metadata

- domain: `graph`
- status: `not_started`
- calibration_direction: `review`
- task_module: `trace/tasks/graph/path/shortest_path_length.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.3750`
- zero_solve_rate: `0.0563`
- perfect_solve_rate: `0.0008`
- mean_task_reward: `0.3750`
- mean_overall_reward: `0.4183`
- mean_format_reward: `0.8078`
- mean_prompt_length: `143.2648`
- mean_generated_tokens: `270.2329`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `229` / `0.1789`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `964` / `0.7531`
- high_count / high_frac (`solve_rate > 0.75`): `87` / `0.0680`
- omitted_count / omitted_frac: `316` / `0.2469`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.3750 | 0.0563 | 0.0008 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
