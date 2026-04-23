# task_icons_counting_reference_match_count

## Metadata

- domain: `icons`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/icons/counting/reference_match_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1094`
- zero_solve_rate: `0.6180`
- perfect_solve_rate: `0.0055`
- mean_task_reward: `0.1094`
- mean_overall_reward: `0.1960`
- mean_format_reward: `0.9754`
- mean_prompt_length: `144.2063`
- mean_generated_tokens: `25.5549`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `997` / `0.7789`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `239` / `0.1867`
- high_count / high_frac (`solve_rate > 0.75`): `44` / `0.0344`
- omitted_count / omitted_frac: `1041` / `0.8133`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1094 | 0.6180 | 0.0055 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
