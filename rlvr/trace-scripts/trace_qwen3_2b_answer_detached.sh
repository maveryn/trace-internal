#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RLVR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

mkdir -p "${RLVR_ROOT}/logs"

ts="$(date -u +%Y%m%d_%H%M%S)"
log_path="${RLVR_ROOT}/logs/qwen3_2b_answer_${ts}.log"
pid_path="${log_path%.log}.pid"

find_last_checkpoint="${FIND_LAST_CHECKPOINT:-false}"
val_before_train="${VAL_BEFORE_TRAIN:-false}"

launch_cmd=$(
  printf \
    'cd %q && FIND_LAST_CHECKPOINT=%q VAL_BEFORE_TRAIN=%q bash %q' \
    "${RLVR_ROOT}" \
    "${find_last_checkpoint}" \
    "${val_before_train}" \
    "${SCRIPT_DIR}/trace_qwen3_2b_answer.sh"
)

setsid nohup bash -lc "${launch_cmd}" >"${log_path}" 2>&1 < /dev/null &
pid=$!

echo "${pid}" > "${pid_path}"

echo "pid=${pid}"
echo "log=${log_path}"
echo "pid_file=${pid_path}"
