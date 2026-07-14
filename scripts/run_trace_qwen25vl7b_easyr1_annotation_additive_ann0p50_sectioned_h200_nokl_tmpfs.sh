#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
export RUN_STAMP

export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-7B-Instruct}"

export TRACE_OUTPUT_MODE=answer_and_annotation
export TRACE_REWARD_MODE=answer_and_annotation
export TRACE_ANNOTATION_REWARD_FORMULA=additive
export TRACE_ANNOTATION_FRACTION="${TRACE_ANNOTATION_FRACTION:-0.50}"
export SYSTEM_PROMPT_FILE="${SYSTEM_PROMPT_FILE:-${REPO_ROOT}/rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_sectioned_reasoning.txt}"

# Historical 2026-07-13/14 run provenance is recorded in
# rlvr/ablations/annotation_sectioned_qwen25vl7b_additive_500step_20260714/.
# This launcher keeps the reusable H200 defaults for new runs.
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-trace_annotation_additive_ann0p50_sectioned_reasoning_qwen25vl7b_h200_100step_${RUN_STAMP}}"
export SAVE_CHECKPOINT_PATH="${SAVE_CHECKPOINT_PATH:-/dev/shm/trace_rlvr/easyr1_checkpoints/${EXPERIMENT_NAME}}"

export MAX_STEPS="${MAX_STEPS:-100}"
export SAVE_FREQ="${SAVE_FREQ:-100}"
export VAL_FREQ="${VAL_FREQ:-100}"
export SAVE_LIMIT="${SAVE_LIMIT:-2}"
export VAL_BEFORE_TRAIN="${VAL_BEFORE_TRAIN:-false}"
export FIND_LAST_CHECKPOINT="${FIND_LAST_CHECKPOINT:-false}"
export LOAD_CHECKPOINT_PATH="${LOAD_CHECKPOINT_PATH:-null}"

export ROLLOUT_BATCH_SIZE="${ROLLOUT_BATCH_SIZE:-128}"
export ACTOR_GLOBAL_BATCH_SIZE="${ACTOR_GLOBAL_BATCH_SIZE:-128}"
export ROLLOUT_N="${ROLLOUT_N:-8}"
export VAL_BATCH_SIZE="${VAL_BATCH_SIZE:-1024}"
export MAX_PROMPT_LENGTH="${MAX_PROMPT_LENGTH:-2048}"
export MAX_RESPONSE_LENGTH="${MAX_RESPONSE_LENGTH:-2048}"

export GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
export MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-32768}"
export TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-2}"
export N_GPUS="${N_GPUS:-8}"

export ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE="${ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE:-4}"
export ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE="${ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE:-8}"
export REF_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE="${REF_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE:-8}"

exec "${REPO_ROOT}/scripts/run_trace_qwen25vl3b_easyr1_annotation_additive_nokl_tmpfs.sh"
