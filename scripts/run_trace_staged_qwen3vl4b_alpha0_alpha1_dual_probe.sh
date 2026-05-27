#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

RUN_ROOT="${RUN_ROOT:-rlvr/outputs/curriculum_probe/dual_qwen3vl4b_200k_alpha0_alpha1_staged4to16_seed20260504}"
mkdir -p "${RUN_ROOT}"

COMMON_ENV=(
  MODEL="${MODEL:-Qwen/Qwen3-VL-4B-Instruct}"
  REPLICA_WORKERS="${REPLICA_WORKERS:-4}"
  TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
  BATCH_SIZE="${BATCH_SIZE:-4096}"
  STAGE_ROLLOUTS="${STAGE_ROLLOUTS:-4}"
  MAX_ROLLOUTS="${MAX_ROLLOUTS:-16}"
  EASY_RATE="${EASY_RATE:-0.875}"
  MAX_PROMPT_LENGTH="${MAX_PROMPT_LENGTH:-1536}"
  MAX_TOKENS="${MAX_TOKENS:-2048}"
  MAX_PIXELS="${MAX_PIXELS:-1048576}"
  MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
  MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-65536}"
  MAX_NUM_SEQS="${MAX_NUM_SEQS:-4096}"
  GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.95}"
  CPU_THREADS_PER_WORKER="${CPU_THREADS_PER_WORKER:-4}"
  PREFETCH_WORKERS="${PREFETCH_WORKERS:-1}"
  SCORE_WORKERS="${SCORE_WORKERS:-1}"
  SCORE_BACKLOG="${SCORE_BACKLOG:-2}"
  TRACE_ANSWER_SCORING="${TRACE_ANSWER_SCORING:-exact_json}"
  DISABLE_TRTLLM_ATTENTION="${DISABLE_TRTLLM_ATTENTION:-1}"
  ATTENTION_BACKEND="${ATTENTION_BACKEND:-FLASH_ATTN}"
  OVERWRITE="${OVERWRITE:-1}"
  RESUME="${RESUME:-0}"
)

launch_probe() {
  local alpha="$1"
  local gpus="$2"
  local dataset="$3"
  local output_dir="$4"
  local log_file="${RUN_ROOT}/alpha${alpha}.log"

  echo "[launch] alpha=${alpha} gpus=${gpus} dataset=${dataset}"
  echo "[launch] alpha=${alpha} output=${output_dir}"
  (
    export CUDA_VISIBLE_DEVICES="${gpus}"
    env \
      "${COMMON_ENV[@]}" \
      DATASET="${dataset}" \
      OUTPUT_DIR="${output_dir}" \
      bash scripts/run_trace_staged_qwen3vl4b_alpha05_probe.sh
  ) >"${log_file}" 2>&1 &
  echo "$!" >"${RUN_ROOT}/alpha${alpha}.pid"
  echo "[launch] alpha=${alpha} pid=$(cat "${RUN_ROOT}/alpha${alpha}.pid") log=${log_file}"
}

ALPHA0_DATASET="${ALPHA0_DATASET:-rlvr/dataset/train/trace_rlvr_train_200000_query_id_alpha0_answer_seed20260504.parquet}"
ALPHA1_DATASET="${ALPHA1_DATASET:-rlvr/dataset/train/trace_rlvr_train_200000_query_id_alpha1_answer_seed20260504.parquet}"

ALPHA0_OUTPUT="${ALPHA0_OUTPUT:-rlvr/outputs/curriculum_probe/qwen3vl4b_200k_query_id_alpha0_answer_staged4to16_seed20260504}"
ALPHA1_OUTPUT="${ALPHA1_OUTPUT:-rlvr/outputs/curriculum_probe/qwen3vl4b_200k_query_id_alpha1_answer_staged4to16_seed20260504}"

launch_probe "0" "${ALPHA0_GPUS:-0,1,2,3}" "${ALPHA0_DATASET}" "${ALPHA0_OUTPUT}"
launch_probe "1" "${ALPHA1_GPUS:-4,5,6,7}" "${ALPHA1_DATASET}" "${ALPHA1_OUTPUT}"

pid0="$(cat "${RUN_ROOT}/alpha0.pid")"
pid1="$(cat "${RUN_ROOT}/alpha1.pid")"

set +e
wait "${pid0}"
rc0="$?"
wait "${pid1}"
rc1="$?"
set -e

echo "[done] alpha0 rc=${rc0} log=${RUN_ROOT}/alpha0.log"
echo "[done] alpha1 rc=${rc1} log=${RUN_ROOT}/alpha1.log"

if [[ "${rc0}" != "0" || "${rc1}" != "0" ]]; then
  exit 1
fi
