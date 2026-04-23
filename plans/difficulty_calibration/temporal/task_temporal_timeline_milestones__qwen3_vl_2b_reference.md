# task_temporal_timeline_milestones

## Metadata

- domain: `temporal`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/temporal/timeline/milestones.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2810`
- zero_solve_rate: `0.3336`
- perfect_solve_rate: `0.1328`
- mean_task_reward: `0.2810`
- mean_overall_reward: `0.3364`
- mean_format_reward: `0.8351`
- mean_prompt_length: `152.0000`
- mean_generated_tokens: `19.9374`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `803` / `0.6273`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `167` / `0.1305`
- high_count / high_frac (`solve_rate > 0.75`): `310` / `0.2422`
- omitted_count / omitted_frac: `1113` / `0.8695`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2810 | 0.3336 | 0.1328 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
