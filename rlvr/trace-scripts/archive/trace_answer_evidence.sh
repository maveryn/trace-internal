#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/validation_pack_qwen3_vl_2b_selected512.sh"

export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-3B-Instruct}"
export TRAIN_FILE="${TRAIN_FILE:-dataset/train/trace_rlvr_train_128k_all_tasks.parquet}"
export PROMPT_KEY="${PROMPT_KEY:-prompt_answer_and_evidence}"
export TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_and_evidence}"
export CURRICULUM_MODE="${CURRICULUM_MODE:-none}"
export VAL_FILES_JSON="${VAL_FILES_JSON:-${DEFAULT_VAL_FILES_JSON}}"
export MAX_STEPS="${MAX_STEPS:-250}"
export VAL_FREQ="${VAL_FREQ:-20}"
export SAVE_FREQ="${SAVE_FREQ:-20}"
export NUM_GPUS="${NUM_GPUS:-4}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen2_5_vl_3b_trace_answer_evidence_128k_val8}"

exec bash "${SCRIPT_DIR}/../trace_shared_launcher.sh"
