# task_tables_readout_subset_value

## Metadata

- domain: `tables`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/tables/readout/subset_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5020`
- zero_solve_rate: `0.0586`
- perfect_solve_rate: `0.3477`
- mean_task_reward: `0.5020`
- mean_overall_reward: `0.5196`
- mean_format_reward: `0.6781`
- mean_prompt_length: `152.0578`
- mean_generated_tokens: `26.0584`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `344` / `0.2687`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `433` / `0.3383`
- high_count / high_frac (`solve_rate > 0.75`): `503` / `0.3930`
- omitted_count / omitted_frac: `847` / `0.6617`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5020 | 0.0586 | 0.3477 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
