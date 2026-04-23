# task_diagrams_set_diagram_region_sum_value

## Metadata

- domain: `diagrams`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/diagrams/set_diagram/region_sum_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2463`
- zero_solve_rate: `0.1734`
- perfect_solve_rate: `0.0367`
- mean_task_reward: `0.2463`
- mean_overall_reward: `0.2914`
- mean_format_reward: `0.6974`
- mean_prompt_length: `158.9242`
- mean_generated_tokens: `327.0511`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `696` / `0.5437`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `388` / `0.3031`
- high_count / high_frac (`solve_rate > 0.75`): `196` / `0.1531`
- omitted_count / omitted_frac: `892` / `0.6969`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2463 | 0.1734 | 0.0367 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
