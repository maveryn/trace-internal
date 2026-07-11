#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"

export TRACE_OUTPUT_MODE=answer_and_annotation
export TRACE_REWARD_MODE=answer_and_annotation
export TRACE_ANNOTATION_REWARD_FORMULA=additive
export TRACE_ANNOTATION_FRACTION="${TRACE_ANNOTATION_FRACTION:-0.5}"

exec "${REPO_ROOT}/scripts/run_trace_qwen25vl3b_easyr1_nokl_tmpfs.sh"
