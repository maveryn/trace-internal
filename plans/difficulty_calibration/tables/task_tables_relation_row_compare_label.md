# task_tables_relation_row_compare_label

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/tables/relation/row_compare_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.7038`
- zero_solve_rate: `0.0375`
- perfect_solve_rate: `0.4383`
- mean_task_reward: `0.7038`
- mean_overall_reward: `0.7334`
- mean_format_reward: `0.9995`
- mean_prompt_length: `160.0234`
- mean_generated_tokens: `36.9743`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `152` / `0.1187`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `361` / `0.2820`
- high_count / high_frac (`solve_rate > 0.75`): `767` / `0.5992`
- omitted_count / omitted_frac: `919` / `0.7180`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.7038 | 0.0375 | 0.4383 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
