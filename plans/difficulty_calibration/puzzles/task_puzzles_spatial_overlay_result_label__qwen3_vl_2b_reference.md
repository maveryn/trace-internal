# task_puzzles_spatial_overlay_result_label

## Metadata

- domain: `puzzles`
- status: `not_started`
- calibration_direction: `review`
- task_module: `trace/tasks/puzzles/spatial/overlay_result_label.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2768`
- zero_solve_rate: `0.0141`
- perfect_solve_rate: `0.0008`
- mean_task_reward: `0.2768`
- mean_overall_reward: `0.3383`
- mean_format_reward: `0.8914`
- mean_prompt_length: `158.4945`
- mean_generated_tokens: `169.6141`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `213` / `0.1664`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `1047` / `0.8180`
- high_count / high_frac (`solve_rate > 0.75`): `20` / `0.0156`
- omitted_count / omitted_frac: `233` / `0.1820`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2768 | 0.0141 | 0.0008 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
