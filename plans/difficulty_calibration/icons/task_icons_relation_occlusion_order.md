# task_icons_relation_occlusion_order

## Metadata

- domain: `icons`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/icons/relation/occlusion_order.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1547`
- zero_solve_rate: `0.3047`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1547`
- mean_overall_reward: `0.2193`
- mean_format_reward: `0.8004`
- mean_prompt_length: `153.2859`
- mean_generated_tokens: `276.2643`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `783` / `0.6117`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `462` / `0.3609`
- high_count / high_frac (`solve_rate > 0.75`): `35` / `0.0273`
- omitted_count / omitted_frac: `818` / `0.6391`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1547 | 0.3047 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
