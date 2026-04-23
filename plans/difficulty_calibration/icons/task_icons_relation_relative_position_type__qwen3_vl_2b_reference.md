# task_icons_relation_relative_position_type

## Metadata

- domain: `icons`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/icons/relation/relative_position_type.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1914`
- zero_solve_rate: `0.3625`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1914`
- mean_overall_reward: `0.2691`
- mean_format_reward: `0.9690`
- mean_prompt_length: `156.6484`
- mean_generated_tokens: `37.3574`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `757` / `0.5914`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `454` / `0.3547`
- high_count / high_frac (`solve_rate > 0.75`): `69` / `0.0539`
- omitted_count / omitted_frac: `826` / `0.6453`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1914 | 0.3625 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
