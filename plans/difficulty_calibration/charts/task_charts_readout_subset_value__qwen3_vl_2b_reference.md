# task_charts_readout_subset_value

## Metadata

- domain: `charts`
- status: `not_started`
- calibration_direction: `make_harder`
- task_module: `trace/tasks/charts/readout/subset_value.py`
- owner: ``

## Current Baseline (128k / 32-rollout base-model probe)

- prompt_count: `1280`
- rollout_count: `40960`
- positive_rollout_rate: `0.5255`
- zero_solve_rate: `0.0477`
- perfect_solve_rate: `0.0938`
- mean_task_reward: `0.5255`
- mean_overall_reward: `0.5508`
- mean_format_reward: `0.7780`
- mean_prompt_length: `135.4227`
- mean_generated_tokens: `68.9706`
- max_generated_tokens: `1024`

## Current Omission Breakdown (128k solve-band cut)

- total: `1280`
- low_count / low_frac (`solve_rate < 0.125`): `193` / `0.1508`
- retained_count / retained_frac (`0.125 <= solve_rate <= 0.75`): `668` / `0.5219`
- high_count / high_frac (`solve_rate > 0.75`): `419` / `0.3273`
- omitted_count / omitted_frac: `612` / `0.4781`

## Working Notes

- initial hypothesis: 
- control knobs to inspect: 
- first change candidate: 

## Probe Log

| Date | Change | Samples | Rollouts | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-04-23 | workspace initialized from current probe | 1280 | 32 | 0.5255 | 0.0477 | 0.0938 | baseline only |

## Next Action

- inspect generator/config knobs and propose the first focused complexity change
