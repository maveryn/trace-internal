# task_documents_relation_section_extremum_value

## Metadata

- domain: `documents`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/documents/relation/section_extremum_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.8230`
- zero_solve_rate: `0.0586`
- perfect_solve_rate: `0.7172`
- mean_task_reward: `0.8230`
- mean_overall_reward: `0.8407`
- mean_format_reward: `0.9999`
- mean_prompt_length: `161.3195`
- mean_generated_tokens: `13.3294`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `147` / `0.1148`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `133` / `0.1039`
- high_count / high_frac (`solve_rate > 0.75`): `1000` / `0.7812`
- omitted_count / omitted_frac: `1147` / `0.8961`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.8230 | 0.0586 | 0.7172 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
