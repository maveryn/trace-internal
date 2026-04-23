# task_charts_trend_structure_value

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/charts/trend/structure_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1760`
- zero_solve_rate: `0.1891`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1760`
- mean_overall_reward: `0.2259`
- mean_format_reward: `0.6755`
- mean_prompt_length: `170.9094`
- mean_generated_tokens: `329.3520`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `666` / `0.5203`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `594` / `0.4641`
- high_count / high_frac (`solve_rate > 0.75`): `20` / `0.0156`
- omitted_count / omitted_frac: `686` / `0.5359`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1760 | 0.1891 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
