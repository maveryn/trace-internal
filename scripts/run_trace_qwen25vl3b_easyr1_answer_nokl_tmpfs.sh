#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"

export TRACE_OUTPUT_MODE=answer
export TRACE_REWARD_MODE=answer
export TRACE_REWARD_SLUG="${TRACE_REWARD_SLUG:-answer}"
export TRACE_ANSWER_WEIGHT="${TRACE_ANSWER_WEIGHT:-1.0}"
export TRACE_ANNOTATION_WEIGHT="${TRACE_ANNOTATION_WEIGHT:-0.0}"

exec "${REPO_ROOT}/scripts/run_trace_qwen25vl3b_easyr1_nokl_tmpfs.sh"
