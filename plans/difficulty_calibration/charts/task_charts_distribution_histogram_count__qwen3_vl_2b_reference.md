# task_charts_distribution_histogram_count

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/charts/distribution/histogram_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.6257`
- zero_solve_rate: `0.0148`
- perfect_solve_rate: `0.3102`
- mean_task_reward: `0.6257`
- mean_overall_reward: `0.6494`
- mean_format_reward: `0.8625`
- mean_prompt_length: `145.7937`
- mean_generated_tokens: `122.7215`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `96` / `0.0750`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `664` / `0.5188`
- high_count / high_frac (`solve_rate > 0.75`): `520` / `0.4062`
- omitted_count / omitted_frac: `616` / `0.4813`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.6257 | 0.0148 | 0.3102 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
