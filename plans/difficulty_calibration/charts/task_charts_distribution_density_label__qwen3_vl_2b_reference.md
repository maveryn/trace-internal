# task_charts_distribution_density_label

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/charts/distribution/density_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5812`
- zero_solve_rate: `0.1625`
- perfect_solve_rate: `0.2742`
- mean_task_reward: `0.5812`
- mean_overall_reward: `0.6221`
- mean_format_reward: `0.9906`
- mean_prompt_length: `156.8719`
- mean_generated_tokens: `48.4959`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `384` / `0.3000`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `220` / `0.1719`
- high_count / high_frac (`solve_rate > 0.75`): `676` / `0.5281`
- omitted_count / omitted_frac: `1060` / `0.8281`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5812 | 0.1625 | 0.2742 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
