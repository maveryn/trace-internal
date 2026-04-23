# task_temporal_calendar_month_view

## Metadata

- domain: `temporal`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/temporal/calendar/month_view.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2958`
- zero_solve_rate: `0.0680`
- perfect_solve_rate: `0.0023`
- mean_task_reward: `0.2958`
- mean_overall_reward: `0.3510`
- mean_format_reward: `0.8477`
- mean_prompt_length: `144.9281`
- mean_generated_tokens: `100.7002`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `386` / `0.3016`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `813` / `0.6352`
- high_count / high_frac (`solve_rate > 0.75`): `81` / `0.0633`
- omitted_count / omitted_frac: `467` / `0.3648`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2958 | 0.0680 | 0.0023 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
