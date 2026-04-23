# Task Difficulty Calibration

This workspace tracks the domain-by-domain task difficulty calibration pass for TRACE RLVR.

## Goal

- bring task difficulty into a non-saturated RLVR regime across tasks
- reduce tasks with very high solve-rate tails by increasing complexity where appropriate
- reduce tasks with very low solve-rate tails by simplifying size/count knobs where appropriate
- keep progress and decisions in one place so task work can be parallelized safely

## Historical Reference Stats

- the existing per-task and per-domain numeric summaries were produced with `Qwen/Qwen3-VL-2B-Instruct`
- those files are retained as reference only and have been renamed with the model in the filename
- active calibration baselines must now come from fresh `Qwen/Qwen3-VL-8B-Instruct` probes on newly generated `200`-sample task datasets

## Standard Calibration Settings

- calibration model: `Qwen/Qwen3-VL-8B-Instruct`
- samples per task probe: `200`
- rollouts per prompt: `32`
- prompt mode: `answer`
- response scoring: TRACE reward with the current probe lenient-answer normalization
- distribution gate: every freshly generated `200`-sample task set must first pass TRACE task-distribution, answer-diversity, and answer-support checks before model evaluation

Note:
- the text-only model `Qwen/Qwen3-8B` cannot consume TRACE image tasks, so calibration should use the visual model `Qwen/Qwen3-VL-8B-Instruct`

## Shared Calibration Algorithm

Use one shared two-sided controller for every task.

### Objective

For a calibrated task, most prompts should land in the mixed-signal regime:

- `0 < solve_rate < 0.8`

Track the two tails separately:

- `hard_frac = frac(solve_rate == 0)`
- `easy_frac = frac(solve_rate >= 0.8)`
- `band_frac = 1 - hard_frac - easy_frac`

Recommended target:

- `band_frac >= 0.95`
- `hard_frac <= 0.025`
- `easy_frac <= 0.025`

Use fraction thresholds as the primary controller:

- ideal target:
  - `hard_frac <= 0.025`
  - `easy_frac <= 0.025`
- acceptable pass:
  - `hard_frac <= 0.10`
  - `easy_frac <= 0.10`
- moderate tail overflow:
  - `0.05 < hard_frac <= 0.15`
  - `0.05 < easy_frac <= 0.15`
- severe tail overflow:
  - `hard_frac > 0.15`
  - `easy_frac > 0.15`

For the standard `200`-prompt probe, the equivalent counts are:

- `0.025` -> `5 / 200`
- `0.05` -> `10 / 200`
- `0.10` -> `20 / 200`
- `0.15` -> `30 / 200`

### Why Not One Scalar Difficulty Level

One scalar is too coarse for TRACE tasks.

- Some tasks are simultaneously too easy at the low end and too hard at the high end.
- A single difficulty shift moves the whole task distribution, but what we usually want is:
  - make the easiest instances harder
  - make the hardest instances easier

So use two task-specific control ladders instead:

- `floor_level`
  Raises the minimum complexity and reduces the easy tail.
- `ceiling_level`
  Lowers the maximum complexity and reduces the hard tail.

Both should be stored as small integer ladder indices in task docs.

### Why Integer Ladders Instead of Real-Valued Controls

Use integer levels for the controller and documentation.

- TRACE task knobs are mostly discrete already:
  - counts
  - ranges
  - categorical scene/task variants
  - variant weights
- Integer levels are easier to review, reproduce, and parallelize.
- Real-valued controls would still need task-specific rounding logic, so they do not actually simplify the task side.

The important part is that each level maps to a full task-specific parameter bundle, not to one universal numeric rule.

### Task-Specific Ladder Design

Each task should define:

- a `floor ladder`
  Controls the easiest generated prompts.
  Typical changes:
  - increase minimum size/count
  - remove easiest scene variants
  - increase minimum distractor count
- a `ceiling ladder`
  Controls the hardest generated prompts.
  Typical changes:
  - decrease maximum size/count
  - remove hardest scene variants
  - reduce maximum distractor count

This keeps the shared algorithm fixed while letting each task choose the right knobs.

### Baseline Replacement Rule

Do not assume the current production support is always the right `level 0` baseline.

If the recorded baseline is far outside the target band, first define a better working baseline for the task.

Typical cases:

- overwhelmingly easy task:
  - replace the baseline with a harder support before starting the normal iteration loop
- overwhelmingly hard task:
  - replace the baseline with an easier support before starting the normal iteration loop

Document this explicitly in the task record:

- `recorded baseline`
  The support that produced the original measured stats.
- `working baseline`
  The support that the calibration loop will actually start from.

This avoids wasting iterations when the original support is obviously unusable.

### Variant-Aware Rule

Before changing knobs, inspect solve-rate stats at least by:

- `task_variant`
- `scene_variant` when applicable

If one variant is much easier or much harder than the others, fix the variant imbalance first:

- adjust variant weights, or
- give that variant its own tighter support

Do not try to solve strong variant imbalance only with global min/max changes.

### Update Rule Per Iteration

At iteration `t`, update with these exact bounded steps:

- floor-side update from `easy_frac`:
  - if `easy_frac <= 0.05`, increase `floor_level` by `0`
  - if `0.05 < easy_frac <= 0.15`, increase `floor_level` by `1`
  - if `easy_frac > 0.15`, increase `floor_level` by `2`

- ceiling-side update from `hard_frac`:
  - if `hard_frac <= 0.05`, increase `ceiling_level` by `0`
  - if `0.05 < hard_frac <= 0.15`, increase `ceiling_level` by `1`
  - if `hard_frac > 0.15`, increase `ceiling_level` by `2`

Interpretation:

- increasing `floor_level` makes the easiest instances harder
- increasing `ceiling_level` makes the hardest instances easier

If both tails overflow, update both sides in the same iteration using the same rules above.

### Stop Rule

Stop when any of these holds:

1. pass condition:
   - `hard_frac <= 0.10`
   - `easy_frac <= 0.10`
   - `band_frac >= 0.80`
2. max iterations reached:
   - `5`
3. no meaningful improvement:
   - best `band_frac` has not improved by at least `0.02` in two consecutive iterations

### Best-Run Selection

If a task does not satisfy the stop rule within `5` iterations, keep the best run by:

1. highest `band_frac`
2. then smallest `abs(easy_frac - hard_frac)`
3. then mean solve rate closest to `0.4`

### Practical Guidance On Knobs

Prefer structural difficulty knobs first:

- counts
- sizes
- branching
- path length
- number of compared items
- number of distractors

Avoid relying on readability degradation unless necessary:

- smaller fonts
- tighter spacing
- clutter through rendering artifacts

Those often create OCR failure instead of clean reasoning difficulty.

## Calibration Loop

1. Inspect the task file and current baseline stats in the task record.
2. Fill in the task-specific baseline parameters, floor ladder, and ceiling ladder.
3. Inspect solve-rate stats by task, and by variant when applicable.
4. Make one bounded two-sided update to the task support.
5. Generate 200 questions for that task.
6. Run TRACE distribution validation on that exact 200-sample set:
   - answer-diversity / unique-answer support
   - answer-support / structural support checks
   - variant-level answer-distribution checks when `task_variant` exists in the trace
7. Only if distribution validation passes, run 32 rollouts with the base Qwen3-VL-8B model.
8. Record updated solve-rate stats and the next decision in the task record.
9. Repeat until the task is in a stable mixed-signal regime or `5` iterations are exhausted.

## Standard Commands

Build a 200-sample task-only TRACE dataset and export it to parquet:

```bash
cd /home/jovyan/work/trace

python scripts/prepare_trace_rlvr_task_probe.py \
  --task-id <task_id> \
  --num-instances 200 \
  --output-root out/calibration \
  --prompt-variant answer \
  --reset
```

This writes:

- parquet: `out/calibration/<task_id>_probe_200.parquet`
- manifest: `out/calibration/<task_id>_probe_200.parquet.manifest.json`

The manifest records the hashed TRACE dataset root under `trace_dataset_root`.

Validate that the exact generated 200-sample set still satisfies TRACE distribution checks before model evaluation:

```bash
cd /home/jovyan/work/trace

DATASET_ROOT=$(python - <<'PY'
import json
from pathlib import Path
manifest = Path("out/calibration/<task_id>_probe_200.parquet.manifest.json")
print(json.loads(manifest.read_text(encoding="utf-8"))["trace_dataset_root"])
PY
)

PYTHONPATH=. python scripts/check_rlvr_probe_distribution.py \
  --parquet out/calibration/<task_id>_probe_200.parquet \
  --dataset-root "$DATASET_ROOT"
```

When task logic or task-family support changes, also run the broader generator-level review workflow:

```bash
cd /home/jovyan/work/trace

PYTHONPATH=. python scripts/run_task_review.py \
  --tasks <task_id> \
  --mode distribution
```

Run the 32-rollout calibration probe:

```bash
cd /home/jovyan/work/trace

python rlvr/scripts/trace_curriculum_probe.py \
  --parquet out/calibration/<task_id>_probe_200.parquet \
  --output-dir rlvr/outputs/curriculum_probe/<task_id>_probe_200_qwen3vl8b \
  --model Qwen/Qwen3-VL-8B-Instruct \
  --tensor-parallel-size 1 \
  --batch-size 6400 \
  --max-num-seqs 128 \
  --gpu-memory-utilization 0.9 \
  --count 200 \
  --rollouts-per-prompt 32
```

Note:

- calibration probes currently use `200` prompts per task, so an explicit `--batch-size 6400` means “do not split into multiple prompt waves unless another scheduler limit forces it”
- the effective prompt batch on a `200`-sample task probe is therefore still at most `200`

## Parallel Working Rules

- Assign one agent per domain whenever possible.
- Before touching a task, fill in the `owner` field in that task record and set `status: in_progress`.
- The default write scope for a domain worker is:
  - `plans/difficulty_calibration/<domain>/`
  - `trace/tasks/<domain>/`
  - `configs/domains/<domain>/`
  - prompt assets directly tied to that domain
- If a task seems to require a shared utility or cross-domain helper change, do not make that change silently.
  Mark the task `blocked` and note the required shared change in the task record first.
- After every probe iteration, update the task record immediately:
  - what changed
  - sample count
  - rollout count
  - new solve-rate stats
  - next decision
- Before the first adjustment on a task, fill in the `Current Baseline Task Parameters` section with the effective knobs that produced the current baseline.
- When a task is acceptable for the current pass, set `status: done` and leave a short final note in `Working Notes`.
- Keep benchmark and probe result files out of git unless they are promoted into a maintained summary document.

## Status Fields

- `not_started`: no task-specific calibration work yet
- `in_progress`: task is currently being tuned
- `blocked`: task needs a design decision or shared infra change
- `done`: current calibration pass is acceptable

## Suggested Initial Order

1. `diagrams`, `documents`, `charts`
   These domains currently have the strongest high-solve saturation and are the clearest “make harder” passes.
2. `icons`, `tile`, `graph`, `games`, `puzzles`
   These domains are mostly under-solved and will likely need simpler size/count settings first.
3. `physics`, `geometry`, `temporal`
   These are also low-solve overall, but closer to a mixed regime than the hardest domains above.
4. `tables`
   This domain is the closest to mixed already and is best used as a later cleanup pass.

## Domain Summary

| Domain | Tasks | Mean positive rollout rate | Mean low omission frac | Mean high omission frac | Folder |
|---|---:|---:|---:|---:|---|
| charts | 10 | 0.5119 | 0.2070 | 0.3520 | [charts](charts/README.md) |
| diagrams | 5 | 0.6149 | 0.2811 | 0.5602 | [diagrams](diagrams/README.md) |
| documents | 5 | 0.6592 | 0.2781 | 0.6205 | [documents](documents/README.md) |
| games | 10 | 0.1523 | 0.5761 | 0.0153 | [games](games/README.md) |
| geometry | 10 | 0.2432 | 0.4282 | 0.0729 | [geometry](geometry/README.md) |
| graph | 10 | 0.1687 | 0.5579 | 0.0216 | [graph](graph/README.md) |
| icons | 10 | 0.1470 | 0.6430 | 0.0234 | [icons](icons/README.md) |
| physics | 5 | 0.2190 | 0.4391 | 0.0306 | [physics](physics/README.md) |
| puzzles | 10 | 0.1674 | 0.5452 | 0.0394 | [puzzles](puzzles/README.md) |
| tables | 10 | 0.4331 | 0.2536 | 0.2486 | [tables](tables/README.md) |
| temporal | 5 | 0.2196 | 0.5114 | 0.0855 | [temporal](temporal/README.md) |
| tile | 10 | 0.1328 | 0.5675 | 0.0098 | [tile](tile/README.md) |

Each domain folder contains one markdown record per task.
