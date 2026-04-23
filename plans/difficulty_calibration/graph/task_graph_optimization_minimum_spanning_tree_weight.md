# task_graph_optimization_minimum_spanning_tree_weight

## Metadata

- domain: `graph`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/graph/optimization/minimum_spanning_tree_weight.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.0134`
- zero_solve_rate: `0.7320`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.0134`
- mean_overall_reward: `0.0195`
- mean_format_reward: `0.0746`
- mean_prompt_length: `134.7648`
- mean_generated_tokens: `943.3100`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `1255` / `0.9805`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `25` / `0.0195`
- high_count / high_frac (`solve_rate > 0.75`): `0` / `0.0000`
- omitted_count / omitted_frac: `1255` / `0.9805`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.0134 | 0.7320 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
