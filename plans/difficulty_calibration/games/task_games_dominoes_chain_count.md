# task_games_dominoes_chain_count

## Metadata

- domain: `games`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/games/dominoes/chain_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1410`
- zero_solve_rate: `0.1141`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.1410`
- mean_overall_reward: `0.2081`
- mean_format_reward: `0.8120`
- mean_prompt_length: `195.8812`
- mean_generated_tokens: `330.3454`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `634` / `0.4953`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `645` / `0.5039`
- high_count / high_frac (`solve_rate > 0.75`): `1` / `0.0008`
- omitted_count / omitted_frac: `635` / `0.4961`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1410 | 0.1141 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
