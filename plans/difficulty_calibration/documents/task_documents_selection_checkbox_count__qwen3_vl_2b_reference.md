# task_documents_selection_checkbox_count

## Metadata

- domain: `documents`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/documents/selection/checkbox_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5080`
- zero_solve_rate: `0.2109`
- perfect_solve_rate: `0.2352`
- mean_task_reward: `0.5080`
- mean_overall_reward: `0.5567`
- mean_format_reward: `0.9951`
- mean_prompt_length: `142.3359`
- mean_generated_tokens: `8.4756`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `460` / `0.3594`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `277` / `0.2164`
- high_count / high_frac (`solve_rate > 0.75`): `543` / `0.4242`
- omitted_count / omitted_frac: `1003` / `0.7836`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5080 | 0.2109 | 0.2352 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
