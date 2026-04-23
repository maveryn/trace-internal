# task_games_go_group_liberty_count

## Metadata

- domain: `games`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/games/go/group_liberty_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.1243`
- zero_solve_rate: `0.3500`
- perfect_solve_rate: `0.0008`
- mean_task_reward: `0.1243`
- mean_overall_reward: `0.1825`
- mean_format_reward: `0.7060`
- mean_prompt_length: `199.3430`
- mean_generated_tokens: `333.6985`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `946` / `0.7391`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `289` / `0.2258`
- high_count / high_frac (`solve_rate > 0.75`): `45` / `0.0352`
- omitted_count / omitted_frac: `991` / `0.7742`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.1243 | 0.3500 | 0.0008 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
