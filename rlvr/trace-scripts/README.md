# TRACE Training Scripts

This directory keeps the active TRACE RLVR launcher surface intentionally small.

## Active files

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

## Active Qwen3-VL-2B runs

Default training parquet:

- `TRAIN_FILE=dataset/train/trace_rlvr_train_128k_all_tasks.parquet`

Default validation pack:

- `dataset/validation/mathverse_mini.parquet`
- `dataset/validation/mathvista_mini.parquet`
- `dataset/validation/mmstar.parquet`
- `dataset/validation/charxiv_dq.parquet`
- `dataset/validation/charxiv_rq.parquet`
- `dataset/validation/embspatialbench.parquet`
- `dataset/validation/blink.parquet`
- `dataset/validation/countqa.parquet`

Shared launcher settings:

- `MODEL_PATH=Qwen/Qwen3-VL-2B-Instruct`
- `CUDA_VISIBLE_DEVICES=0,1`
- `NUM_GPUS=2`
- `flash-attn` / FlashAttention 2 is required; the launcher exits before training if it is unavailable
- `MAX_STEPS=500`
- `GPU_MEMORY_UTILIZATION=0.9`
- `ROLLOUT_N=8`
- `MAX_RESPONSE_LENGTH=1024` for training rollouts
- `VAL_MAX_TOKENS=2048` for validation rollouts
- `ROLLOUT_BATCH_SIZE=32`
- `ACTOR_GLOBAL_BATCH_SIZE=32`
- `ACTOR_MICRO_BATCH_SIZE_UPDATE=4`
- `ACTOR_MICRO_BATCH_SIZE_EXPERIENCE=4`
- `PADDING_FREE=false`
- `USE_TORCH_COMPILE=false`

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
