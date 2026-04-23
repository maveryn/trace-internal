# Task Difficulty Calibration

This workspace tracks the domain-by-domain task difficulty calibration pass for TRACE RLVR.

## Goal

- bring task difficulty into a non-saturated RLVR regime across tasks
- reduce tasks with very high solve-rate tails by increasing complexity where appropriate
- reduce tasks with very low solve-rate tails by simplifying size/count knobs where appropriate
- keep progress and decisions in one place so task work can be parallelized safely

## Calibration Loop

1. Inspect the task file and current baseline stats in the task record.
2. Identify the control knobs that can change difficulty without changing task semantics.
3. Make one focused difficulty adjustment.
4. Generate 200 questions for that task.
5. Run 32 rollouts with the base Qwen3-VL-2B model.
6. Record updated solve-rate stats and the next decision in the task record.
7. Repeat until the task is in a stable mixed-signal regime.

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
