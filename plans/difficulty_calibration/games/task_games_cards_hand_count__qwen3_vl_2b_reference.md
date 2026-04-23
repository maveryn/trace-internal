# task_games_cards_hand_count

## Metadata

- domain: `games`
- status: `not_started`
- calibration_direction: `make_easier`
- task_module: `trace/tasks/games/cards/hand_count.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.2929`
- zero_solve_rate: `0.0852`
- perfect_solve_rate: `0.0000`
- mean_task_reward: `0.2929`
- mean_overall_reward: `0.3437`
- mean_format_reward: `0.8012`
- mean_prompt_length: `179.2422`
- mean_generated_tokens: `305.3373`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `378` / `0.2953`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `854` / `0.6672`
- high_count / high_frac (`solve_rate > 0.75`): `48` / `0.0375`
- omitted_count / omitted_frac: `426` / `0.3328`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.2929 | 0.0852 | 0.0000 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
