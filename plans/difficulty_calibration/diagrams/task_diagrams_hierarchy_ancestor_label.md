# task_diagrams_hierarchy_ancestor_label

## Metadata

- domain: `diagrams`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/diagrams/hierarchy/ancestor_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.8358`
- zero_solve_rate: `0.0773`
- perfect_solve_rate: `0.6953`
- mean_task_reward: `0.8358`
- mean_overall_reward: `0.8522`
- mean_format_reward: `0.9997`
- mean_prompt_length: `146.0516`
- mean_generated_tokens: `7.4314`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `141` / `0.1102`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `110` / `0.0859`
- high_count / high_frac (`solve_rate > 0.75`): `1029` / `0.8039`
- omitted_count / omitted_frac: `1170` / `0.9141`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.8358 | 0.0773 | 0.6953 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
