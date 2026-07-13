#!/usr/bin/env bash
set -euo pipefail

DECODING="${DECODING:-greedy4096}"
case "${DECODING}" in
  greedy4096)
    TEMPERATURE="${TEMPERATURE:-0}"
    TOP_P="${TOP_P:-1}"
    TOP_K="${TOP_K:--1}"
    PRESENCE_PENALTY="${PRESENCE_PENALTY:-0}"
    REPETITION_PENALTY="${REPETITION_PENALTY:-1}"
    SEED_ARGS=()
    ;;
  temp06_4096)
    TEMPERATURE="${TEMPERATURE:-0.6}"
    TOP_P="${TOP_P:-1}"
    TOP_K="${TOP_K:--1}"
    PRESENCE_PENALTY="${PRESENCE_PENALTY:-0}"
    REPETITION_PENALTY="${REPETITION_PENALTY:-1}"
    SEED="${SEED:-42}"
    SEED_ARGS=(--seed "${SEED}")
    ;;
  *)
    echo "Unknown DECODING=${DECODING}; expected greedy4096 or temp06_4096" >&2
    exit 2
    ;;
esac

RUN_TAG="${RUN_TAG:-trace_ann29_${DECODING}_$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_ROOT="${RUN_ROOT:-/dev/shm/trace_rlvr/${RUN_TAG}/runs}"
LATEST_RUN_LINK="${LATEST_RUN_LINK:-/dev/shm/trace_rlvr/trace_ann29_${DECODING}_latest}"
LOG_ROOT="${LOG_ROOT:-/home/shadeform/trace/logs/benchmark/${RUN_TAG}}"
CANDIDATE_SUBSET_ROOT="${CANDIDATE_SUBSET_ROOT:-/home/shadeform/trace/benchmark/subsets/trace_candidate24_full}"

MODEL_SLUG="${MODEL_SLUG:-trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500}"
MODEL_PATH="${MODEL_PATH:-/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500}"

PORT_START="${PORT_START:-18000}"
HOST="${HOST:-127.0.0.1}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-32768}"
MAX_TOKENS="${MAX_TOKENS:-4096}"
CANDIDATE_PARALLELISM_PER_ENDPOINT="${CANDIDATE_PARALLELISM_PER_ENDPOINT:-4}"
EXTRA_PARALLELISM_PER_ENDPOINT="${EXTRA_PARALLELISM_PER_ENDPOINT:-8}"

CANDIDATE_BENCHMARKS=(
  chartmuseum
  game_qa_lite
  screenspot
  screenspotpro
  chartqapro
  puzzlevqa
  logicvista
  mathvista
  cvbench_3d
  wemath
  mathvision
  erqa
  treebench
  countbenchqa
  mathverse
  charxivreason
  phyx_mini_mc
  physics
  mmmu_pro_vision
  blink
  vstarbench
  vlmbias
)

EXTRA_BENCHMARKS=(
  spbench_si_cot
  visualpuzzles
  spatialvizbench_cot
  tablevqabench
  mmhelix
  omni3dbench
  countqa
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

pool_log_dir="${LOG_ROOT}/vllm_${MODEL_SLUG}"
current_pid_file="${pool_log_dir}/pids.txt"

echo "[suite] tag=${RUN_TAG}"
echo "[suite] decoding=${DECODING} temperature=${TEMPERATURE} top_p=${TOP_P} top_k=${TOP_K} presence_penalty=${PRESENCE_PENALTY} repetition_penalty=${REPETITION_PENALTY} max_tokens=${MAX_TOKENS}"
echo "[suite] run_root=${RUN_ROOT}"
echo "[suite] latest_run_link=${LATEST_RUN_LINK}"
echo "[suite] log_root=${LOG_ROOT}"
echo "[suite] model=${MODEL_PATH}"
echo "[suite] endpoints=${#GPU_GROUP_ARRAY[@]}"

MODEL_PATH="${MODEL_PATH}" \
SERVED_MODEL_NAME="${MODEL_SLUG}" \
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
  --model "${MODEL_PATH}" \
  --model-slug "${MODEL_SLUG}" \
  --api-model "${MODEL_SLUG}" \
  "${endpoint_args[@]}" \
  --parallelism-per-endpoint "${CANDIDATE_PARALLELISM_PER_ENDPOINT}" \
  --run-set full \
  --subset-root "${CANDIDATE_SUBSET_ROOT}" \
  --run-root "${RUN_ROOT}" \
  --exact-only \
  --only "${CANDIDATE_BENCHMARKS[@]}" \
  --temperature "${TEMPERATURE}" \
  --top-p "${TOP_P}" \
  --top-k "${TOP_K}" \
  --presence-penalty "${PRESENCE_PENALTY}" \
  --repetition-penalty "${REPETITION_PENALTY}" \
  --max-tokens "${MAX_TOKENS}" \
  "${SEED_ARGS[@]}" \
  2>&1 | tee "${LOG_ROOT}/generation_candidate24_minus_chartqa_visiongraph_${MODEL_SLUG}.log"

python /home/shadeform/trace/scripts/run_external_benchmark_generation_api_queue.py \
  --model "${MODEL_PATH}" \
  --model-slug "${MODEL_SLUG}" \
  --api-model "${MODEL_SLUG}" \
  "${endpoint_args[@]}" \
  --parallelism-per-endpoint "${EXTRA_PARALLELISM_PER_ENDPOINT}" \
  --run-set trace_candidate37_200 \
  --run-root "${RUN_ROOT}" \
  --exact-only \
  --only "${EXTRA_BENCHMARKS[@]}" \
  --temperature "${TEMPERATURE}" \
  --top-p "${TOP_P}" \
  --top-k "${TOP_K}" \
  --presence-penalty "${PRESENCE_PENALTY}" \
  --repetition-penalty "${REPETITION_PENALTY}" \
  --max-tokens "${MAX_TOKENS}" \
  "${SEED_ARGS[@]}" \
  2>&1 | tee "${LOG_ROOT}/generation_extra7_${MODEL_SLUG}.log"

PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh
current_pid_file=""

ln -sfn "$(dirname "${RUN_ROOT}")" "${LATEST_RUN_LINK}"
echo "[suite:done] run_root=${RUN_ROOT}"
echo "[suite:done] latest_run_link=${LATEST_RUN_LINK}"
