#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
export RUN_STAMP

export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-7B-Instruct}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-trace_qwen25vl7b_easyr1_all1000_answer_nokl_step500_bsz128_rollout8_iidval2000_${RUN_STAMP}}"
export SAVE_CHECKPOINT_PATH="${SAVE_CHECKPOINT_PATH:-/dev/shm/trace_rlvr/easyr1_checkpoints/${EXPERIMENT_NAME}}"

export MAX_STEPS="${MAX_STEPS:-500}"
export SAVE_FREQ="${SAVE_FREQ:-100}"
export VAL_FREQ="${VAL_FREQ:-100}"
export SAVE_LIMIT="${SAVE_LIMIT:-2}"
export VAL_BEFORE_TRAIN="${VAL_BEFORE_TRAIN:-false}"
export FIND_LAST_CHECKPOINT="${FIND_LAST_CHECKPOINT:-true}"
export LOAD_CHECKPOINT_PATH="${LOAD_CHECKPOINT_PATH:-null}"

export ROLLOUT_BATCH_SIZE="${ROLLOUT_BATCH_SIZE:-128}"
export ACTOR_GLOBAL_BATCH_SIZE="${ACTOR_GLOBAL_BATCH_SIZE:-128}"
export ROLLOUT_N="${ROLLOUT_N:-8}"
export VAL_BATCH_SIZE="${VAL_BATCH_SIZE:-1024}"
export MAX_PROMPT_LENGTH="${MAX_PROMPT_LENGTH:-2048}"
export MAX_RESPONSE_LENGTH="${MAX_RESPONSE_LENGTH:-2048}"

# Match the proven 3B all1000 rollout memory settings first. Raise these only
# after a stable smoke run on the target hardware.
export GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.6}"
export MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-8192}"
export TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-2}"
export N_GPUS="${N_GPUS:-8}"

exec "${REPO_ROOT}/scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh"
