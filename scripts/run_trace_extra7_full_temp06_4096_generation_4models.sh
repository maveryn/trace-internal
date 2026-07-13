#!/usr/bin/env bash
set -euo pipefail

RUN_TAG="${RUN_TAG:-trace_extra7_full_temp06_4096_$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_ROOT="${RUN_ROOT:-/dev/shm/trace_rlvr/${RUN_TAG}/runs}"
LATEST_RUN_LINK="${LATEST_RUN_LINK:-/dev/shm/trace_rlvr/trace_extra7_full_temp06_4096_latest}"
LOG_ROOT="${LOG_ROOT:-/home/shadeform/trace/logs/benchmark/${RUN_TAG}}"

PORT_START="${PORT_START:-18000}"
HOST="${HOST:-127.0.0.1}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-32768}"
MAX_TOKENS="${MAX_TOKENS:-4096}"
TEMPERATURE="${TEMPERATURE:-0.6}"
TOP_P="${TOP_P:-1.0}"
TOP_K="${TOP_K:--1}"
PRESENCE_PENALTY="${PRESENCE_PENALTY:-0.0}"
REPETITION_PENALTY="${REPETITION_PENALTY:-1.0}"
GENERATION_SEED="${GENERATION_SEED:-42}"
PARALLELISM_PER_ENDPOINT="${PARALLELISM_PER_ENDPOINT:-8}"

BENCHMARKS=(
  spbench_si_cot
  visualpuzzles
  spatialvizbench_cot
  tablevqabench
  mmhelix
  omni3dbench
  countqa
)

MODEL_SLUGS=(
  qwen25vl3b-base
  trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500
  qwen25vl7b-base
  trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500
)

MODEL_PATHS=(
  Qwen/Qwen2.5-VL-3B-Instruct
  /dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500
  Qwen/Qwen2.5-VL-7B-Instruct
  /dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500
)

mkdir -p "${RUN_ROOT}" "${LOG_ROOT}"

current_pid_file=""
cleanup_current_pool() {
  if [[ -n "${current_pid_file}" && -f "${current_pid_file}" ]]; then
    PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh || true
  fi
}
trap cleanup_current_pool EXIT

endpoint_args=()
if [[ "${GPU_GROUPS}" == *";"* ]]; then
  IFS=';' read -r -a GPU_GROUP_ARRAY <<< "${GPU_GROUPS}"
else
  read -r -a GPU_GROUP_ARRAY <<< "${GPU_GROUPS}"
fi
for offset in "${!GPU_GROUP_ARRAY[@]}"; do
  endpoint_args+=(--api-base "http://${HOST}:$((PORT_START + offset))/v1")
done

benchmark_args=(--only "${BENCHMARKS[@]}")

echo "[suite] tag=${RUN_TAG}"
echo "[suite] run_root=${RUN_ROOT}"
echo "[suite] latest_run_link=${LATEST_RUN_LINK}"
echo "[suite] log_root=${LOG_ROOT}"
echo "[suite] dataset_selection=full_vlmevalkit_datasets"
echo "[suite] decoding temperature=${TEMPERATURE} top_p=${TOP_P} top_k=${TOP_K} presence_penalty=${PRESENCE_PENALTY} repetition_penalty=${REPETITION_PENALTY} max_tokens=${MAX_TOKENS} seed=${GENERATION_SEED}"
echo "[suite] generation endpoints=${#GPU_GROUP_ARRAY[@]} parallelism_per_endpoint=${PARALLELISM_PER_ENDPOINT}"

for i in "${!MODEL_SLUGS[@]}"; do
  slug="${MODEL_SLUGS[$i]}"
  model="${MODEL_PATHS[$i]}"
  pool_log_dir="${LOG_ROOT}/vllm_${slug}"
  current_pid_file="${pool_log_dir}/pids.txt"

  echo "[model:start] slug=${slug} model=${model}"
  MODEL_PATH="${model}" \
  SERVED_MODEL_NAME="${slug}" \
  HOST="${HOST}" \
  PORT_START="${PORT_START}" \
  GPU_GROUPS="${GPU_GROUPS}" \
  GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION}" \
  MAX_MODEL_LEN="${MAX_MODEL_LEN}" \
  MAX_NUM_SEQS="${MAX_NUM_SEQS}" \
  MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS}" \
  LOG_DIR="${pool_log_dir}" \
  PID_FILE="${current_pid_file}" \
    bash /home/shadeform/trace/scripts/start_vllm_endpoint_pool.sh

  python /home/shadeform/trace/scripts/run_external_benchmark_generation_api_queue.py \
    --model "${model}" \
    --model-slug "${slug}" \
    --api-model "${slug}" \
    "${endpoint_args[@]}" \
    --parallelism-per-endpoint "${PARALLELISM_PER_ENDPOINT}" \
    --run-set trace_candidate37_200 \
    --run-root "${RUN_ROOT}" \
    --exact-only \
    "${benchmark_args[@]}" \
    --temperature "${TEMPERATURE}" \
    --top-p "${TOP_P}" \
    --top-k "${TOP_K}" \
    --presence-penalty "${PRESENCE_PENALTY}" \
    --repetition-penalty "${REPETITION_PENALTY}" \
    --max-tokens "${MAX_TOKENS}" \
    --seed "${GENERATION_SEED}" \
    2>&1 | tee "${LOG_ROOT}/generation_${slug}.log"

  PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh
  current_pid_file=""
  echo "[model:done] slug=${slug}"
done

ln -sfn "$(dirname "${RUN_ROOT}")" "${LATEST_RUN_LINK}"
echo "[suite:done] run_root=${RUN_ROOT}"
echo "[suite:done] latest_run_link=${LATEST_RUN_LINK}"
