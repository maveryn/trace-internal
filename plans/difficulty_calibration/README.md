# Task Difficulty Calibration

This workspace tracks the manual TRACE RLVR difficulty calibration pass.

## Goal

- measure every task with the current code/config
- keep tasks away from fully solved and fully unsolved regimes
- tune task configs manually after reviewing probe results
- keep one current-best summary per task in [plans/PROGRESS_SUMMARY.md](../PROGRESS_SUMMARY.md)

Historical `Qwen/Qwen3-VL-2B-Instruct` files and older `200 x 32` probes are reference only. Do not copy those numbers into the current-best summary.

## Standard Probe

- model: `Qwen/Qwen3-VL-8B-Instruct`
- backend: `vLLM`
- prompts per task: `100`
- rollouts per prompt: `64`
- batch size: `6400`
- prompt mode: `answer`
- GPU policy: run one task probe on one GPU
- scoring: TRACE reward with current lenient-answer normalization

Sample categories:

- hard: `solved_rollouts == 0`
- easy: `solved_rollouts >= 58`
- mixed: everything else

Target:

- `hard_frac <= 0.15`
- `easy_frac <= 0.15`

## Workflow

1. Pick one task and inspect its task record, generator, and config.
2. Generate exactly `100` fresh samples for that task.
3. Run TRACE distribution validation on that exact sample set.
4. If distribution validation fails, fix the task config or generator support before model evaluation.
5. If distribution validation passes, run the `100 x 64` vLLM probe on one GPU.
6. Review hard/easy/mixed counts overall and by `task_variant` / `scene_variant` when present.
7. Manually decide the next config change:
   - too many easy samples: make the easiest support harder
   - too many hard samples: make the hardest support easier
   - one variant dominates a tail: tune that variant specifically
   - local config changes do not help: consider semantic redesign, blocking, or dropping the task
8. Repeat as needed and keep the best current-code/current-config result.
9. Update the task record and [plans/PROGRESS_SUMMARY.md](../PROGRESS_SUMMARY.md) after every retained best result.

This is not automated. The config change is chosen manually after reading the probe results.

## Commands

Build and export a 100-sample task probe:

```bash
cd /home/jovyan/work/trace

python scripts/prepare_trace_rlvr_task_probe.py \
  --task-id <task_id> \
  --num-instances 100 \
  --output-root out/calibration \
  --prompt-variant answer \
  --reset
```

Validate the exact exported sample set:

```bash
cd /home/jovyan/work/trace

DATASET_ROOT=$(python - <<'PY'
import json
from pathlib import Path
manifest = Path("out/calibration/<task_id>_probe_100.parquet.manifest.json")
print(json.loads(manifest.read_text(encoding="utf-8"))["trace_dataset_root"])
PY
)

PYTHONPATH=. python scripts/check_rlvr_probe_distribution.py \
  --parquet out/calibration/<task_id>_probe_100.parquet \
  --dataset-root "$DATASET_ROOT"
```

Run the 64-rollout probe:

```bash
cd /home/jovyan/work/trace

CUDA_VISIBLE_DEVICES=<gpu_id> \
python rlvr/scripts/trace_curriculum_probe.py \
  --parquet out/calibration/<task_id>_probe_100.parquet \
  --output-dir rlvr/outputs/curriculum_probe/<task_id>_probe_100_qwen3vl8b \
  --model Qwen/Qwen3-VL-8B-Instruct \
  --tensor-parallel-size 1 \
  --batch-size 6400 \
  --max-num-seqs 128 \
  --gpu-memory-utilization 0.9 \
  --count 100 \
  --rollouts-per-prompt 64
```

Run broader distribution review after changing task logic or support:

```bash
cd /home/jovyan/work/trace

PYTHONPATH=. python scripts/run_task_review.py \
  --tasks <task_id> \
  --mode distribution
```

## Records

For each retained result, record:

- task id
- config label or explicit override
- parquet path
- TRACE dataset root
- model output directory
- hard/easy/band fractions
- per-variant notes when useful
- manual decision for the next step

`plans/PROGRESS_SUMMARY.md` must contain one row per task grouped by domain. Rows without a valid current-code/current-config probe should stay `pending_current_probe`.

## Working Rules

- Keep probe artifacts out of git unless promoted into a maintained summary.
- Before editing a task, set its task record status to `in_progress`.
- If a task needs shared infrastructure or a semantic redesign, mark it `blocked` and explain why.
- When a task meets the target or is close enough to keep, mark it `done` or record the retained best result.
