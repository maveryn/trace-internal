# task_graph_comparison_largest_component_size

## Metadata

- domain: `graph`
- status: `not_started`
- calibration_direction: `review`
- task_module: `trace/tasks/graph/comparison/largest_component_size.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2818`
- zero_solve_rate: `0.0258`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.2818`
- mean_overall_reward: `0.3308`
- mean_format_reward: `0.7720`
- mean_prompt_length: `125.8250`
- mean_generated_tokens: `300.9585`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `251` / `0.1961`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `1007` / `0.7867`
- high_count / high_frac (`solve_rate > 0.75`): `22` / `0.0172`
- omitted_count / omitted_frac: `273` / `0.2133`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2818 | 0.0258 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
