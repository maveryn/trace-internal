# task_diagrams_flow_next_step_label

## Metadata

- domain: `diagrams`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/diagrams/flow/next_step_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.9949`
- zero_solve_rate: `0.0008`
- perfect_solve_rate: `0.9773`
- mean_task_reward: `0.9949`
- mean_overall_reward: `0.9954`
- mean_format_reward: `1.0000`
- mean_prompt_length: `148.0914`
- mean_generated_tokens: `7.1633`
- max_generated_tokens: `152`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `1` / `0.0008`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `9` / `0.0070`
- high_count / high_frac (`solve_rate > 0.75`): `1270` / `0.9922`
- omitted_count / omitted_frac: `1271` / `0.9930`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.9949 | 0.0008 | 0.9773 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
