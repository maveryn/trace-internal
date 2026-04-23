# task_geometry_analytical_2d_value

## Metadata

- domain: `geometry`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/geometry/analytical_2d/value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5135`
- zero_solve_rate: `0.0422`
- perfect_solve_rate: `0.0484`
- mean_task_reward: `0.5135`
- mean_overall_reward: `0.5392`
- mean_format_reward: `0.7709`
- mean_prompt_length: `139.3992`
- mean_generated_tokens: `371.8417`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `159` / `0.1242`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `785` / `0.6133`
- high_count / high_frac (`solve_rate > 0.75`): `336` / `0.2625`
- omitted_count / omitted_frac: `495` / `0.3867`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5135 | 0.0422 | 0.0484 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
