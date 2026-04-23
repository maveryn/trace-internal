# task_tables_statistics_filtered_subset_label

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/tables/statistics/filtered_subset_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5497`
- zero_solve_rate: `0.0250`
- perfect_solve_rate: `0.0281`
- mean_task_reward: `0.5497`
- mean_overall_reward: `0.5932`
- mean_format_reward: `0.9849`
- mean_prompt_length: `170.4117`
- mean_generated_tokens: `200.5592`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `81` / `0.0633`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `852` / `0.6656`
- high_count / high_frac (`solve_rate > 0.75`): `347` / `0.2711`
- omitted_count / omitted_frac: `428` / `0.3344`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5497 | 0.0250 | 0.0281 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
