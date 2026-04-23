# task_icons_pattern_structured_violation

## Metadata

- domain: `icons`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/icons/pattern/structured_violation.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1206`
- zero_solve_rate: `0.1750`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1206`
- mean_overall_reward: `0.1639`
- mean_format_reward: `0.5538`
- mean_prompt_length: `132.7906`
- mean_generated_tokens: `500.8508`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `874` / `0.6828`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `395` / `0.3086`
- high_count / high_frac (`solve_rate > 0.75`): `11` / `0.0086`
- omitted_count / omitted_frac: `885` / `0.6914`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1206 | 0.1750 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
