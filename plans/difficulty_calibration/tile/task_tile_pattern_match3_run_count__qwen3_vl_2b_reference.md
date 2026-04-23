# task_tile_pattern_match3_run_count

## Metadata

- domain: `tile`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/tile/pattern_match3_run_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1948`
- zero_solve_rate: `0.0508`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1948`
- mean_overall_reward: `0.2225`
- mean_format_reward: `0.4720`
- mean_prompt_length: `158.9578`
- mean_generated_tokens: `596.8490`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `457` / `0.3570`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `814` / `0.6359`
- high_count / high_frac (`solve_rate > 0.75`): `9` / `0.0070`
- omitted_count / omitted_frac: `466` / `0.3641`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1948 | 0.0508 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
