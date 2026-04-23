# task_documents_readout_field_value

## Metadata

- domain: `documents`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/documents/readout/field_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.9681`
- zero_solve_rate: `0.0203`
- perfect_solve_rate: `0.9320`
- mean_task_reward: `0.9681`
- mean_overall_reward: `0.9713`
- mean_format_reward: `1.0000`
- mean_prompt_length: `140.6539`
- mean_generated_tokens: `12.0356`
- max_generated_tokens: `29`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `30` / `0.0234`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `16` / `0.0125`
- high_count / high_frac (`solve_rate > 0.75`): `1234` / `0.9641`
- omitted_count / omitted_frac: `1264` / `0.9875`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.9681 | 0.0203 | 0.9320 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
