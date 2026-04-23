# task_charts_multiseries_pairwise_comparison_count

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `review`
- task_module: `trace/tasks/charts/multiseries/pairwise_comparison_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2890`
- zero_solve_rate: `0.0250`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.2890`
- mean_overall_reward: `0.3428`
- mean_format_reward: `0.8266`
- mean_prompt_length: `169.9727`
- mean_generated_tokens: `118.3455`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `223` / `0.1742`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `1043` / `0.8148`
- high_count / high_frac (`solve_rate > 0.75`): `14` / `0.0109`
- omitted_count / omitted_frac: `237` / `0.1852`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2890 | 0.0250 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
