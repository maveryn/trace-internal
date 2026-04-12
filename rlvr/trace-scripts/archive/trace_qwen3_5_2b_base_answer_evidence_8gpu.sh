#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RLVR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/validation_pack_qwen3_vl_2b_selected512.sh"

export PYTHONPATH="${RLVR_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3,4,5,6,7}"
export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3.5-2B-Base}"
export TRAIN_FILE="${TRAIN_FILE:-dataset/train/trace_rlvr_train_128k_all_tasks.parquet}"
export PROMPT_KEY="${PROMPT_KEY:-prompt_answer_and_evidence}"
export TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_and_evidence}"
export VAL_FILES_JSON="${VAL_FILES_JSON:-${DEFAULT_VAL_FILES_JSON}}"
export MAX_STEPS="${MAX_STEPS:-100}"
export VAL_FREQ="${VAL_FREQ:-20}"
export SAVE_FREQ="${SAVE_FREQ:-20}"
export NUM_GPUS="${NUM_GPUS:-8}"
export ROLLOUT_TP="${ROLLOUT_TP:-1}"
export ROLLOUT_N="${ROLLOUT_N:-8}"
export ROLLOUT_BATCH_SIZE="${ROLLOUT_BATCH_SIZE:-128}"
export ACTOR_GLOBAL_BATCH_SIZE="${ACTOR_GLOBAL_BATCH_SIZE:-128}"
export ACTOR_MICRO_BATCH_SIZE_UPDATE="${ACTOR_MICRO_BATCH_SIZE_UPDATE:-4}"
export ACTOR_MICRO_BATCH_SIZE_EXPERIENCE="${ACTOR_MICRO_BATCH_SIZE_EXPERIENCE:-8}"
export TRAIN_DATALOADER_NUM_WORKERS="${TRAIN_DATALOADER_NUM_WORKERS:-4}"
export VAL_DATALOADER_NUM_WORKERS="${VAL_DATALOADER_NUM_WORKERS:-4}"
export GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.8}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export MAX_RESPONSE_LENGTH="${MAX_RESPONSE_LENGTH:-1536}"
export VAL_MAX_TOKENS="${VAL_MAX_TOKENS:-2048}"
export PADDING_FREE="${PADDING_FREE:-false}"
export USE_TORCH_COMPILE="${USE_TORCH_COMPILE:-false}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen3_5_2b_base_trace_answer_evidence_8gpu_val8}"

python3 - "${MODEL_PATH}" <<'PY'
import sys

try:
    from transformers import AutoConfig, AutoProcessor
except Exception as exc:
    raise SystemExit(
        "Failed to import transformers for Qwen3.5 preflight. "
        "Install the base RLVR requirements, then apply requirements-qwen3_5_overlay.txt. "
        f"Original error: {type(exc).__name__}: {exc}"
    ) from exc

model_path = str(sys.argv[1])
try:
    config = AutoConfig.from_pretrained(model_path, trust_remote_code=False)
except Exception as exc:
    raise SystemExit(
        "Failed to load the Qwen3.5 config. "
        "Your transformers build is likely too old for model_type=qwen3_5. "
        "Apply requirements-qwen3_5_overlay.txt and retry. "
        f"Original error: {type(exc).__name__}: {exc}"
    ) from exc
if str(getattr(config, "model_type", "")).strip() != "qwen3_5":
    raise SystemExit(
        f"Expected model_type='qwen3_5' for {model_path}, got {getattr(config, 'model_type', None)!r}."
    )

try:
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=False, use_fast=True)
except Exception as exc:
    raise SystemExit(
        "Failed to build the AutoProcessor for Qwen3.5. "
        "Verify the upgraded transformers install before launching training. "
        f"Original error: {type(exc).__name__}: {exc}"
    ) from exc
processor_name = processor.__class__.__name__
if "Qwen3VLProcessor" not in processor_name:
    raise SystemExit(
        f"Expected a Qwen3VLProcessor-compatible AutoProcessor for {model_path}, got {processor_name!r}."
    )

print(
    "Qwen3.5 preflight passed:",
    f"model_type={config.model_type}",
    f"processor={processor_name}",
)
PY

exec bash "${SCRIPT_DIR}/../trace_shared_launcher.sh"
