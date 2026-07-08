# TRACE RLVR Training Runbook

This is the operational runbook for the current split-v1 TRACE RLVR training
pass. It records the commands to run on a GPU host and the CPU-safe checks that
can be run anywhere.

Use this runbook with:

- strategy: `docs/RLVR_TRAINING_STRATEGY.md`
- task split: `docs/RLVR_TASK_SPLIT_PLAN.md`
- external benchmark subsets: `docs/workflows/EXTERNAL_BENCHMARK_EVAL.md`
- launcher reference: `rlvr/README.md`

Do not start training on a host without a CUDA GPU. Documentation edits, dry-run
config checks, dataset manifest checks, and benchmark subset preparation do not
need training hardware.

## Current Training Inputs

| item | value |
| --- | --- |
| base model | `Qwen/Qwen2.5-VL-3B-Instruct` |
| training split | `maveryn/trace@train` |
| validation split | `maveryn/trace@validation` |
| split id | `trace_rlvr_task_split_v1` |
| train rows | `230,400` (`900` tasks x `256` samples) |
| validation rows | `2,500` (`100` tasks x `25` samples) |
| default mode | answer-only |
| train batch | `256` prompts |
| rollouts | `8` per prompt |
| canonical first-stage cap | `200` steps before external benchmark comparison |
| full planned cap | `900` steps if the staged run is healthy |

The canonical launcher for this run is:

```bash
rlvr/examples/model_runs/run_trace_qwen25vl_3b_answer_split_v1.sh
```

It sets the intended split-v1 defaults: prompt length `2048`, training response
length `4096`, validation response length `2048`, exact JSON answer scoring,
batch `256`, rollouts `8`, and total steps `900` unless overridden.

## CPU-Safe Preflight

Run these before moving to a GPU host:

```bash
cd /home/jovyan/work/trace

git diff --check -- docs rlvr scripts tests trace configs prompts AGENTS.md README.md

PYTHONPATH=. python scripts/prepare_external_eval_subset_v1.py --dry-run
PYTHONPATH=. python scripts/upload_external_eval_subset_v1_to_hf.py --dry-run

TRACE_RLVR_DRY_RUN=1 \
TRAINER_EXPERIMENT_NAME=trace_qwen25vl3b_split_v1_answer_dryrun \
rlvr/examples/model_runs/run_trace_qwen25vl_3b_answer_split_v1.sh
```

The dry-run command only prints the resolved training command. It does not load
the model or start training.

## Base Validation Before RL

Run this on the GPU host to establish the pre-training TRACE validation score:

```bash
cd /home/jovyan/work/trace

WANDB_MODE=online \
TRAINER_EXPERIMENT_NAME=trace_qwen25vl3b_split_v1_answer_base_val \
rlvr/examples/model_runs/run_trace_qwen25vl_3b_answer_split_v1.sh \
  trainer.val_only=true \
  trainer.total_training_steps=1 \
  trainer.save_freq=-1
```

Track at minimum:

- answer reward
- format validity
- response length mean, p90, and p95
- truncation rate
- grouped domain/task metrics

Do not start the RL run if validation fails to load the dataset, cannot parse
TRACE reward payloads, or shows a severe format-validity regression from the
prompt-pilot baseline.

## Base External Benchmarks

Run fixed `external_eval_v1` subsets for the base model before training:

```bash
cd /home/jovyan/work/trace

PYTHONPATH=. python scripts/run_external_benchmark_generation_queue.py \
  --model Qwen/Qwen2.5-VL-3B-Instruct \
  --model-slug qwen25vl3b-base \
  --run-set full \
  --only chartqapro charxivreason mathvista mmmu_pro_vision countqa game_qa_lite blink screenspotpro \
  --subset-root benchmark/subsets/external_eval_v1 \
  --queue-name qwen25vl3b-base_external_eval_v1

PYTHONPATH=. python scripts/run_external_benchmark_score_queue.py \
  --model Qwen/Qwen2.5-VL-3B-Instruct \
  --model-slug qwen25vl3b-base \
  --run-set full \
  --only chartqapro charxivreason mathvista mmmu_pro_vision countqa game_qa_lite blink screenspotpro \
  --queue-name qwen25vl3b-base_external_eval_v1
```

This is a checkpoint-level comparison set, not an in-loop validation set.

## GPU Smoke Run

Before the staged run, run a tiny training smoke on the GPU host:

```bash
cd /home/jovyan/work/trace

WANDB_MODE=offline \
TOTAL_TRAINING_STEPS=2 \
TRAIN_BATCH_SIZE=8 \
ROLLOUT_N=2 \
SAVE_FREQ=1 \
TEST_FREQ=1 \
MAX_ACTOR_CKPT_TO_KEEP=2 \
MAX_CRITIC_CKPT_TO_KEEP=2 \
TRAINER_APPEND_TIMESTAMP=0 \
TRAINER_EXPERIMENT_NAME=trace_qwen25vl3b_split_v1_answer_smoke \
rlvr/examples/model_runs/run_trace_qwen25vl_3b_answer_split_v1.sh
```

The smoke passes only if a checkpoint writes under
`checkpoints/trace_rlvr/trace_qwen25vl3b_split_v1_answer_smoke/`, validation
runs, and reward/format metrics are logged.

## Stage 0-200 Training

The first real run should stop at step `200`, keep every checkpoint needed for
comparison, and validate every `50` steps:

```bash
cd /home/jovyan/work/trace

WANDB_MODE=online \
TOTAL_TRAINING_STEPS=200 \
SAVE_FREQ=50 \
TEST_FREQ=50 \
MAX_ACTOR_CKPT_TO_KEEP=6 \
MAX_CRITIC_CKPT_TO_KEEP=6 \
TRAINER_APPEND_TIMESTAMP=0 \
TRAINER_EXPERIMENT_NAME=trace_qwen25vl3b_split_v1_answer_stage0_200_seed42 \
rlvr/examples/model_runs/run_trace_qwen25vl_3b_answer_split_v1.sh
```

Hard-stop conditions:

- NaN or exploding loss/reward statistics
- checkpoints fail to save or reload
- validation cannot run
- JSON/format validity collapses
- truncation rate becomes high enough that responses are routinely cut off
- reward collapses near zero across most domains

Step `50` is a health check. Step `100` is an early sanity check. Step `200` is
the first external benchmark decision point.

## Merge A Checkpoint To HF Format

The external benchmark queue expects a Hugging Face model path. Merge an actor
checkpoint after the staged run:

```bash
cd /home/jovyan/work/trace/rlvr

python -m verl.model_merger merge \
  --backend fsdp \
  --local_dir ../checkpoints/trace_rlvr/trace_qwen25vl3b_split_v1_answer_stage0_200_seed42/global_step_200/actor \
  --target_dir ../checkpoints/trace_rlvr_merged_hf/trace_qwen25vl3b_split_v1_answer_step200 \
  --trust-remote-code
```

If uploading the merged checkpoint directly from the merger, add:

```bash
--hf_upload_path <org-or-user>/<repo-name> --private
```

## Step-200 External Benchmarks

Run the same fixed external subset against the merged checkpoint:

```bash
cd /home/jovyan/work/trace

PYTHONPATH=. python scripts/run_external_benchmark_generation_queue.py \
  --model checkpoints/trace_rlvr_merged_hf/trace_qwen25vl3b_split_v1_answer_step200 \
  --model-slug trace-qwen25vl3b-step200 \
  --run-set full \
  --only chartqapro charxivreason mathvista mmmu_pro_vision countqa game_qa_lite blink screenspotpro \
  --subset-root benchmark/subsets/external_eval_v1 \
  --queue-name trace-qwen25vl3b-step200_external_eval_v1

PYTHONPATH=. python scripts/run_external_benchmark_score_queue.py \
  --model checkpoints/trace_rlvr_merged_hf/trace_qwen25vl3b_split_v1_answer_step200 \
  --model-slug trace-qwen25vl3b-step200 \
  --run-set full \
  --only chartqapro charxivreason mathvista mmmu_pro_vision countqa game_qa_lite blink screenspotpro \
  --queue-name trace-qwen25vl3b-step200_external_eval_v1
```

Continue only if TRACE validation improved or remained healthy and external
benchmarks do not show unacceptable broad regressions.

## Continue From Step 200

Resume from the global checkpoint folder, not the `actor/` subfolder:

```bash
cd /home/jovyan/work/trace

WANDB_MODE=online \
RESUME_FROM_PATH=/home/jovyan/work/trace/checkpoints/trace_rlvr/trace_qwen25vl3b_split_v1_answer_stage0_200_seed42/global_step_200 \
TOTAL_TRAINING_STEPS=900 \
SAVE_FREQ=100 \
TEST_FREQ=100 \
MAX_ACTOR_CKPT_TO_KEEP=8 \
MAX_CRITIC_CKPT_TO_KEEP=8 \
TRAINER_APPEND_TIMESTAMP=0 \
TRAINER_EXPERIMENT_NAME=trace_qwen25vl3b_split_v1_answer_stage0_200_seed42 \
rlvr/examples/model_runs/run_trace_qwen25vl_3b_answer_split_v1.sh
```

Keep the same experiment name when resuming a staged run so the checkpoint tree
remains contiguous.

## Optional Reward Ablation

Answer-only is the first operational run. If it is stable, run
answer-and-annotation ablations separately:

```bash
TRACE_OUTPUT_MODE=answer_and_annotation \
TRACE_ANSWER_WEIGHT=0.8 \
TRACE_ANNOTATION_WEIGHT=0.2 \
TRAINER_EXPERIMENT_NAME=trace_qwen25vl3b_split_v1_answer_annotation_08_02_stage0_200_seed42 \
TOTAL_TRAINING_STEPS=200 \
SAVE_FREQ=50 \
TEST_FREQ=50 \
MAX_ACTOR_CKPT_TO_KEEP=6 \
MAX_CRITIC_CKPT_TO_KEEP=6 \
rlvr/examples/model_runs/run_trace_qwen25vl_3b_answer_split_v1.sh
```

Do not compare answer-only and answer-and-annotation runs unless they use the
same model, data split, batch size, rollout count, response cap, and checkpoint
cadence.

## What To Record

For each run, record:

- launcher command and environment overrides
- git commit and dirty-worktree status
- dataset repo/revision or local parquet manifest
- checkpoint paths retained
- TRACE validation summary for every checkpoint
- external benchmark queue names and score summaries
- known failures or manually excluded comparisons

If a run was started from a dirty worktree, record the relevant diff or commit
the exact launcher/config/doc changes before treating the result as canonical.
