# task_games_mancala_move_count

## Metadata

- domain: `games`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/games/mancala/move_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1491`
- zero_solve_rate: `0.2633`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1491`
- mean_overall_reward: `0.1921`
- mean_format_reward: `0.5784`
- mean_prompt_length: `235.7094`
- mean_generated_tokens: `457.2542`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `829` / `0.6477`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `431` / `0.3367`
- high_count / high_frac (`solve_rate > 0.75`): `20` / `0.0156`
- omitted_count / omitted_frac: `849` / `0.6633`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1491 | 0.2633 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
