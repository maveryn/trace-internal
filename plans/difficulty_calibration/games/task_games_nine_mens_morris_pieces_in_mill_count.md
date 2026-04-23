# task_games_nine_mens_morris_pieces_in_mill_count

## Metadata

- domain: `games`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/games/nine_mens_morris/pieces_in_mill_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.0680`
- zero_solve_rate: `0.5234`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.0680`
- mean_overall_reward: `0.1051`
- mean_format_reward: `0.4394`
- mean_prompt_length: `175.9383`
- mean_generated_tokens: `590.3199`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `1029` / `0.8039`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `248` / `0.1938`
- high_count / high_frac (`solve_rate > 0.75`): `3` / `0.0023`
- omitted_count / omitted_frac: `1032` / `0.8063`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.0680 | 0.5234 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
