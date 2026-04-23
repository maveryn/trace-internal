# task_charts_composition_subset_value

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/charts/composition/subset_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.7512`
- zero_solve_rate: `0.0086`
- perfect_solve_rate: `0.4773`
- mean_task_reward: `0.7512`
- mean_overall_reward: `0.7631`
- mean_format_reward: `0.8700`
- mean_prompt_length: `139.0711`
- mean_generated_tokens: `58.3157`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `67` / `0.0523`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `417` / `0.3258`
- high_count / high_frac (`solve_rate > 0.75`): `796` / `0.6219`
- omitted_count / omitted_frac: `863` / `0.6742`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.7512 | 0.0086 | 0.4773 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
