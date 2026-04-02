#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VALIDATION_ROOT="${REPO_ROOT}/benchmark/data/external_validation_v1"

DEFAULT_VAL_FILES_JSON="$(printf '[\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"]' \
  "${VALIDATION_ROOT}/mathvista.parquet" \
  "${VALIDATION_ROOT}/mathvision.parquet" \
  "${VALIDATION_ROOT}/charxiv.parquet" \
  "${VALIDATION_ROOT}/ocrbench_v2.parquet" \
  "${VALIDATION_ROOT}/spatialeval.parquet" \
  "${VALIDATION_ROOT}/puzzlevqa.parquet")"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3,4,5,6,7}"
export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-VL-4B-Instruct}"
export TRAIN_FILE="${TRAIN_FILE:-mydata/trace_train_128k_multivariant_hf.parquet}"
export PROMPT_KEY="${PROMPT_KEY:-prompt_answer_and_evidence}"
export TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_and_evidence}"
export CURRICULUM_MODE="${CURRICULUM_MODE:-self_paced_ema}"
export CURRICULUM_ALPHA0="${CURRICULUM_ALPHA0:-0.995}"
export CURRICULUM_BETA="${CURRICULUM_BETA:-2.0}"
export CURRICULUM_EPS_FLOOR="${CURRICULUM_EPS_FLOOR:-}"
export VAL_FILES_JSON="${VAL_FILES_JSON:-${DEFAULT_VAL_FILES_JSON}}"
export MAX_STEPS="${MAX_STEPS:-250}"
export VAL_FREQ="${VAL_FREQ:-20}"
export SAVE_FREQ="${SAVE_FREQ:-20}"
export NUM_GPUS="${NUM_GPUS:-8}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen3_vl_4b_trace_answer_evidence_curriculum_128k_val6}"

exec bash "${SCRIPT_DIR}/qwen2_5-3b-vl-trace-4gpu.sh"
