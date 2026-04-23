# task_games_reversi_move_count

## Metadata

- domain: `games`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/games/reversi/move_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1505`
- zero_solve_rate: `0.1781`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1505`
- mean_overall_reward: `0.2050`
- mean_format_reward: `0.6959`
- mean_prompt_length: `203.6789`
- mean_generated_tokens: `379.0160`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `806` / `0.6297`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `431` / `0.3367`
- high_count / high_frac (`solve_rate > 0.75`): `43` / `0.0336`
- omitted_count / omitted_frac: `849` / `0.6633`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1505 | 0.1781 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
