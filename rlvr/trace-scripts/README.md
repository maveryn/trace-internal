# TRACE Training Scripts

This directory keeps the active TRACE RLVR launcher surface intentionally small.

## Active files

- `trace_qwen2_5_3b_answer.sh` — Qwen2.5-VL-3B answer-only training.
- `trace_qwen2_5_3b_answer_curriculum.sh` — Qwen2.5-VL-3B answer-only training with self-paced curriculum.
- `trace_qwen2_5_3b_evidence.sh` — Qwen2.5-VL-3B answer+evidence training.
- `trace_qwen2_5_3b_evidence_curriculum.sh` — Qwen2.5-VL-3B answer+evidence training with self-paced curriculum.
- `trace_qwen2_5_3b_common.sh` — shared internal Qwen2.5-VL-3B preflight launcher.
- `trace_qwen3_2b_answer.sh` — Qwen3-VL-2B answer-only training.
- `trace_qwen3_2b_answer_curriculum.sh` — Qwen3-VL-2B answer-only training with self-paced curriculum.
- `trace_qwen3_2b_evidence.sh` — Qwen3-VL-2B answer+evidence training.
- `trace_qwen3_2b_evidence_curriculum.sh` — Qwen3-VL-2B answer+evidence training with self-paced curriculum.
- `trace_qwen3_2b_common.sh` — shared internal Qwen3-VL-2B preflight launcher.
- `trace_shared_launcher.sh` — shared internal RLVR launcher used by the Qwen3-VL-2B wrappers.
- `config_trace.yaml` — shared TRACE RLVR config defaults.
- `validation_pack_qwen3_vl_2b_selected512.sh` — shared 8-dataset validation pack definition.

Archived launchers for other models and older ablation wrappers live under:

- `trace-scripts/archive/`

## Active Qwen2.5-VL-3B runs

These launchers keep the same TRACE training surface, but they use the older
Qwen2.5-VL-3B runtime knobs that matched the earlier 8x H100 run more closely.

Shared launcher settings:

- `MODEL_PATH=Qwen/Qwen2.5-VL-3B-Instruct`
- `CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7`
- `NUM_GPUS=8`
- `flash-attn` / FlashAttention 2 is required; the launcher exits before training if it is unavailable
- `VLLM_USE_FLASHINFER_SAMPLER=0` by default to avoid FlashInfer JIT sampler builds on machines without CUDA dev headers; override to `1` only if that stack is known-good
- `MAX_STEPS=500`
- `VAL_BEFORE_TRAIN=true`
- `VAL_ONLY=false`
- `GPU_MEMORY_UTILIZATION=0.85`
- `ROLLOUT_N=8`
- `MAX_PROMPT_LENGTH=2048`
- `MAX_RESPONSE_LENGTH=1024` for training rollouts
- `VAL_MAX_TOKENS=2048` for validation rollouts
- `ROLLOUT_BATCH_SIZE=128`
- `ACTOR_GLOBAL_BATCH_SIZE=128`
- `ACTOR_MICRO_BATCH_SIZE_UPDATE=4`
- `ACTOR_MICRO_BATCH_SIZE_EXPERIENCE=4`
- `ACTOR_OPTIM_STRATEGY=adamw`
- `VAL_BATCH_SIZE=512`
- `TRAIN_DATALOADER_NUM_WORKERS=8`
- `VAL_DATALOADER_NUM_WORKERS=16`
- `ENABLE_GRADIENT_CHECKPOINTING=true`
- `ACTOR_ENABLE_FULL_SHARD=true`
- `REF_ENABLE_FULL_SHARD=true`
- `PADDING_FREE=true`
- `USE_TORCH_COMPILE=true`

Variant-specific defaults:

- `trace_qwen2_5_3b_answer.sh`
  - `PROMPT_KEY=prompt_answer_only`
  - `TRACE_REWARD_MODE=answer_only`
  - `CURRICULUM_MODE=none`
- `trace_qwen2_5_3b_answer_curriculum.sh`
  - `PROMPT_KEY=prompt_answer_only`
  - `TRACE_REWARD_MODE=answer_only`
  - `CURRICULUM_MODE=self_paced_ema`
- `trace_qwen2_5_3b_evidence.sh`
  - `PROMPT_KEY=prompt_answer_and_evidence`
  - `TRACE_REWARD_MODE=answer_and_evidence`
  - `CURRICULUM_MODE=none`
- `trace_qwen2_5_3b_evidence_curriculum.sh`
  - `PROMPT_KEY=prompt_answer_and_evidence`
  - `TRACE_REWARD_MODE=answer_and_evidence`
  - `CURRICULUM_MODE=self_paced_ema`

Run one of:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/trace_qwen2_5_3b_answer.sh
bash trace-scripts/trace_qwen2_5_3b_answer_curriculum.sh
bash trace-scripts/trace_qwen2_5_3b_evidence.sh
bash trace-scripts/trace_qwen2_5_3b_evidence_curriculum.sh
```

Preflight only:

```bash
cd /home/jovyan/work/trace/rlvr
TRACE_PREFLIGHT_ONLY=1 bash trace-scripts/trace_qwen2_5_3b_evidence.sh
```

## Active Qwen3-VL-2B runs

Default training source:

- `TRAIN_FILE=xashru/trace_rlvr_train_128k_all_tasks.parquet@train`
- Optional local override: `TRAIN_FILE=dataset/train/trace_rlvr_train_128k_all_tasks.parquet`
- Optional smaller smoke-test parquet: build one locally with `scripts/build_trace_train_subset.py`

Default validation pack:

- `dataset/validation/mathverse_mini.parquet`
- `dataset/validation/mathvista_mini.parquet`
- `dataset/validation/mmstar.parquet`
- `dataset/validation/charxiv_dq.parquet`
- `dataset/validation/charxiv_rq.parquet`
- `dataset/validation/embspatialbench.parquet`
- `dataset/validation/blink.parquet`
- `dataset/validation/countqa.parquet`

`combined.parquet` is kept as an offline convenience artifact only. The active
training path uses one validation dataloader per benchmark, matching the
`symrl` validation flow.

Shared launcher settings:

- `MODEL_PATH=Qwen/Qwen3-VL-2B-Instruct`
- `CUDA_VISIBLE_DEVICES=0,1,2,3`
- `NUM_GPUS=4`
- `flash-attn` / FlashAttention 2 is required; the launcher exits before training if it is unavailable
- `VLLM_USE_FLASHINFER_SAMPLER=0` by default to avoid FlashInfer JIT sampler builds on machines without CUDA dev headers; override to `1` only if that stack is known-good
- `MAX_STEPS=500`
- `VAL_BEFORE_TRAIN=true`
- `VAL_ONLY=false`
- `GPU_MEMORY_UTILIZATION=0.9`
- `ROLLOUT_N=8`
- `MAX_PROMPT_LENGTH=2048`
- `MAX_RESPONSE_LENGTH=1024` for training rollouts
- `VAL_MAX_TOKENS=2048` for validation rollouts
- `ROLLOUT_BATCH_SIZE=128`
- `ACTOR_GLOBAL_BATCH_SIZE=128`
- `ACTOR_MICRO_BATCH_SIZE_UPDATE=16`
- `ACTOR_MICRO_BATCH_SIZE_EXPERIENCE=32`
- `VAL_BATCH_SIZE=512`
- `TRAIN_DATALOADER_NUM_WORKERS=8`
- `VAL_DATALOADER_NUM_WORKERS=16`
- `ENABLE_GRADIENT_CHECKPOINTING=false`
- `ACTOR_ENABLE_FULL_SHARD=false`
- `REF_ENABLE_FULL_SHARD=false`
- `PADDING_FREE=true`
- `USE_TORCH_COMPILE=true`

Variant-specific defaults:

- `trace_qwen3_2b_answer.sh`
  - `PROMPT_KEY=prompt_answer_only`
  - `TRACE_REWARD_MODE=answer_only`
  - `CURRICULUM_MODE=none`
- `trace_qwen3_2b_answer_curriculum.sh`
  - `PROMPT_KEY=prompt_answer_only`
  - `TRACE_REWARD_MODE=answer_only`
  - `CURRICULUM_MODE=self_paced_ema`
- `trace_qwen3_2b_evidence.sh`
  - `PROMPT_KEY=prompt_answer_and_evidence`
  - `TRACE_REWARD_MODE=answer_and_evidence`
  - `CURRICULUM_MODE=none`
- `trace_qwen3_2b_evidence_curriculum.sh`
  - `PROMPT_KEY=prompt_answer_and_evidence`
  - `TRACE_REWARD_MODE=answer_and_evidence`
  - `CURRICULUM_MODE=self_paced_ema`

Run one of:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/trace_qwen3_2b_answer.sh
bash trace-scripts/trace_qwen3_2b_answer_curriculum.sh
bash trace-scripts/trace_qwen3_2b_evidence.sh
bash trace-scripts/trace_qwen3_2b_evidence_curriculum.sh
```

Preflight only:

```bash
cd /home/jovyan/work/trace/rlvr
TRACE_PREFLIGHT_ONLY=1 bash trace-scripts/trace_qwen3_2b_evidence.sh
```
