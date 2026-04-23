#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

export TRAIN_FILES="${TRAIN_FILES:-$REPO_ROOT/dataset/train/trace_rlvr_train_51k_solve_0125_0750_uniform.parquet}"
export MAX_RESPONSE_LENGTH="${MAX_RESPONSE_LENGTH:-4096}"
export TRACE_ANSWER_SCORING="${TRACE_ANSWER_SCORING:-legacy_strict}"
export TRAINER_EXPERIMENT_SUFFIX="${TRAINER_EXPERIMENT_SUFFIX:-trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp}"

exec "$SCRIPT_DIR/run_trace_qwen3vl_2b_answer.sh" "$@"
