#!/usr/bin/env bash
set -euo pipefail

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_TAG="${RUN_TAG:-trace_selected8_qwen25vl7b_annotation_temp06_4096_${RUN_STAMP}}"
SCORE_TAG="${SCORE_TAG:-${RUN_TAG}_score}"

BASE_TMP_ROOT="${BASE_TMP_ROOT:-/dev/shm/trace_rlvr}"
RUN_ROOT="${RUN_ROOT:-${BASE_TMP_ROOT}/${RUN_TAG}/runs}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-${BASE_TMP_ROOT}/${SCORE_TAG}/benchmark}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${BASE_TMP_ROOT}/${SCORE_TAG}/llm_extracted}"
LOG_ROOT="${LOG_ROOT:-/home/shadeform/trace/logs/benchmark/${RUN_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-/home/shadeform/trace/results}"

MODEL_SLUG="${MODEL_SLUG:-trace-qwen25vl7b-rlvr-ann-additive-0p50-sectioned-step500}"
MODEL_PATH="${MODEL_PATH:-/dev/shm/trace_rlvr/hf_models/trace-qwen25vl7b-rlvr-ann-additive-0p50-sectioned-step500}"

HOST="${HOST:-127.0.0.1}"
GEN_PORT_START="${GEN_PORT_START:-18000}"
JUDGE_PORT_START="${JUDGE_PORT_START:-18100}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"

GEN_GPU_MEMORY_UTILIZATION="${GEN_GPU_MEMORY_UTILIZATION:-0.90}"
GEN_MAX_MODEL_LEN="${GEN_MAX_MODEL_LEN:-32768}"
GEN_MAX_NUM_SEQS="${GEN_MAX_NUM_SEQS:-256}"
GEN_MAX_NUM_BATCHED_TOKENS="${GEN_MAX_NUM_BATCHED_TOKENS:-32768}"
CANDIDATE_PARALLELISM_PER_ENDPOINT="${CANDIDATE_PARALLELISM_PER_ENDPOINT:-4}"
EXTRA_PARALLELISM_PER_ENDPOINT="${EXTRA_PARALLELISM_PER_ENDPOINT:-8}"

TEMPERATURE="${TEMPERATURE:-0.6}"
TOP_P="${TOP_P:-1}"
TOP_K="${TOP_K:--1}"
PRESENCE_PENALTY="${PRESENCE_PENALTY:-0}"
REPETITION_PENALTY="${REPETITION_PENALTY:-1}"
MAX_TOKENS="${MAX_TOKENS:-4096}"
SEED="${SEED:-42}"

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

CANDIDATE_SUBSET_ROOT="${CANDIDATE_SUBSET_ROOT:-/home/shadeform/trace/benchmark/subsets/trace_candidate24_full}"

CANDIDATE_BENCHMARKS=(
  blink
  chartqapro
  game_qa_lite
  mathverse
  wemath
  vstarbench
  screenspot
)

EXTRA_BENCHMARKS=(
  countqa
)

OFFICIAL_DIRECT_BENCHMARKS=(
  screenspot
  mathverse
)

LLM_EXTRACT_BENCHMARKS=(
  blink
  chartqapro
  countqa
  game_qa_lite
  wemath
  vstarbench
)

ALL_BENCHMARKS=(
  blink
  chartqapro
  countqa
  game_qa_lite
  mathverse
  wemath
  vstarbench
  screenspot
)

mkdir -p "${RUN_ROOT}" "${BENCHMARK_ROOT}" "${OUTPUT_ROOT}" "${LOG_ROOT}" "${RESULTS_ROOT}"

current_pid_file=""
cleanup_current_pool() {
  if [[ -n "${current_pid_file}" && -f "${current_pid_file}" ]]; then
    PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh || true
  fi
}
trap cleanup_current_pool EXIT

if [[ "${GPU_GROUPS}" == *";"* ]]; then
  IFS=';' read -r -a GPU_GROUP_ARRAY <<< "${GPU_GROUPS}"
else
  read -r -a GPU_GROUP_ARRAY <<< "${GPU_GROUPS}"
fi

generation_endpoint_args=()
judge_endpoint_args=()
llm_endpoint_args=()
for offset in "${!GPU_GROUP_ARRAY[@]}"; do
  generation_endpoint_args+=(--api-base "http://${HOST}:$((GEN_PORT_START + offset))/v1")
  judge_endpoint_args+=(--judge-api-base "http://${HOST}:$((JUDGE_PORT_START + offset))/v1")
  llm_endpoint_args+=(--api-base "http://${HOST}:$((JUDGE_PORT_START + offset))/v1")
done

echo "[selected8] tag=${RUN_TAG}"
echo "[selected8] model=${MODEL_PATH}"
echo "[selected8] run_root=${RUN_ROOT}"
echo "[selected8] benchmark_root=${BENCHMARK_ROOT}"
echo "[selected8] output_root=${OUTPUT_ROOT}"
echo "[selected8] log_root=${LOG_ROOT}"
echo "[selected8] decoding temperature=${TEMPERATURE} top_p=${TOP_P} top_k=${TOP_K} max_tokens=${MAX_TOKENS} seed=${SEED}"
echo "[selected8] generation_endpoints=${#GPU_GROUP_ARRAY[@]} judge_endpoints=${#GPU_GROUP_ARRAY[@]}"

gen_log_dir="${LOG_ROOT}/vllm_${MODEL_SLUG}"
current_pid_file="${gen_log_dir}/pids.txt"
MODEL_PATH="${MODEL_PATH}" \
SERVED_MODEL_NAME="${MODEL_SLUG}" \
HOST="${HOST}" \
PORT_START="${GEN_PORT_START}" \
GPU_GROUPS="${GPU_GROUPS}" \
GPU_MEMORY_UTILIZATION="${GEN_GPU_MEMORY_UTILIZATION}" \
MAX_MODEL_LEN="${GEN_MAX_MODEL_LEN}" \
MAX_NUM_SEQS="${GEN_MAX_NUM_SEQS}" \
MAX_NUM_BATCHED_TOKENS="${GEN_MAX_NUM_BATCHED_TOKENS}" \
LOG_DIR="${gen_log_dir}" \
PID_FILE="${current_pid_file}" \
  bash /home/shadeform/trace/scripts/start_vllm_endpoint_pool.sh

python /home/shadeform/trace/scripts/run_external_benchmark_generation_api_queue.py \
  --model "${MODEL_PATH}" \
  --model-slug "${MODEL_SLUG}" \
  --api-model "${MODEL_SLUG}" \
  "${generation_endpoint_args[@]}" \
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
  --seed "${SEED}" \
  2>&1 | tee "${LOG_ROOT}/generation_candidate_selected7_${MODEL_SLUG}.log"

python /home/shadeform/trace/scripts/run_external_benchmark_generation_api_queue.py \
  --model "${MODEL_PATH}" \
  --model-slug "${MODEL_SLUG}" \
  --api-model "${MODEL_SLUG}" \
  "${generation_endpoint_args[@]}" \
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
  --seed "${SEED}" \
  2>&1 | tee "${LOG_ROOT}/generation_extra_selected1_${MODEL_SLUG}.log"

PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh
current_pid_file=""

judge_log_dir="${LOG_ROOT}/vllm_${JUDGE_SERVED_MODEL_NAME}"
current_pid_file="${judge_log_dir}/pids.txt"
MODEL_PATH="${JUDGE_MODEL}" \
SERVED_MODEL_NAME="${JUDGE_SERVED_MODEL_NAME}" \
HOST="${HOST}" \
PORT_START="${JUDGE_PORT_START}" \
GPU_GROUPS="${GPU_GROUPS}" \
GPU_MEMORY_UTILIZATION="${JUDGE_GPU_MEMORY_UTILIZATION}" \
MAX_MODEL_LEN="${JUDGE_MAX_MODEL_LEN}" \
MAX_NUM_SEQS="${JUDGE_MAX_NUM_SEQS}" \
MAX_NUM_BATCHED_TOKENS="${JUDGE_MAX_NUM_BATCHED_TOKENS}" \
LOG_DIR="${judge_log_dir}" \
PID_FILE="${current_pid_file}" \
  bash /home/shadeform/trace/scripts/start_vllm_endpoint_pool.sh

python /home/shadeform/trace/scripts/run_external_benchmark_score_multi_model_queue.py \
  --model-entry "${MODEL_SLUG}=${MODEL_PATH}" \
  --queue-name "${SCORE_TAG}_official_direct" \
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
  --queue-name "${SCORE_TAG}_llm_extract" \
  --run-root "${RUN_ROOT}" \
  --queue-root /home/shadeform/trace/benchmark/queues \
  --output-root "${OUTPUT_ROOT}" \
  --benchmark-root "${BENCHMARK_ROOT}" \
  --model-entry "${MODEL_SLUG}=${MODEL_PATH}" \
  --benchmarks "${LLM_EXTRACT_BENCHMARKS[@]}" \
  2>&1 | tee "${LOG_ROOT}/llm_extract_prepare.log"

python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
  --api-run \
  --queue-name "${SCORE_TAG}_llm_extract" \
  --run-root "${RUN_ROOT}" \
  --queue-root /home/shadeform/trace/benchmark/queues \
  --output-root "${OUTPUT_ROOT}" \
  --benchmark-root "${BENCHMARK_ROOT}" \
  --model-entry "${MODEL_SLUG}=${MODEL_PATH}" \
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
  --queue-name "${SCORE_TAG}_llm_extract" \
  --run-root "${RUN_ROOT}" \
  --queue-root /home/shadeform/trace/benchmark/queues \
  --output-root "${OUTPUT_ROOT}" \
  --benchmark-root "${BENCHMARK_ROOT}" \
  --model-entry "${MODEL_SLUG}=${MODEL_PATH}" \
  --benchmarks "${LLM_EXTRACT_BENCHMARKS[@]}" \
  --judge-model "${JUDGE_MODEL}" \
  2>&1 | tee "${LOG_ROOT}/llm_extract_finalize.log"

python /home/shadeform/trace/scripts/summarize_trace_candidate37_200_results.py \
  --benchmark-root "${BENCHMARK_ROOT}" \
  --run-root "${RUN_ROOT}" \
  --suite-name "trace_selected8_qwen25vl7b_annotation_temp06_4096" \
  --subset-label "trace_candidate24_full selected + full countqa" \
  --title "Qwen2.5-VL-7B TRACE Annotation Additive 0.50 Step500 Selected8 Temp0.6 Results" \
  --markdown "${RESULTS_ROOT}/trace_selected8_qwen25vl7b_annotation_temp06_4096_results.md" \
  --excel "${RESULTS_ROOT}/trace_selected8_qwen25vl7b_annotation_temp06_4096_results.xlsx" \
  --models "${MODEL_SLUG}" \
  --only "${ALL_BENCHMARKS[@]}" \
  2>&1 | tee "${LOG_ROOT}/summarize.log"

PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh
current_pid_file=""

echo "[selected8:done] run_root=${RUN_ROOT}"
echo "[selected8:done] benchmark_root=${BENCHMARK_ROOT}"
echo "[selected8:done] output_root=${OUTPUT_ROOT}"
echo "[selected8:done] markdown=${RESULTS_ROOT}/trace_selected8_qwen25vl7b_annotation_temp06_4096_results.md"
echo "[selected8:done] excel=${RESULTS_ROOT}/trace_selected8_qwen25vl7b_annotation_temp06_4096_results.xlsx"
