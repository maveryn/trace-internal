#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-3B-Instruct}"
export PROMPT_KEY="${PROMPT_KEY:-prompt_answer_only}"
export TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_only}"
export CURRICULUM_MODE="${CURRICULUM_MODE:-none}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-trace_qwen2_5_3b_answer}"

exec bash "${SCRIPT_DIR}/trace_qwen2_5_3b_common.sh"
