# task_temporal_clock_readout

## Metadata

- domain: `temporal`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/temporal/clock/readout.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2222`
- zero_solve_rate: `0.2539`
- perfect_solve_rate: `0.0234`
- mean_task_reward: `0.2222`
- mean_overall_reward: `0.2993`
- mean_format_reward: `0.9932`
- mean_prompt_length: `164.6945`
- mean_generated_tokens: `69.2630`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `709` / `0.5539`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `429` / `0.3352`
- high_count / high_frac (`solve_rate > 0.75`): `142` / `0.1109`
- omitted_count / omitted_frac: `851` / `0.6648`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2222 | 0.2539 | 0.0234 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
