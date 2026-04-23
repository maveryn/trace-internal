# task_diagrams_schematic_callout_target_label

## Metadata

- domain: `diagrams`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/diagrams/schematic/callout_target_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.8447`
- zero_solve_rate: `0.0086`
- perfect_solve_rate: `0.5992`
- mean_task_reward: `0.8447`
- mean_overall_reward: `0.8602`
- mean_format_reward: `0.9997`
- mean_prompt_length: `144.0766`
- mean_generated_tokens: `6.0891`
- max_generated_tokens: `527`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `42` / `0.0328`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `247` / `0.1930`
- high_count / high_frac (`solve_rate > 0.75`): `991` / `0.7742`
- omitted_count / omitted_frac: `1033` / `0.8070`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.8447 | 0.0086 | 0.5992 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
