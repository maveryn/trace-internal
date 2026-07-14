#!/usr/bin/env bash
set -euo pipefail

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_TAG="${RUN_TAG:-trace_selected25_full_temp06_4096_seed43_44_answer_3b7b_${RUN_STAMP}}"
TMP_ROOT="${TMP_ROOT:-/dev/shm/trace_rlvr}"
RUN_ROOT_BASE="${RUN_ROOT_BASE:-${TMP_ROOT}/${RUN_TAG}}"
SCORE_ROOT_BASE="${SCORE_ROOT_BASE:-${TMP_ROOT}/${RUN_TAG}_score}"
LOG_ROOT="${LOG_ROOT:-/home/shadeform/trace/logs/benchmark/${RUN_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-/home/shadeform/trace/results}"
SUBSET_ROOT="${SUBSET_ROOT:-/home/shadeform/trace/benchmark/subsets/trace_candidate24_full}"
LATEST_LINK="${LATEST_LINK:-${TMP_ROOT}/trace_selected25_full_temp06_seed43_44_answer_3b7b_latest}"

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

SEEDS=(${SEEDS:-43 44})

CANDIDATE_BENCHMARKS=(
  blink
  chartmuseum
  chartqapro
  charxivreason
  countbenchqa
  cvbench_3d
  erqa
  game_qa_lite
  logicvista
  mathverse
  mathvision
  mathvista
  mmmu_pro_vision
  physics
  phyx_mini_mc
  puzzlevqa
  screenspot
  treebench
  vstarbench
  wemath
)

EXTRA_BENCHMARKS=(
  countqa
  mmhelix
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
  mathverse
  charxivreason
  mmhelix
  tablevqabench
)

LLM_EXTRACT_BENCHMARKS=(
  blink
  chartqapro
  countbenchqa
  countqa
  cvbench_3d
  erqa
  game_qa_lite
  mmmu_pro_vision
  physics
  phyx_mini_mc
  puzzlevqa
  spatialvizbench_cot
  treebench
  visualpuzzles
  vstarbench
  wemath
)

ALL_BENCHMARKS=("${OFFICIAL_DIRECT_BENCHMARKS[@]}" "${LLM_EXTRACT_BENCHMARKS[@]}")

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

MODEL_ARGS=(
  --model-entry qwen25vl3b-base=Qwen/Qwen2.5-VL-3B-Instruct
  --model-entry trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500=/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500
  --model-entry qwen25vl7b-base=Qwen/Qwen2.5-VL-7B-Instruct
  --model-entry trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500=/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500
)

mkdir -p "${RUN_ROOT_BASE}" "${SCORE_ROOT_BASE}" "${LOG_ROOT}" "${RESULTS_ROOT}"

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

validate_local_models() {
  for model in "${MODEL_PATHS[@]}"; do
    if [[ "${model}" == /* && ! -d "${model}" ]]; then
      echo "[error] missing local model path: ${model}" >&2
      exit 1
    fi
  done
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

run_generation_for_model_seed() {
  local slug="$1"
  local model="$2"
  local seed="$3"
  local run_root="${RUN_ROOT_BASE}/seed_${seed}/runs"
  local -a api_args
  build_endpoint_args "${GEN_PORT_START}" "--api-base" api_args

  mkdir -p "${run_root}"

  echo "[generate:candidate] seed=${seed} slug=${slug} run_root=${run_root}"
  python /home/shadeform/trace/scripts/run_external_benchmark_generation_api_queue.py \
    --model "${model}" \
    --model-slug "${slug}" \
    --api-model "${slug}" \
    "${api_args[@]}" \
    --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
    --run-set full \
    --subset-root "${SUBSET_ROOT}" \
    --run-root "${run_root}" \
    --exact-only \
    --only "${CANDIDATE_BENCHMARKS[@]}" \
    --temperature "${GEN_TEMPERATURE}" \
    --top-p "${GEN_TOP_P}" \
    --top-k "${GEN_TOP_K}" \
    --presence-penalty "${GEN_PRESENCE_PENALTY}" \
    --repetition-penalty "${GEN_REPETITION_PENALTY}" \
    --max-tokens "${GEN_MAX_TOKENS}" \
    --seed "${seed}" \
    2>&1 | tee "${LOG_ROOT}/generation_seed${seed}_${slug}_candidate.log"

  echo "[generate:extra] seed=${seed} slug=${slug} run_root=${run_root}"
  python /home/shadeform/trace/scripts/run_external_benchmark_generation_api_queue.py \
    --model "${model}" \
    --model-slug "${slug}" \
    --api-model "${slug}" \
    "${api_args[@]}" \
    --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
    --run-set trace_candidate37_200 \
    --run-root "${run_root}" \
    --exact-only \
    --only "${EXTRA_BENCHMARKS[@]}" \
    --temperature "${GEN_TEMPERATURE}" \
    --top-p "${GEN_TOP_P}" \
    --top-k "${GEN_TOP_K}" \
    --presence-penalty "${GEN_PRESENCE_PENALTY}" \
    --repetition-penalty "${GEN_REPETITION_PENALTY}" \
    --max-tokens "${GEN_MAX_TOKENS}" \
    --seed "${seed}" \
    2>&1 | tee "${LOG_ROOT}/generation_seed${seed}_${slug}_extra.log"
}

run_generation() {
  validate_local_models
  echo "[generation] tag=${RUN_TAG}"
  echo "[generation] seeds=${SEEDS[*]}"
  echo "[generation] decoding temperature=${GEN_TEMPERATURE} top_p=${GEN_TOP_P} top_k=${GEN_TOP_K} presence_penalty=${GEN_PRESENCE_PENALTY} repetition_penalty=${GEN_REPETITION_PENALTY} max_tokens=${GEN_MAX_TOKENS}"
  echo "[generation] endpoints=${GPU_GROUPS} parallelism_per_endpoint=${GEN_PARALLELISM_PER_ENDPOINT}"
  for i in "${!MODEL_SLUGS[@]}"; do
    local slug="${MODEL_SLUGS[$i]}"
    local model="${MODEL_PATHS[$i]}"
    local pool_log_dir="${LOG_ROOT}/vllm_generation_${slug}"
    echo "[model:start] slug=${slug} model=${model}"
    start_pool "${model}" "${slug}" "${GEN_PORT_START}" "${pool_log_dir}" "${GEN_GPU_MEMORY_UTILIZATION}" "${GEN_MAX_MODEL_LEN}" "${GEN_MAX_NUM_SEQS}" "${GEN_MAX_NUM_BATCHED_TOKENS}"
    for seed in "${SEEDS[@]}"; do
      run_generation_for_model_seed "${slug}" "${model}" "${seed}"
    done
    stop_pool
    echo "[model:done] slug=${slug}"
  done
  ln -sfn "${RUN_ROOT_BASE}" "${LATEST_LINK}"
  echo "[generation:done] run_root_base=${RUN_ROOT_BASE}"
}

run_score_for_seed() {
  local seed="$1"
  local run_root="${RUN_ROOT_BASE}/seed_${seed}/runs"
  local benchmark_root="${SCORE_ROOT_BASE}/seed_${seed}/benchmark"
  local output_root="${SCORE_ROOT_BASE}/seed_${seed}/llm_extracted"
  local score_tag="${RUN_TAG}_seed${seed}_score"
  local -a judge_endpoint_args
  local -a llm_endpoint_args
  build_endpoint_args "${JUDGE_PORT_START}" "--judge-api-base" judge_endpoint_args
  build_endpoint_args "${JUDGE_PORT_START}" "--api-base" llm_endpoint_args

  mkdir -p "${benchmark_root}" "${output_root}"

  echo "[score:direct] seed=${seed} run_root=${run_root}"
  python /home/shadeform/trace/scripts/run_external_benchmark_score_multi_model_queue.py \
    "${MODEL_ARGS[@]}" \
    --queue-name "${score_tag}_official_direct" \
    --run-set trace_candidate37_200 \
    --run-root "${run_root}" \
    --benchmark-root "${benchmark_root}" \
    --exact-only \
    --only "${OFFICIAL_DIRECT_BENCHMARKS[@]}" \
    --judge-model "${JUDGE_MODEL}" \
    --judge-max-tokens "${JUDGE_MAX_TOKENS}" \
    --judge-api-model "${JUDGE_SERVED_MODEL_NAME}" \
    --judge-api-tokenizer-model "${JUDGE_MODEL}" \
    --judge-api-parallelism "${JUDGE_API_PARALLELISM}" \
    "${judge_endpoint_args[@]}" \
    2>&1 | tee "${LOG_ROOT}/score_seed${seed}_official_direct.log"

  echo "[score:llm-extract:prepare] seed=${seed}"
  python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
    --prepare \
    --queue-name "${score_tag}_llm_extract" \
    --run-root "${run_root}" \
    --queue-root /home/shadeform/trace/benchmark/queues \
    --output-root "${output_root}" \
    --benchmark-root "${benchmark_root}" \
    "${MODEL_ARGS[@]}" \
    --benchmarks "${LLM_EXTRACT_BENCHMARKS[@]}" \
    2>&1 | tee "${LOG_ROOT}/llm_extract_seed${seed}_prepare.log"

  echo "[score:llm-extract:api] seed=${seed}"
  python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
    --api-run \
    --queue-name "${score_tag}_llm_extract" \
    --run-root "${run_root}" \
    --queue-root /home/shadeform/trace/benchmark/queues \
    --output-root "${output_root}" \
    --benchmark-root "${benchmark_root}" \
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
    2>&1 | tee "${LOG_ROOT}/llm_extract_seed${seed}_api.log"

  echo "[score:llm-extract:finalize] seed=${seed}"
  python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
    --finalize \
    --queue-name "${score_tag}_llm_extract" \
    --run-root "${run_root}" \
    --queue-root /home/shadeform/trace/benchmark/queues \
    --output-root "${output_root}" \
    --benchmark-root "${benchmark_root}" \
    "${MODEL_ARGS[@]}" \
    --benchmarks "${LLM_EXTRACT_BENCHMARKS[@]}" \
    --judge-model "${JUDGE_MODEL}" \
    2>&1 | tee "${LOG_ROOT}/llm_extract_seed${seed}_finalize.log"
}

run_score() {
  echo "[judge:start] model=${JUDGE_MODEL} served=${JUDGE_SERVED_MODEL_NAME}"
  echo "[judge] api_parallelism=${JUDGE_API_PARALLELISM} batch_size=${JUDGE_API_BATCH_SIZE} batches_per_endpoint=${JUDGE_API_BATCHES_PER_ENDPOINT} max_batch_chars=${JUDGE_API_MAX_BATCH_CHARS}"
  start_pool "${JUDGE_MODEL}" "${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_PORT_START}" "${LOG_ROOT}/vllm_${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_GPU_MEMORY_UTILIZATION}" "${JUDGE_MAX_MODEL_LEN}" "${JUDGE_MAX_NUM_SEQS}" "${JUDGE_MAX_NUM_BATCHED_TOKENS}"
  for seed in "${SEEDS[@]}"; do
    run_score_for_seed "${seed}"
  done
  stop_pool
  echo "[score:done] score_root_base=${SCORE_ROOT_BASE}"
}

run_summary_for_seed() {
  local seed="$1"
  local run_root="${RUN_ROOT_BASE}/seed_${seed}/runs"
  local benchmark_root="${SCORE_ROOT_BASE}/seed_${seed}/benchmark"
  local title="Qwen2.5-VL Selected25 Full Temp0.6 Seed ${seed} Answer-GRPO Benchmark Results"
  local markdown="${RESULTS_ROOT}/trace_selected25_full_temp06_seed${seed}_answer_3b7b_results.md"
  local excel="${RESULTS_ROOT}/trace_selected25_full_temp06_seed${seed}_answer_3b7b_results.xlsx"

  python /home/shadeform/trace/scripts/summarize_trace_candidate37_200_results.py \
    --benchmark-root "${benchmark_root}" \
    --run-root "${run_root}" \
    --suite-name "trace_selected25_full_temp06_seed${seed}_answer_3b7b" \
    --run-set trace_candidate37_200 \
    --subset-root "${SUBSET_ROOT}" \
    --subset-label "selected25 full; candidate benchmarks use trace_candidate24_full subset manifests; extra benchmarks use full VLMEvalKit datasets" \
    --title "${title}" \
    --markdown "${markdown}" \
    --excel "${excel}" \
    --models "${MODEL_SLUGS[@]}" \
    --only "${ALL_BENCHMARKS[@]}" \
    2>&1 | tee "${LOG_ROOT}/summarize_seed${seed}.log"
}

run_summary() {
  for seed in "${SEEDS[@]}"; do
    run_summary_for_seed "${seed}"
  done
}

echo "[suite] tag=${RUN_TAG}"
echo "[suite] run_root_base=${RUN_ROOT_BASE}"
echo "[suite] score_root_base=${SCORE_ROOT_BASE}"
echo "[suite] log_root=${LOG_ROOT}"
echo "[suite] results_root=${RESULTS_ROOT}"
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
