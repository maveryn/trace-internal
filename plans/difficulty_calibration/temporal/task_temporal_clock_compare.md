# task_temporal_clock_compare

## Metadata

- domain: `temporal`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/temporal/clock/compare.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1959`
- zero_solve_rate: `0.1102`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1959`
- mean_overall_reward: `0.2599`
- mean_format_reward: `0.8366`
- mean_prompt_length: `134.4750`
- mean_generated_tokens: `503.9159`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `522` / `0.4078`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `744` / `0.5813`
- high_count / high_frac (`solve_rate > 0.75`): `14` / `0.0109`
- omitted_count / omitted_frac: `536` / `0.4188`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1959 | 0.1102 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
