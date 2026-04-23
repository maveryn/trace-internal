# task_documents_layout_section_membership_label

## Metadata

- domain: `documents`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/documents/layout/section_membership_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.7017`
- zero_solve_rate: `0.2367`
- perfect_solve_rate: `0.6461`
- mean_task_reward: `0.7017`
- mean_overall_reward: `0.7314`
- mean_format_reward: `0.9988`
- mean_prompt_length: `153.1117`
- mean_generated_tokens: `6.6371`
- max_generated_tokens: `36`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `341` / `0.2664`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `60` / `0.0469`
- high_count / high_frac (`solve_rate > 0.75`): `879` / `0.6867`
- omitted_count / omitted_frac: `1220` / `0.9531`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.7017 | 0.2367 | 0.6461 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
