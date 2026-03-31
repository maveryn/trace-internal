#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VALIDATION_ROOT="${REPO_ROOT}/benchmark/data/external_validation_v1"

DEFAULT_VAL_FILES_JSON="$(printf '[\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"]' \
  "${VALIDATION_ROOT}/mathvista.parquet" \
  "${VALIDATION_ROOT}/mathvision.parquet" \
  "${VALIDATION_ROOT}/charxiv.parquet" \
  "${VALIDATION_ROOT}/ocrbench_v2.parquet" \
  "${VALIDATION_ROOT}/seephys.parquet" \
  "${VALIDATION_ROOT}/spatialeval.parquet" \
  "${VALIDATION_ROOT}/vgcure.parquet" \
  "${VALIDATION_ROOT}/puzzlevqa.parquet")"

export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-3B-Instruct}"
export TRAIN_FILE="${TRAIN_FILE:-mydata/trace_train_128k_multivariant_hf.parquet}"
export PROMPT_KEY="${PROMPT_KEY:-prompt_answer_only}"
export TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_only}"
export CURRICULUM_MODE="${CURRICULUM_MODE:-self_paced_ema}"
export CURRICULUM_ALPHA0="${CURRICULUM_ALPHA0:-0.995}"
export CURRICULUM_BETA="${CURRICULUM_BETA:-2.0}"
export CURRICULUM_EPS_FLOOR="${CURRICULUM_EPS_FLOOR:-}"
export VAL_FILES_JSON="${VAL_FILES_JSON:-${DEFAULT_VAL_FILES_JSON}}"
export MAX_STEPS="${MAX_STEPS:-500}"
export VAL_FREQ="${VAL_FREQ:-20}"
export SAVE_FREQ="${SAVE_FREQ:-20}"
export NUM_GPUS="${NUM_GPUS:-4}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen2_5_vl_3b_trace_answer_only_curriculum_128k_val8}"

exec bash "${SCRIPT_DIR}/qwen2_5-3b-vl-trace-4gpu.sh"
