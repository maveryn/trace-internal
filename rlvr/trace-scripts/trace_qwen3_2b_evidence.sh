#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-VL-2B-Instruct}"
export PROMPT_KEY="${PROMPT_KEY:-prompt_answer_and_evidence}"
export TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_and_evidence}"
export CURRICULUM_MODE="${CURRICULUM_MODE:-none}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen3_2b_instruct_trace_evidence_8gpu_val8}"

exec bash "${SCRIPT_DIR}/trace_qwen3_2b_common.sh"
