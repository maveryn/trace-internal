# task_icons_sequence_missing_count

## Metadata

- domain: `icons`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/icons/sequence/missing_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1232`
- zero_solve_rate: `0.2625`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1232`
- mean_overall_reward: `0.1906`
- mean_format_reward: `0.7972`
- mean_prompt_length: `140.0656`
- mean_generated_tokens: `248.2127`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `821` / `0.6414`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `455` / `0.3555`
- high_count / high_frac (`solve_rate > 0.75`): `4` / `0.0031`
- omitted_count / omitted_frac: `825` / `0.6445`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1232 | 0.2625 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
