#!/usr/bin/env bash
set -euo pipefail

: "${MODEL_PATH:?Set MODEL_PATH to the HF repo id or local checkpoint path to evaluate.}"
: "${MODEL_SLUG:?Set MODEL_SLUG to the output-safe model slug, e.g. sphinx-qwen7b-500.}"

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_TAG="${RUN_TAG:-trace_final20_temp06_seed42_${MODEL_SLUG}_${RUN_STAMP}}"
TMP_ROOT="${TMP_ROOT:-/dev/shm/trace_rlvr}"
RUN_ROOT="${RUN_ROOT:-${TMP_ROOT}/${RUN_TAG}/runs}"
SCORE_ROOT="${SCORE_ROOT:-${TMP_ROOT}/${RUN_TAG}_score}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-${SCORE_ROOT}/benchmark}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${SCORE_ROOT}/llm_extracted}"
LOG_ROOT="${LOG_ROOT:-/home/shadeform/trace/logs/benchmark/${RUN_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-/home/shadeform/trace/results}"
SUBSET_ROOT="${SUBSET_ROOT:-/home/shadeform/trace/benchmark/subsets/trace_candidate24_full}"
LATEST_LINK="${LATEST_LINK:-${TMP_ROOT}/trace_final20_temp06_seed42_${MODEL_SLUG}_latest}"

HOST="${HOST:-127.0.0.1}"
GEN_PORT_START="${GEN_PORT_START:-18000}"
JUDGE_PORT_START="${JUDGE_PORT_START:-18100}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"

GEN_GPU_MEMORY_UTILIZATION="${GEN_GPU_MEMORY_UTILIZATION:-0.90}"
GEN_MAX_MODEL_LEN="${GEN_MAX_MODEL_LEN:-32768}"
GEN_MAX_NUM_SEQS="${GEN_MAX_NUM_SEQS:-256}"
GEN_MAX_NUM_BATCHED_TOKENS="${GEN_MAX_NUM_BATCHED_TOKENS:-32768}"
GEN_MAX_TOKENS="${GEN_MAX_TOKENS:-4096}"
GEN_TEMPERATURE="${GEN_TEMPERATURE:-0.6}"
GEN_TOP_P="${GEN_TOP_P:-1.0}"
GEN_TOP_K="${GEN_TOP_K:--1}"
GEN_PRESENCE_PENALTY="${GEN_PRESENCE_PENALTY:-0.0}"
GEN_REPETITION_PENALTY="${GEN_REPETITION_PENALTY:-1.0}"
GENERATION_SEED="${GENERATION_SEED:-42}"
GEN_PARALLELISM_PER_ENDPOINT="${GEN_PARALLELISM_PER_ENDPOINT:-32}"

JUDGE_MODEL="${JUDGE_MODEL:-Qwen/Qwen3-32B}"
JUDGE_SERVED_MODEL_NAME="${JUDGE_SERVED_MODEL_NAME:-qwen3-32b-judge}"
JUDGE_GPU_MEMORY_UTILIZATION="${JUDGE_GPU_MEMORY_UTILIZATION:-0.90}"
JUDGE_MAX_MODEL_LEN="${JUDGE_MAX_MODEL_LEN:-8192}"
JUDGE_MAX_NUM_SEQS="${JUDGE_MAX_NUM_SEQS:-128}"
JUDGE_MAX_NUM_BATCHED_TOKENS="${JUDGE_MAX_NUM_BATCHED_TOKENS:-32768}"
JUDGE_MAX_TOKENS="${JUDGE_MAX_TOKENS:-64}"
JUDGE_API_PARALLELISM="${JUDGE_API_PARALLELISM:-16}"
JUDGE_API_BATCH_SIZE="${JUDGE_API_BATCH_SIZE:-128}"
JUDGE_API_BATCHES_PER_ENDPOINT="${JUDGE_API_BATCHES_PER_ENDPOINT:-2}"
JUDGE_API_MAX_BATCH_CHARS="${JUDGE_API_MAX_BATCH_CHARS:-200000}"

RUN_GENERATION="${RUN_GENERATION:-1}"
RUN_SCORE="${RUN_SCORE:-1}"
RUN_SUMMARY="${RUN_SUMMARY:-1}"

CANDIDATE_BENCHMARKS=(
  blink
  chartmuseum
  chartqapro
  charxivreason
  countbenchqa
  cvbench_3d
  game_qa_lite
  logicvista
  mathvision
  mathvista
  mmmu_pro_vision
  physics
  phyx_mini_mc
  puzzlevqa
  screenspot
  treebench
  wemath
)

EXTRA_BENCHMARKS=(
  spatialvizbench_cot
  tablevqabench
  visualpuzzles
)

OFFICIAL_DIRECT_BENCHMARKS=(
  chartmuseum
  screenspot
  logicvista
  mathvista
  mathvision
  charxivreason
  tablevqabench
)

LLM_EXTRACT_BENCHMARKS=(
  blink
  chartqapro
  countbenchqa
  cvbench_3d
  game_qa_lite
  mmmu_pro_vision
  physics
  phyx_mini_mc
  puzzlevqa
  spatialvizbench_cot
  treebench
  visualpuzzles
  wemath
)

ALL_BENCHMARKS=("${OFFICIAL_DIRECT_BENCHMARKS[@]}" "${LLM_EXTRACT_BENCHMARKS[@]}")
MODEL_ARGS=(--model-entry "${MODEL_SLUG}=${MODEL_PATH}")

mkdir -p "${RUN_ROOT}" "${BENCHMARK_ROOT}" "${OUTPUT_ROOT}" "${LOG_ROOT}" "${RESULTS_ROOT}"

current_pid_file=""
cleanup_current_pool() {
  if [[ -n "${current_pid_file}" && -f "${current_pid_file}" ]]; then
    PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh || true
  fi
}
trap cleanup_current_pool EXIT

split_gpu_groups() {
  if [[ "${GPU_GROUPS}" == *";"* ]]; then
    IFS=';' read -r -a GROUP_ARRAY <<< "${GPU_GROUPS}"
  else
    read -r -a GROUP_ARRAY <<< "${GPU_GROUPS}"
  fi
}

build_endpoint_args() {
  local port_start="$1"
  local flag="$2"
  local -n out_array="$3"
  out_array=()
  split_gpu_groups
  for offset in "${!GROUP_ARRAY[@]}"; do
    out_array+=("${flag}" "http://${HOST}:$((port_start + offset))/v1")
  done
}

validate_model_path() {
  if [[ "${MODEL_PATH}" == /* && ! -d "${MODEL_PATH}" ]]; then
    echo "[error] missing local MODEL_PATH: ${MODEL_PATH}" >&2
    exit 1
  fi
}

start_pool() {
  local model="$1"
  local served_name="$2"
  local port_start="$3"
  local log_dir="$4"
  local gpu_mem="$5"
  local max_model_len="$6"
  local max_num_seqs="$7"
  local max_num_batched_tokens="$8"

  current_pid_file="${log_dir}/pids.txt"
  MODEL_PATH="${model}" \
  SERVED_MODEL_NAME="${served_name}" \
  HOST="${HOST}" \
  PORT_START="${port_start}" \
  GPU_GROUPS="${GPU_GROUPS}" \
  GPU_MEMORY_UTILIZATION="${gpu_mem}" \
  MAX_MODEL_LEN="${max_model_len}" \
  MAX_NUM_SEQS="${max_num_seqs}" \
  MAX_NUM_BATCHED_TOKENS="${max_num_batched_tokens}" \
  LOG_DIR="${log_dir}" \
  PID_FILE="${current_pid_file}" \
    bash /home/shadeform/trace/scripts/start_vllm_endpoint_pool.sh
}

stop_pool() {
  if [[ -n "${current_pid_file}" && -f "${current_pid_file}" ]]; then
    PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh
  fi
  current_pid_file=""
}

run_generation() {
  validate_model_path
  local -a api_args
  build_endpoint_args "${GEN_PORT_START}" "--api-base" api_args

  echo "[generation:start] model_slug=${MODEL_SLUG} model=${MODEL_PATH}"
  echo "[generation] run_root=${RUN_ROOT}"
  echo "[generation] benchmarks=${#CANDIDATE_BENCHMARKS[@]} candidate + ${#EXTRA_BENCHMARKS[@]} extra"
  echo "[generation] decoding temperature=${GEN_TEMPERATURE} top_p=${GEN_TOP_P} top_k=${GEN_TOP_K} presence_penalty=${GEN_PRESENCE_PENALTY} repetition_penalty=${GEN_REPETITION_PENALTY} max_tokens=${GEN_MAX_TOKENS} seed=${GENERATION_SEED}"
  echo "[generation] gpu_groups=${GPU_GROUPS} parallelism_per_endpoint=${GEN_PARALLELISM_PER_ENDPOINT}"

  start_pool "${MODEL_PATH}" "${MODEL_SLUG}" "${GEN_PORT_START}" "${LOG_ROOT}/vllm_generation_${MODEL_SLUG}" "${GEN_GPU_MEMORY_UTILIZATION}" "${GEN_MAX_MODEL_LEN}" "${GEN_MAX_NUM_SEQS}" "${GEN_MAX_NUM_BATCHED_TOKENS}"

  python /home/shadeform/trace/scripts/run_external_benchmark_generation_api_queue.py \
    --model "${MODEL_PATH}" \
    --model-slug "${MODEL_SLUG}" \
    --api-model "${MODEL_SLUG}" \
    "${api_args[@]}" \
    --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
    --run-set full \
    --subset-root "${SUBSET_ROOT}" \
    --run-root "${RUN_ROOT}" \
    --exact-only \
    --only "${CANDIDATE_BENCHMARKS[@]}" \
    --temperature "${GEN_TEMPERATURE}" \
    --top-p "${GEN_TOP_P}" \
    --top-k "${GEN_TOP_K}" \
    --presence-penalty "${GEN_PRESENCE_PENALTY}" \
    --repetition-penalty "${GEN_REPETITION_PENALTY}" \
    --max-tokens "${GEN_MAX_TOKENS}" \
    --seed "${GENERATION_SEED}" \
    2>&1 | tee "${LOG_ROOT}/generation_${MODEL_SLUG}_candidate.log"

  python /home/shadeform/trace/scripts/run_external_benchmark_generation_api_queue.py \
    --model "${MODEL_PATH}" \
    --model-slug "${MODEL_SLUG}" \
    --api-model "${MODEL_SLUG}" \
    "${api_args[@]}" \
    --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
    --run-set trace_candidate37_200 \
    --run-root "${RUN_ROOT}" \
    --exact-only \
    --only "${EXTRA_BENCHMARKS[@]}" \
    --temperature "${GEN_TEMPERATURE}" \
    --top-p "${GEN_TOP_P}" \
    --top-k "${GEN_TOP_K}" \
    --presence-penalty "${GEN_PRESENCE_PENALTY}" \
    --repetition-penalty "${GEN_REPETITION_PENALTY}" \
    --max-tokens "${GEN_MAX_TOKENS}" \
    --seed "${GENERATION_SEED}" \
    2>&1 | tee "${LOG_ROOT}/generation_${MODEL_SLUG}_extra.log"

  stop_pool
  ln -sfn "$(dirname "${RUN_ROOT}")" "${LATEST_LINK}"
  echo "[generation:done] run_root=${RUN_ROOT}"
}

run_score() {
  local -a judge_endpoint_args
  local -a llm_endpoint_args
  build_endpoint_args "${JUDGE_PORT_START}" "--judge-api-base" judge_endpoint_args
  build_endpoint_args "${JUDGE_PORT_START}" "--api-base" llm_endpoint_args

  echo "[score:start] model_slug=${MODEL_SLUG}"
  echo "[score] benchmark_root=${BENCHMARK_ROOT}"
  echo "[score] output_root=${OUTPUT_ROOT}"
  echo "[score] judge=${JUDGE_MODEL} served=${JUDGE_SERVED_MODEL_NAME}"

  start_pool "${JUDGE_MODEL}" "${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_PORT_START}" "${LOG_ROOT}/vllm_${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_GPU_MEMORY_UTILIZATION}" "${JUDGE_MAX_MODEL_LEN}" "${JUDGE_MAX_NUM_SEQS}" "${JUDGE_MAX_NUM_BATCHED_TOKENS}"

  python /home/shadeform/trace/scripts/run_external_benchmark_score_multi_model_queue.py \
    "${MODEL_ARGS[@]}" \
    --queue-name "${RUN_TAG}_official_direct" \
    --run-set trace_candidate37_200 \
    --run-root "${RUN_ROOT}" \
    --benchmark-root "${BENCHMARK_ROOT}" \
    --exact-only \
    --only "${OFFICIAL_DIRECT_BENCHMARKS[@]}" \
    --judge-model "${JUDGE_MODEL}" \
    --judge-max-tokens "${JUDGE_MAX_TOKENS}" \
    --judge-api-model "${JUDGE_SERVED_MODEL_NAME}" \
    --judge-api-tokenizer-model "${JUDGE_MODEL}" \
    --judge-api-parallelism "${JUDGE_API_PARALLELISM}" \
    "${judge_endpoint_args[@]}" \
    2>&1 | tee "${LOG_ROOT}/score_official_direct.log"

  python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
    --prepare \
    --queue-name "${RUN_TAG}_llm_extract" \
    --run-root "${RUN_ROOT}" \
    --queue-root /home/shadeform/trace/benchmark/queues \
    --output-root "${OUTPUT_ROOT}" \
    --benchmark-root "${BENCHMARK_ROOT}" \
    "${MODEL_ARGS[@]}" \
    --benchmarks "${LLM_EXTRACT_BENCHMARKS[@]}" \
    2>&1 | tee "${LOG_ROOT}/llm_extract_prepare.log"

  python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
    --api-run \
    --queue-name "${RUN_TAG}_llm_extract" \
    --run-root "${RUN_ROOT}" \
    --queue-root /home/shadeform/trace/benchmark/queues \
    --output-root "${OUTPUT_ROOT}" \
    --benchmark-root "${BENCHMARK_ROOT}" \
    "${MODEL_ARGS[@]}" \
    --benchmarks "${LLM_EXTRACT_BENCHMARKS[@]}" \
    --api-model "${JUDGE_SERVED_MODEL_NAME}" \
    --api-tokenizer-model "${JUDGE_MODEL}" \
    --api-parallelism "${JUDGE_API_PARALLELISM}" \
    --api-batch-size "${JUDGE_API_BATCH_SIZE}" \
    --api-batches-per-endpoint "${JUDGE_API_BATCHES_PER_ENDPOINT}" \
    --api-max-batch-chars "${JUDGE_API_MAX_BATCH_CHARS}" \
    --judge-model "${JUDGE_MODEL}" \
    --judge-max-tokens "${JUDGE_MAX_TOKENS}" \
    "${llm_endpoint_args[@]}" \
    2>&1 | tee "${LOG_ROOT}/llm_extract_api.log"

  python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
    --finalize \
    --queue-name "${RUN_TAG}_llm_extract" \
    --run-root "${RUN_ROOT}" \
    --queue-root /home/shadeform/trace/benchmark/queues \
    --output-root "${OUTPUT_ROOT}" \
    --benchmark-root "${BENCHMARK_ROOT}" \
    "${MODEL_ARGS[@]}" \
    --benchmarks "${LLM_EXTRACT_BENCHMARKS[@]}" \
    --judge-model "${JUDGE_MODEL}" \
    2>&1 | tee "${LOG_ROOT}/llm_extract_finalize.log"

  stop_pool
  echo "[score:done] benchmark_root=${BENCHMARK_ROOT}"
}

run_summary() {
  local markdown="${RESULTS_ROOT}/${RUN_TAG}_results.md"
  local excel="${RESULTS_ROOT}/${RUN_TAG}_results.xlsx"

  python /home/shadeform/trace/scripts/summarize_trace_candidate37_200_results.py \
    --benchmark-root "${BENCHMARK_ROOT}" \
    --run-root "${RUN_ROOT}" \
    --suite-name "trace_final20_temp06_seed42" \
    --run-set trace_candidate37_200 \
    --subset-root "${SUBSET_ROOT}" \
    --subset-label "final20 full eval; candidate benchmarks use trace_candidate24_full subset manifests; SpatialVizBench/TableVQABench/VisualPuzzles use full VLMEvalKit datasets" \
    --title "TRACE Final20 Temp0.6 Seed42 Benchmark Results: ${MODEL_SLUG}" \
    --markdown "${markdown}" \
    --excel "${excel}" \
    --models "${MODEL_SLUG}" \
    --only "${ALL_BENCHMARKS[@]}" \
    2>&1 | tee "${LOG_ROOT}/summarize.log"

  echo "[summary:done] markdown=${markdown}"
  echo "[summary:done] excel=${excel}"
}

echo "[suite] tag=${RUN_TAG}"
echo "[suite] model_slug=${MODEL_SLUG}"
echo "[suite] model_path=${MODEL_PATH}"
echo "[suite] run_root=${RUN_ROOT}"
echo "[suite] score_root=${SCORE_ROOT}"
echo "[suite] log_root=${LOG_ROOT}"
echo "[suite] latest_link=${LATEST_LINK}"

if [[ "${RUN_GENERATION}" == "1" ]]; then
  run_generation
fi

if [[ "${RUN_SCORE}" == "1" ]]; then
  run_score
fi

if [[ "${RUN_SUMMARY}" == "1" ]]; then
  run_summary
fi

echo "[suite:done] tag=${RUN_TAG}"
echo "[suite:done] latest_link=${LATEST_LINK}"
