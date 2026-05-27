#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-VL-2B-Instruct}"
export TRACE_OUTPUT_MODE="${TRACE_OUTPUT_MODE:-answer}"
export TRAINER_EXPERIMENT_SUFFIX="${TRAINER_EXPERIMENT_SUFFIX:-trace_qwen3_2b_answer}"
export TRAINER_APPEND_TIMESTAMP="${TRAINER_APPEND_TIMESTAMP:-1}"

exec "$SCRIPT_DIR/run_trace_vl_rlvr.sh" "$@"
