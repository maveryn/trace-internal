#!/usr/bin/env bash
set -euo pipefail

SCORE_TAG="${SCORE_TAG:-trace_extra7_full_greedy4096_score_$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_ROOT="${RUN_ROOT:-/dev/shm/trace_rlvr/trace_extra7_full_greedy4096_latest/runs}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-/dev/shm/trace_rlvr/${SCORE_TAG}/benchmark}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/dev/shm/trace_rlvr/${SCORE_TAG}/llm_extracted}"
LOG_ROOT="${LOG_ROOT:-/home/shadeform/trace/logs/benchmark/${SCORE_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-/home/shadeform/trace/results}"
SUBSET_ROOT="${SUBSET_ROOT:-/home/shadeform/trace/benchmark/subsets/trace_extra7_full}"
PREVIOUS_SUBSET_ROOT="${PREVIOUS_SUBSET_ROOT:-/home/shadeform/trace/benchmark/subsets/trace_candidate37_200}"
SUBSET_TARGET_SIZE="${SUBSET_TARGET_SIZE:-1000000}"
SAMPLE_SEED="${SAMPLE_SEED:-42}"

JUDGE_MODEL="${JUDGE_MODEL:-Qwen/Qwen3-32B}"
JUDGE_SERVED_MODEL_NAME="${JUDGE_SERVED_MODEL_NAME:-qwen3-32b-judge}"
JUDGE_PORT_START="${JUDGE_PORT_START:-18100}"
HOST="${HOST:-127.0.0.1}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-128}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-32768}"
JUDGE_MAX_TOKENS="${JUDGE_MAX_TOKENS:-64}"
JUDGE_API_PARALLELISM="${JUDGE_API_PARALLELISM:-16}"
JUDGE_API_BATCH_SIZE="${JUDGE_API_BATCH_SIZE:-128}"
JUDGE_API_BATCHES_PER_ENDPOINT="${JUDGE_API_BATCHES_PER_ENDPOINT:-2}"
JUDGE_API_MAX_BATCH_CHARS="${JUDGE_API_MAX_BATCH_CHARS:-200000}"

BENCHMARKS=(
  spbench_si_cot
  visualpuzzles
  spatialvizbench_cot
  tablevqabench
  mmhelix
  omni3dbench
  countqa
)

MODEL_ARGS=(
  --model-entry qwen25vl3b-base=Qwen/Qwen2.5-VL-3B-Instruct
  --model-entry trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500=/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500
  --model-entry qwen25vl7b-base=Qwen/Qwen2.5-VL-7B-Instruct
  --model-entry trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500=/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500
)

OFFICIAL_DIRECT_BENCHMARKS=(
  tablevqabench
  mmhelix
  omni3dbench
)

LLM_EXTRACT_BENCHMARKS=(
  spbench_si_cot
  visualpuzzles
  spatialvizbench_cot
  countqa
)

mkdir -p "${LOG_ROOT}" "${BENCHMARK_ROOT}" "${OUTPUT_ROOT}"

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

echo "[score-suite] tag=${SCORE_TAG}"
echo "[score-suite] run_root=${RUN_ROOT}"
echo "[score-suite] benchmark_root=${BENCHMARK_ROOT}"
echo "[score-suite] output_root=${OUTPUT_ROOT}"
echo "[score-suite] log_root=${LOG_ROOT}"
echo "[score-suite] results_root=${RESULTS_ROOT}"
echo "[score-suite] subset_root=${SUBSET_ROOT}"

python /home/shadeform/trace/scripts/run_external_benchmark_score_multi_model_queue.py \
  "${MODEL_ARGS[@]}" \
  --queue-name "${SCORE_TAG}_official_direct" \
  --run-set trace_candidate37_200 \
  --run-root "${RUN_ROOT}" \
  --benchmark-root "${BENCHMARK_ROOT}" \
  --exact-only \
  --only "${OFFICIAL_DIRECT_BENCHMARKS[@]}" \
  2>&1 | tee "${LOG_ROOT}/score_official_direct.log"

if [[ "${GPU_GROUPS}" == *";"* ]]; then
  IFS=';' read -r -a JUDGE_GROUP_ARRAY <<< "${GPU_GROUPS}"
else
  read -r -a JUDGE_GROUP_ARRAY <<< "${GPU_GROUPS}"
fi

endpoint_args=()
for offset in "${!JUDGE_GROUP_ARRAY[@]}"; do
  endpoint_args+=(--api-base "http://${HOST}:$((JUDGE_PORT_START + offset))/v1")
done

pool_log_dir="${LOG_ROOT}/vllm_${JUDGE_SERVED_MODEL_NAME}"
current_pid_file="${pool_log_dir}/pids.txt"

echo "[score-suite] judge=${JUDGE_MODEL} served=${JUDGE_SERVED_MODEL_NAME}"
echo "[score-suite] judge_api_parallelism=${JUDGE_API_PARALLELISM}"
echo "[score-suite] judge_api_batch_size=${JUDGE_API_BATCH_SIZE} batches_per_endpoint=${JUDGE_API_BATCHES_PER_ENDPOINT} max_batch_chars=${JUDGE_API_MAX_BATCH_CHARS}"
MODEL_PATH="${JUDGE_MODEL}" \
SERVED_MODEL_NAME="${JUDGE_SERVED_MODEL_NAME}" \
HOST="${HOST}" \
PORT_START="${JUDGE_PORT_START}" \
GPU_GROUPS="${GPU_GROUPS}" \
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION}" \
MAX_MODEL_LEN="${MAX_MODEL_LEN}" \
MAX_NUM_SEQS="${MAX_NUM_SEQS}" \
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS}" \
LOG_DIR="${pool_log_dir}" \
PID_FILE="${current_pid_file}" \
  bash /home/shadeform/trace/scripts/start_vllm_endpoint_pool.sh

python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
  --prepare \
  --queue-name "${SCORE_TAG}_llm_extract" \
  --run-root "${RUN_ROOT}" \
  --queue-root /home/shadeform/trace/benchmark/queues \
  --output-root "${OUTPUT_ROOT}" \
  --benchmark-root "${BENCHMARK_ROOT}" \
  "${MODEL_ARGS[@]}" \
  --benchmarks "${LLM_EXTRACT_BENCHMARKS[@]}" \
  2>&1 | tee "${LOG_ROOT}/llm_extract_prepare.log"

python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
  --api-run \
  --queue-name "${SCORE_TAG}_llm_extract" \
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
  "${endpoint_args[@]}" \
  2>&1 | tee "${LOG_ROOT}/llm_extract_api.log"

python /home/shadeform/trace/scripts/run_llm_extracted_benchmark_score_queue.py \
  --finalize \
  --queue-name "${SCORE_TAG}_llm_extract" \
  --run-root "${RUN_ROOT}" \
  --queue-root /home/shadeform/trace/benchmark/queues \
  --output-root "${OUTPUT_ROOT}" \
  --benchmark-root "${BENCHMARK_ROOT}" \
  "${MODEL_ARGS[@]}" \
  --benchmarks "${LLM_EXTRACT_BENCHMARKS[@]}" \
  --judge-model "${JUDGE_MODEL}" \
  2>&1 | tee "${LOG_ROOT}/llm_extract_finalize.log"

python /home/shadeform/trace/scripts/summarize_trace_candidate37_200_results.py \
  --benchmark-root "${BENCHMARK_ROOT}" \
  --run-root "${RUN_ROOT}" \
  --suite-name trace_extra7_full_greedy4096 \
  --subset-root "${SUBSET_ROOT}" \
  --title "Qwen2.5-VL TRACE Extra7 Full Greedy-4096 Benchmark Results" \
  --markdown "${RESULTS_ROOT}/trace_extra7_full_greedy4096_results.md" \
  --excel "${RESULTS_ROOT}/trace_extra7_full_greedy4096_results.xlsx" \
  --models \
    qwen25vl3b-base \
    trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500 \
    qwen25vl7b-base \
    trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 \
  --only "${OFFICIAL_DIRECT_BENCHMARKS[@]}" "${LLM_EXTRACT_BENCHMARKS[@]}" \
  2>&1 | tee "${LOG_ROOT}/summarize.log"

PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh
current_pid_file=""

echo "[score-suite:done] benchmark_root=${BENCHMARK_ROOT}"
echo "[score-suite:done] output_root=${OUTPUT_ROOT}"
echo "[score-suite:done] markdown=${RESULTS_ROOT}/trace_extra7_full_greedy4096_results.md"
echo "[score-suite:done] excel=${RESULTS_ROOT}/trace_extra7_full_greedy4096_results.xlsx"
