# task_graph_relation_same_component_count

## Metadata

- domain: `graph`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/graph/relation/same_component_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2226`
- zero_solve_rate: `0.1406`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.2226`
- mean_overall_reward: `0.2686`
- mean_format_reward: `0.6827`
- mean_prompt_length: `133.8875`
- mean_generated_tokens: `282.8509`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `483` / `0.3773`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `775` / `0.6055`
- high_count / high_frac (`solve_rate > 0.75`): `22` / `0.0172`
- omitted_count / omitted_frac: `505` / `0.3945`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2226 | 0.1406 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
