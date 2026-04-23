# task_diagrams_cycle_offset_stage_label

## Metadata

- domain: `diagrams`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/diagrams/cycle/offset_stage_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1526`
- zero_solve_rate: `0.4797`
- perfect_solve_rate: `0.0461`
- mean_task_reward: `0.1526`
- mean_overall_reward: `0.2373`
- mean_format_reward: `0.9995`
- mean_prompt_length: `149.5875`
- mean_generated_tokens: `8.0334`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `919` / `0.7180`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `262` / `0.2047`
- high_count / high_frac (`solve_rate > 0.75`): `99` / `0.0773`
- omitted_count / omitted_frac: `1018` / `0.7953`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1526 | 0.4797 | 0.0461 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
