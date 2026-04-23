# task_charts_statistics_summary_value

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/charts/statistics/summary_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.6520`
- zero_solve_rate: `0.0195`
- perfect_solve_rate: `0.2586`
- mean_task_reward: `0.6520`
- mean_overall_reward: `0.6593`
- mean_format_reward: `0.7259`
- mean_prompt_length: `144.6297`
- mean_generated_tokens: `85.9019`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `114` / `0.0891`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `538` / `0.4203`
- high_count / high_frac (`solve_rate > 0.75`): `628` / `0.4906`
- omitted_count / omitted_frac: `742` / `0.5797`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.6520 | 0.0195 | 0.2586 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
