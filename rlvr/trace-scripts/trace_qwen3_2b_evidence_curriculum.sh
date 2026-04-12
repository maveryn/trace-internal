#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-VL-2B-Instruct}"
export PROMPT_KEY="${PROMPT_KEY:-prompt_answer_and_evidence}"
export TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_and_evidence}"
export CURRICULUM_MODE="${CURRICULUM_MODE:-self_paced_ema}"
export CURRICULUM_ALPHA0="${CURRICULUM_ALPHA0:-0.995}"
export CURRICULUM_BETA="${CURRICULUM_BETA:-2.0}"
export CURRICULUM_EPS_FLOOR="${CURRICULUM_EPS_FLOOR:-}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen3_2b_instruct_trace_evidence_curriculum_8gpu_val8}"

exec bash "${SCRIPT_DIR}/trace_qwen3_2b_common.sh"
