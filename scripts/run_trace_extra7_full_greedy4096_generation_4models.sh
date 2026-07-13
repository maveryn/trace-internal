#!/usr/bin/env bash
set -euo pipefail

RUN_TAG="${RUN_TAG:-trace_extra7_full_greedy4096_$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_ROOT="${RUN_ROOT:-/dev/shm/trace_rlvr/${RUN_TAG}/runs}"
LATEST_RUN_LINK="${LATEST_RUN_LINK:-/dev/shm/trace_rlvr/trace_extra7_full_greedy4096_latest}"
LOG_ROOT="${LOG_ROOT:-/home/shadeform/trace/logs/benchmark/${RUN_TAG}}"
SUBSET_ROOT="${SUBSET_ROOT:-/home/shadeform/trace/benchmark/subsets/trace_extra7_full}"
PREVIOUS_SUBSET_ROOT="${PREVIOUS_SUBSET_ROOT:-/home/shadeform/trace/benchmark/subsets/trace_candidate37_200}"
SUBSET_TARGET_SIZE="${SUBSET_TARGET_SIZE:-1000000}"
SAMPLE_SEED="${SAMPLE_SEED:-42}"

PORT_START="${PORT_START:-18000}"
HOST="${HOST:-127.0.0.1}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-32768}"
MAX_TOKENS="${MAX_TOKENS:-4096}"
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

if [[ ! -f "${SUBSET_ROOT}/manifest.json" ]]; then
  echo "[subset:build] subset_root=${SUBSET_ROOT} target_size=${SUBSET_TARGET_SIZE}"
  python /home/shadeform/trace/scripts/build_trace_benchmark_stage_subset.py \
    --previous-root "${PREVIOUS_SUBSET_ROOT}" \
    --out-root "${SUBSET_ROOT}" \
    --target-size "${SUBSET_TARGET_SIZE}" \
    --sample-seed "${SAMPLE_SEED}" \
    --subset-version "trace_extra7_full_seed${SAMPLE_SEED}" \
    --allow-missing-previous \
    --only "${BENCHMARKS[@]}" \
    2>&1 | tee "${LOG_ROOT}/build_subset.log"
fi

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
echo "[suite] subset_root=${SUBSET_ROOT}"
echo "[suite] decoding temperature=0 top_p=1 top_k=-1 presence_penalty=0 repetition_penalty=1 max_tokens=${MAX_TOKENS}"
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
    --subset-root "${SUBSET_ROOT}" \
    --run-root "${RUN_ROOT}" \
    --exact-only \
    "${benchmark_args[@]}" \
    --temperature 0 \
    --top-p 1 \
    --top-k -1 \
    --presence-penalty 0 \
    --repetition-penalty 1 \
    --max-tokens "${MAX_TOKENS}" \
    2>&1 | tee "${LOG_ROOT}/generation_${slug}.log"

  PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh
  current_pid_file=""
  echo "[model:done] slug=${slug}"
done

ln -sfn "$(dirname "${RUN_ROOT}")" "${LATEST_RUN_LINK}"
echo "[suite:done] run_root=${RUN_ROOT}"
echo "[suite:done] latest_run_link=${LATEST_RUN_LINK}"
