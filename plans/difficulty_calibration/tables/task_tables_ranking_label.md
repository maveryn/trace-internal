# task_tables_ranking_label

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/tables/ranking/label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1877`
- zero_solve_rate: `0.1609`
- perfect_solve_rate: `0.0063`
- mean_task_reward: `0.1877`
- mean_overall_reward: `0.2674`
- mean_format_reward: `0.9840`
- mean_prompt_length: `156.8953`
- mean_generated_tokens: `43.1622`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `652` / `0.5094`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `572` / `0.4469`
- high_count / high_frac (`solve_rate > 0.75`): `56` / `0.0437`
- omitted_count / omitted_frac: `708` / `0.5531`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1877 | 0.1609 | 0.0063 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
