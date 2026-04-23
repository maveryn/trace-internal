# task_games_checkers_move_count

## Metadata

- domain: `games`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/games/checkers/move_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1504`
- zero_solve_rate: `0.1961`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1504`
- mean_overall_reward: `0.2015`
- mean_format_reward: `0.6609`
- mean_prompt_length: `234.0813`
- mean_generated_tokens: `375.5134`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `668` / `0.5219`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `611` / `0.4773`
- high_count / high_frac (`solve_rate > 0.75`): `1` / `0.0008`
- omitted_count / omitted_frac: `669` / `0.5227`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1504 | 0.1961 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
