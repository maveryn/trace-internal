# task_physics_optics_ray_trace

## Metadata

- domain: `physics`
- status: `not_started`
- owner: ``
- active_calibration_model: `Qwen/Qwen3-VL-8B-Instruct`
- probe_size: `200`
- rollouts_per_prompt: `32`
- task_module: `trace/tasks/physics/optics/ray_trace.py`
- 2b_reference_file: [task_physics_optics_ray_trace__qwen3_vl_2b_reference.md](task_physics_optics_ray_trace__qwen3_vl_2b_reference.md)

## Reference Context

- the linked 2B reference file records the historical `Qwen/Qwen3-VL-2B-Instruct` probe numbers
- use it only as context for task behavior and tail shape
- the active baseline for calibration must come from a fresh `Qwen/Qwen3-VL-8B-Instruct` probe on newly generated `200` samples

## Recorded Baseline Task Parameters

- pending baseline support extraction


## Working Baseline

- status: `pending`
- baseline_replacement_needed: `pending`
- rationale: ``
- params_override: ``

## Distribution Validation

- status: `pending`
- requirement: generated calibration samples must satisfy TRACE task-distribution and answer-support checks before model evaluation
- workflow reference: `docs/workflows/BUILD_VALIDATION.md`
- suggested command: `PYTHONPATH=. python scripts/run_task_review.py --tasks task_physics_optics_ray_trace --mode distribution`
- notes: ``

## Floor Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded or working baseline | pending |
| `1` | raise minimum difficulty | pending |
| `2` | aggressively raise minimum difficulty | pending |

## Ceiling Ladder

| Level | Intent | Params |
|---|---|---|
| `0` | recorded or working baseline | pending |
| `1` | lower maximum difficulty | pending |
| `2` | aggressively lower maximum difficulty | pending |

## 8B Baseline Probe

- status: `pending`
- prompt_count: `pending`
- rollout_count: `pending`
- hard_frac (`solve_rate == 0`): `pending`
- easy_frac (`solve_rate >= 0.8`): `pending`
- band_frac (`0 < solve_rate < 0.8`): `pending`
- mean_solve_rate: `pending`

## Working Notes

- start from a fresh `200 x 32` `Qwen/Qwen3-VL-8B-Instruct` probe
- update this file after every iteration; keep the 2B reference file unchanged

## Probe Log

| Date | Model | Samples | Rollouts | Hard frac | Easy frac | Band frac | Mean solve rate | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|

## Next Action

- extract or define the working baseline and task-specific floor/ceiling ladders, then run the first `200 x 32` 8B probe
