# TRACE Annotation Ablation Runbook

This is the handoff runbook for agents running TRACE answer-and-annotation
ablations on separate GPU hosts. It uses the active EasyR1 backend, the all-1000
TRACE RLVR dataset on Hugging Face, and tmpfs-backed cache/checkpoint paths.

Use this for new paper runs. Do not use the legacy `rlvr/verl/` launchers unless
explicitly requested.

## Source Of Truth

| item | value |
| --- | --- |
| branch | `rlvr` |
| active backend | `rlvr/easyr1_backend/` |
| generic launcher | `scripts/run_trace_qwen25vl3b_easyr1_nokl_tmpfs.sh` |
| answer wrapper | `scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh` |
| gated annotation wrapper | `scripts/run_trace_qwen25vl3b_easyr1_annotation_gated_nokl_tmpfs.sh` |
| additive annotation wrapper | `scripts/run_trace_qwen25vl3b_easyr1_annotation_additive_nokl_tmpfs.sh` |
| task-conditioned wrapper | `scripts/run_trace_qwen25vl3b_easyr1_task_conditioned_nokl_tmpfs.sh` |
| reward adapter | `rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py` |
| shared scorer | `trace/core/reward_scoring.py` |
| reward-mode reference | `rlvr/TRACE_REWARD_MODES.md` |

## Dataset

The current dataset is private on Hugging Face:

```text
maveryn/trace
```

Files:

```text
data/train/trace_rlvr_train_64000_all1000_seed42-*.parquet
data/validation/trace_rlvr_validation_iid_2000_all1000_seed1042.parquet
```

Schema:

```text
images
image_sizes
prompt_answer
prompt_answer_and_annotation
answer_gt
annotation_gt
reward_contract
instance_id
domain
task
scene_id
query_id
scene_variant
trace_ref
trace_supervision_mode
```

The training split has `64,000` rows: `1000` active tasks x `64` samples per
task, stored as multiple parquet shards for Hugging Face viewer/range-read
stability. At `ROLLOUT_BATCH_SIZE=128`, `500` optimizer steps is one pass over
the prompt rows before reuse.

The validation parquet has `2,000` IID rows: `1000` active tasks x `2` samples
per task, generated with a different seed.

`trace_supervision_mode` is an additive per-task field with value `answer` or
`answer_and_annotation`. Existing global answer and answer-plus-annotation
runs continue to use their original prompt columns. The `task_conditioned`
mode selects the matching prompt, system prompt, and reward per row.

`images` contains the actual image bytes passed into EasyR1/vLLM.
`image_sizes` contains the width/height of those same image bytes.
`annotation_gt` uses the same image pixel coordinate frame. Do not use
normalized coordinates or model-internal resized tensor coordinates for
annotation rewards.

The generic EasyR1 launcher loads `maveryn/trace@train` and
`maveryn/trace@validation` by default when `TRAIN_FILES` and `VAL_FILES` are unset.

## Host Setup

On a fresh Shadeform-style host:

```bash
cd /home/shadeform
git clone https://github.com/maveryn/trace.git
cd /home/shadeform/trace
git checkout rlvr
git lfs pull
```

Authenticate before launching:

```bash
huggingface-cli login --token "$HF_TOKEN"
wandb login "$WANDB_API_KEY"
```

The launcher defaults to tmpfs paths suitable for high-RAM, low-disk machines:

```text
HF_HOME=/dev/shm/trace_rlvr/cache/huggingface
HF_DATASETS_CACHE=/dev/shm/trace_rlvr/cache/huggingface/datasets
TRANSFORMERS_CACHE=/dev/shm/trace_rlvr/cache/huggingface/transformers
RAY_TMPDIR=/dev/shm/trace_rlvr/ray
WANDB_DIR=/dev/shm/trace_rlvr/wandb
SAVE_CHECKPOINT_PATH=/dev/shm/trace_rlvr/easyr1_checkpoints/<experiment>
```

If the repo is not at `/home/shadeform/trace`, set `REPO_ROOT` explicitly.

## GPU Topology Preflight

Before downloading data or launching a smoke run, report the available GPU count
and the full peer-connectivity matrix:

```bash
nvidia-smi --list-gpus
nvidia-smi topo -m
```

Include the full `nvidia-smi topo -m` output in the handoff/status update and
state whether the host is suitable for the planned `N_GPUS` run:

- Good for 8-GPU EasyR1/FSDP training: all or nearly all GPU-to-GPU pairs among
  `GPU0` through `GPU7` show `NV#` links, for example `NV18`.
- Good for 4-GPU training: the selected four GPUs have broad `NV#`
  connectivity to each other. If only some GPUs are NVLink-connected, set
  `CUDA_VISIBLE_DEVICES` to that connected subset and use `N_GPUS=4`.
- Risky or unsuitable without confirmation: the selected GPU-to-GPU matrix is
  mostly `PHB`, `PXB`, `PIX`, or `SYS`. These hosts can be extremely slow for
  FSDP/NCCL-heavy runs and may fail with NCCL peer-access errors.

Also report the intended values of `CUDA_VISIBLE_DEVICES`, `N_GPUS`, and
`TENSOR_PARALLEL_SIZE`. Do not start a real ablation until this topology check
has been reported.

## Smoke Checks

Verify the HF dataset schema:

```bash
cd /home/shadeform/trace
python - <<'PY'
from datasets import load_dataset

expected = [
    "images",
    "image_sizes",
    "prompt_answer",
    "prompt_answer_and_annotation",
    "answer_gt",
    "annotation_gt",
    "reward_contract",
    "instance_id",
    "domain",
    "task",
    "scene_id",
    "query_id",
    "scene_variant",
    "trace_ref",
    "trace_supervision_mode",
]
row = next(iter(load_dataset("maveryn/trace", split="train", streaming=True, token=True)))
assert list(row) == expected, list(row)
assert row["image_sizes"], row["image_sizes"]
print("ok", row["image_sizes"], row["domain"], row["task"])
PY
```

Run one tiny offline smoke before a real ablation:

```bash
cd /home/shadeform/trace
WANDB_MODE=offline \
MAX_STEPS=1 \
SAVE_FREQ=1 \
VAL_FREQ=1 \
SAVE_LIMIT=2 \
ROLLOUT_BATCH_SIZE=8 \
ACTOR_GLOBAL_BATCH_SIZE=8 \
ROLLOUT_N=2 \
VAL_BATCH_SIZE=16 \
EXPERIMENT_NAME=trace_annotation_smoke_$(date -u +%Y%m%dT%H%M%SZ) \
scripts/run_trace_qwen25vl3b_easyr1_annotation_gated_nokl_tmpfs.sh
```

The smoke passes if it loads the HF parquets, computes reward metrics, logs to
console/W&B, and writes a checkpoint under `/dev/shm/trace_rlvr/easyr1_checkpoints`.

Before a task-conditioned GPU smoke, resolve its configuration without loading
the model:

```bash
cd /home/shadeform/trace
TRACE_RLVR_DRY_RUN=1 \
scripts/run_trace_qwen25vl3b_easyr1_task_conditioned_nokl_tmpfs.sh
```

Then run the same one-step smoke settings with the task-conditioned wrapper.
The loader must select the user prompt and system prompt per row, and the reward
adapter must score each row with that same concrete mode.

## Ablation Matrix

Use one row per machine when possible:

| run | script | `TRACE_ANNOTATION_FRACTION` | task reward |
| --- | --- | --- | --- |
| answer baseline | `scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh` | `0.0` | `answer_reward` |
| gated 0.25 | `scripts/run_trace_qwen25vl3b_easyr1_annotation_gated_nokl_tmpfs.sh` | `0.25` | `answer * (0.75 + 0.25 * annotation)` |
| gated 0.50 | `scripts/run_trace_qwen25vl3b_easyr1_annotation_gated_nokl_tmpfs.sh` | `0.50` | `answer * (0.50 + 0.50 * annotation)` |
| additive 0.25 | `scripts/run_trace_qwen25vl3b_easyr1_annotation_additive_nokl_tmpfs.sh` | `0.25` | `0.75 * answer + 0.25 * annotation` |
| additive 0.50 | `scripts/run_trace_qwen25vl3b_easyr1_annotation_additive_nokl_tmpfs.sh` | `0.50` | `0.50 * answer + 0.50 * annotation` |
| task-conditioned additive 0.50 | `scripts/run_trace_qwen25vl3b_easyr1_task_conditioned_nokl_tmpfs.sh` | `0.50` for annotation rows only | answer reward or `0.50 * answer + 0.50 * annotation`, selected per task |

The optimized scalar is always:

```text
overall = 0.95 * task_reward + 0.05 * format_reward
```

For task-conditioned runs, also track `reward/mode_count/*`,
`reward/mode_fraction/*`, and `reward/by_mode/<mode>/*`. These confirm the
mixed batch contains the expected contracts and expose mode-specific reward
without conflating answer-only rows with annotation rows.

## Background Launch Template

The tested default is `8` visible GPUs, `ROLLOUT_BATCH_SIZE=128`,
`ROLLOUT_N=8`, response cap `2048`, no KL, constant LR `1e-6`, and vision tower
unfrozen.

Example for gated 0.25:

```bash
cd /home/shadeform/trace
mkdir -p logs/rlvr
RUN_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_LOG="logs/rlvr/annotation_gated_ann0p25_${RUN_STAMP}.log"

setsid nohup bash -lc '
  cd /home/shadeform/trace &&
  exec env \
    TRACE_ANNOTATION_FRACTION=0.25 \
    MAX_STEPS=500 \
    SAVE_FREQ=100 \
    VAL_FREQ=100 \
    SAVE_LIMIT=8 \
    VAL_BEFORE_TRAIN=false \
    ROLLOUT_BATCH_SIZE=128 \
    ACTOR_GLOBAL_BATCH_SIZE=128 \
    ROLLOUT_N=8 \
    MAX_PROMPT_LENGTH=2048 \
    MAX_RESPONSE_LENGTH=2048 \
    N_GPUS=8 \
    TENSOR_PARALLEL_SIZE=2 \
    GPU_MEMORY_UTILIZATION=0.6 \
    MAX_NUM_BATCHED_TOKENS=8192 \
    scripts/run_trace_qwen25vl3b_easyr1_annotation_gated_nokl_tmpfs.sh
' > "$RUN_LOG" 2>&1 < /dev/null &

echo $! | tee "${RUN_LOG%.log}.pid"
echo "$RUN_LOG"
```

Change only the wrapper and `TRACE_ANNOTATION_FRACTION` for the other ablation
rows.

Progress commands:

```bash
tail -f "$RUN_LOG"
pgrep -af "run_trace_qwen25vl3b_easyr1|verl.trainer.main"
df -h /dev/shm
nvidia-smi
```

## Metrics To Compare

For training curves:

```text
reward/answer_reward
reward/annotation_reward
reward/format
reward/task_reward_raw
reward/overall
rlvr_stats/zero_solve_rate
rlvr_stats/perfect_solve_rate
```

For validation:

```text
val/reward/answer_reward
val/reward/annotation_reward
val/reward/format
val/reward/task_reward_raw
val/reward/overall
val/zero_solve_rate
val/perfect_solve_rate
```

Use `reward/answer_reward` and `val/reward/answer_reward` for answer-quality
comparisons across answer-only and annotation-mode runs. Do not use
`reward/overall` as the primary cross-mode answer metric because annotation
mode includes annotation reward.

Annotation-type diagnostics are logged as:

```text
reward/annotation_count/<type>
reward/annotation_fraction/<type>
reward/annotation_reward/<type>
```

## Resume

Resume from the global checkpoint directory, not the `actor/` subdirectory:

```bash
LOAD_CHECKPOINT_PATH=/dev/shm/trace_rlvr/easyr1_checkpoints/<experiment>/global_step_200 \
FIND_LAST_CHECKPOINT=false \
MAX_STEPS=500 \
scripts/run_trace_qwen25vl3b_easyr1_annotation_gated_nokl_tmpfs.sh
```

If resuming into the same `SAVE_CHECKPOINT_PATH`, keep the same experiment name
and leave `FIND_LAST_CHECKPOINT=true` so EasyR1 finds the latest checkpoint.

## Stop Conditions

Stop and report if any of these happen:

- HF dataset schema is not the 14-column all1000 schema above.
- `image_sizes` is missing or empty.
- reward metrics do not include `reward/answer_reward`,
  `reward/annotation_reward`, and `reward/format`.
- checkpoints fail to save under `/dev/shm/trace_rlvr/easyr1_checkpoints`.
- validation repeatedly OOMs at the default `VAL_BATCH_SIZE=1024`; lower
  `VAL_BATCH_SIZE` first before changing train settings.
- `/dev/shm` drops below the space needed for the next checkpoint.
