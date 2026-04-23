# task_graph_relation_reachable_count

## Metadata

- domain: `graph`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/graph/relation/reachable_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1366`
- zero_solve_rate: `0.2023`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1366`
- mean_overall_reward: `0.1814`
- mean_format_reward: `0.5842`
- mean_prompt_length: `135.7680`
- mean_generated_tokens: `424.2992`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `711` / `0.5555`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `566` / `0.4422`
- high_count / high_frac (`solve_rate > 0.75`): `3` / `0.0023`
- omitted_count / omitted_frac: `714` / `0.5578`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1366 | 0.2023 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
