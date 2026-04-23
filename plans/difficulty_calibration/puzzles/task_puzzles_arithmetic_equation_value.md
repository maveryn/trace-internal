# task_puzzles_arithmetic_equation_value

## Metadata

- domain: `puzzles`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/puzzles/arithmetic/equation_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5690`
- zero_solve_rate: `0.0078`
- perfect_solve_rate: `0.2703`
- mean_task_reward: `0.5690`
- mean_overall_reward: `0.5993`
- mean_format_reward: `0.8720`
- mean_prompt_length: `164.5000`
- mean_generated_tokens: `50.1227`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `121` / `0.0945`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `689` / `0.5383`
- high_count / high_frac (`solve_rate > 0.75`): `470` / `0.3672`
- omitted_count / omitted_frac: `591` / `0.4617`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5690 | 0.0078 | 0.2703 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
