#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-3B-Instruct}"
export PROMPT_KEY="${PROMPT_KEY:-prompt_answer_only}"
export TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_only}"
export CURRICULUM_MODE="${CURRICULUM_MODE:-self_paced_ema}"
export CURRICULUM_ALPHA0="${CURRICULUM_ALPHA0:-0.995}"
export CURRICULUM_BETA="${CURRICULUM_BETA:-2.0}"
export CURRICULUM_EPS_FLOOR="${CURRICULUM_EPS_FLOOR:-}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-trace_qwen2_5_3b_answer_curriculum}"

exec bash "${SCRIPT_DIR}/trace_qwen2_5_3b_common.sh"
