# task_graph_counting_degree_count

## Metadata

- domain: `graph`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/graph/counting/degree_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1931`
- zero_solve_rate: `0.2477`
- perfect_solve_rate: `0.0078`
- mean_task_reward: `0.1931`
- mean_overall_reward: `0.2375`
- mean_format_reward: `0.6363`
- mean_prompt_length: `122.7422`
- mean_generated_tokens: `139.0896`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `710` / `0.5547`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `496` / `0.3875`
- high_count / high_frac (`solve_rate > 0.75`): `74` / `0.0578`
- omitted_count / omitted_frac: `784` / `0.6125`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1931 | 0.2477 | 0.0078 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
