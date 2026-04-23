# task_charts_counting_value_count

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/charts/counting/value_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2843`
- zero_solve_rate: `0.0648`
- perfect_solve_rate: `0.0102`
- mean_task_reward: `0.2843`
- mean_overall_reward: `0.3214`
- mean_format_reward: `0.6548`
- mean_prompt_length: `154.6094`
- mean_generated_tokens: `85.0658`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `370` / `0.2891`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `840` / `0.6562`
- high_count / high_frac (`solve_rate > 0.75`): `70` / `0.0547`
- omitted_count / omitted_frac: `440` / `0.3438`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2843 | 0.0648 | 0.0102 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
