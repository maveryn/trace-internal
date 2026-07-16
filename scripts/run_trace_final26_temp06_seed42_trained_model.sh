#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
TMP_ROOT="/dev/shm/trace_rlvr"

export REPO_ROOT TMP_ROOT
export SUITE=all26
export SEEDS=42
export GPU_GROUPS="0 1 2 3 4 5 6 7"

export SINGLE_MODEL_SLUG="trace-qwen25vl7b-answer-step500-rerun-20260715"
export SINGLE_MODEL_PATH="${TMP_ROOT}/easyr1_checkpoints/trace_qwen25vl7b_easyr1_all1000_answer_nokl_step500_bsz128_rollout8_iidval2000_rerun_20260715T161252Z/global_step_500/actor/huggingface"
export SINGLE_MODEL_REVISION="sha256set:8396b0be6a760ff7cbbdff02b3017b6b5bc352c87291480aba18fd3e3b6a13b5"
export SINGLE_MODEL_SOURCE="maveryn/trace-qwen25vl7b-rlvr-answer-step500-rerun-20260715T161252Z@896a3e158b912ad9f24c816fad9b790808c983b9"
export SINGLE_MODEL_LABEL="TRACE Qwen2.5-VL-7B Answer RLVR Step 500"

export RUN_TAG="${RUN_TAG:-trace_final26_temp06_seed42_${SINGLE_MODEL_SLUG}}"
export CAMPAIGN_ROOT="${CAMPAIGN_ROOT:-${TMP_ROOT}/${RUN_TAG}}"
export RESULTS_ROOT="${RESULTS_ROOT:-${CAMPAIGN_ROOT}/results}"
export LMUData="${LMUData:-${TMP_ROOT}/LMUData}"

export GEN_TEMPERATURE=0.6
export GEN_TOP_P=1.0
export GEN_TOP_K=-1
export GEN_PRESENCE_PENALTY=0.0
export GEN_REPETITION_PENALTY=1.0
export GEN_MAX_TOKENS=4096

export RUN_REUSE=0
export RUN_HF_ARCHIVE="${RUN_HF_ARCHIVE:-1}"
export HF_ARCHIVE_LOCAL_ONLY="${HF_ARCHIVE_LOCAL_ONLY:-1}"
export HF_ARCHIVE_REPO_ID="${HF_ARCHIVE_REPO_ID:-maveryn/trace-final25-eval-runs}"
export HF_ARCHIVE_TOKEN_FILE="${HF_ARCHIVE_TOKEN_FILE:-${REPO_ROOT}/hf-token.txt}"
export MODEL_VERIFY_DEEP="${MODEL_VERIFY_DEEP:-1}"

exec bash "${REPO_ROOT}/scripts/run_trace_final25_temp06_3seed_8models.sh" "$@"
