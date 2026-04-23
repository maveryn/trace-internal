# task_charts_distribution_boxplot_label

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/charts/distribution/boxplot_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5306`
- zero_solve_rate: `0.1242`
- perfect_solve_rate: `0.1922`
- mean_task_reward: `0.5306`
- mean_overall_reward: `0.5753`
- mean_format_reward: `0.9782`
- mean_prompt_length: `164.4398`
- mean_generated_tokens: `117.2452`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `370` / `0.2891`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `335` / `0.2617`
- high_count / high_frac (`solve_rate > 0.75`): `575` / `0.4492`
- omitted_count / omitted_frac: `945` / `0.7383`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5306 | 0.1242 | 0.1922 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
