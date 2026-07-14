#!/usr/bin/env bash
set -euo pipefail

SUITE_TAG="${SUITE_TAG:-trace_ocr_screenspotv2_qwen25vl3b_3models_$(date -u +%Y%m%dT%H%M%SZ)}"
LOG_ROOT="${LOG_ROOT:-/home/shadeform/trace/logs/benchmark/${SUITE_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-/home/shadeform/trace/results}"
DATA_ROOT="${DATA_ROOT:-/home/shadeform/LMUData}"

PORT_START="${PORT_START:-18400}"
HOST="${HOST:-127.0.0.1}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-32768}"
MAX_TOKENS="${MAX_TOKENS:-4096}"
PARALLELISM_PER_ENDPOINT="${PARALLELISM_PER_ENDPOINT:-8}"
GENERATION_SEED="${GENERATION_SEED:-42}"
EVAL_NPROC="${EVAL_NPROC:-16}"
INSTALL_OCRBENCH_DEPS="${INSTALL_OCRBENCH_DEPS:-1}"

BENCHMARKS=(
  ocrbench_v2_mini
  screenspot_v2
)

MODEL_SLUGS=(
  qwen25vl3b-base
  trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500
  trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500
)

MODEL_PATHS=(
  Qwen/Qwen2.5-VL-3B-Instruct
  /dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500
  /dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500
)

mkdir -p "${LOG_ROOT}" "${RESULTS_ROOT}" "${DATA_ROOT}"

if [[ "${INSTALL_OCRBENCH_DEPS}" == "1" ]]; then
  python -m pip install -r /home/shadeform/trace/external/VLMEvalKit/vlmeval/dataset/utils/Ocrbench_v2/requirements.txt
  python - <<'PY'
import nltk

for package in ("wordnet", "omw-1.4"):
    nltk.download(package, quiet=True)
PY
fi

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

endpoint_args=()
for offset in "${!GPU_GROUP_ARRAY[@]}"; do
  endpoint_args+=(--api-base "http://${HOST}:$((PORT_START + offset))/v1")
done

model_args=()
for i in "${!MODEL_SLUGS[@]}"; do
  model_args+=(--model-entry "${MODEL_SLUGS[$i]}=${MODEL_PATHS[$i]}")
done

benchmark_args=(--only "${BENCHMARKS[@]}")

run_generation_for_decode() {
  local decode_name="$1"
  local run_root="$2"
  local temperature="$3"
  local top_p="$4"
  local top_k="$5"
  local presence_penalty="$6"
  local repetition_penalty="$7"
  local extra_seed_args=()
  if [[ "${temperature}" != "0" && "${temperature}" != "0.0" ]]; then
    extra_seed_args=(--seed "${GENERATION_SEED}")
  fi

  mkdir -p "${run_root}" "${LOG_ROOT}/${decode_name}"
  echo "[generation-suite:start] decode=${decode_name} run_root=${run_root}"
  echo "[generation-suite:config] endpoints=${#GPU_GROUP_ARRAY[@]} parallelism_per_endpoint=${PARALLELISM_PER_ENDPOINT} max_tokens=${MAX_TOKENS} temperature=${temperature} top_p=${top_p} top_k=${top_k}"

  for i in "${!MODEL_SLUGS[@]}"; do
    local slug="${MODEL_SLUGS[$i]}"
    local model="${MODEL_PATHS[$i]}"
    local pool_log_dir="${LOG_ROOT}/${decode_name}/vllm_${slug}"
    current_pid_file="${pool_log_dir}/pids.txt"

    echo "[model:start] decode=${decode_name} slug=${slug} model=${model}"
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

    LMUData="${DATA_ROOT}" python /home/shadeform/trace/scripts/run_external_benchmark_generation_api_queue.py \
      --model "${model}" \
      --model-slug "${slug}" \
      --api-model "${slug}" \
      "${endpoint_args[@]}" \
      --parallelism-per-endpoint "${PARALLELISM_PER_ENDPOINT}" \
      --run-set full \
      --run-root "${run_root}" \
      --exact-only \
      "${benchmark_args[@]}" \
      --temperature "${temperature}" \
      --top-p "${top_p}" \
      --top-k "${top_k}" \
      --presence-penalty "${presence_penalty}" \
      --repetition-penalty "${repetition_penalty}" \
      --max-tokens "${MAX_TOKENS}" \
      "${extra_seed_args[@]}" \
      2>&1 | tee "${LOG_ROOT}/${decode_name}/generation_${slug}.log"

    PID_FILE="${current_pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh
    current_pid_file=""
    echo "[model:done] decode=${decode_name} slug=${slug}"
  done
  echo "[generation-suite:done] decode=${decode_name}"
}

run_score_for_decode() {
  local decode_name="$1"
  local run_root="$2"
  local benchmark_root="$3"
  local queue_name="$4"

  mkdir -p "${benchmark_root}" "${LOG_ROOT}/${decode_name}"
  echo "[score-suite:start] decode=${decode_name} benchmark_root=${benchmark_root}"
  LMUData="${DATA_ROOT}" python /home/shadeform/trace/scripts/run_external_benchmark_score_multi_model_queue.py \
    "${model_args[@]}" \
    --queue-name "${queue_name}" \
    --run-set full \
    --run-root "${run_root}" \
    --benchmark-root "${benchmark_root}" \
    --exact-only \
    "${benchmark_args[@]}" \
    --eval-judge-model exact_matching \
    --eval-nproc "${EVAL_NPROC}" \
    2>&1 | tee "${LOG_ROOT}/${decode_name}/score.log"
  echo "[score-suite:done] decode=${decode_name}"
}

GREEDY_RUN_TAG="${SUITE_TAG}_greedy4096"
TEMP06_RUN_TAG="${SUITE_TAG}_temp06_4096"
GREEDY_RUN_ROOT="${GREEDY_RUN_ROOT:-/dev/shm/trace_rlvr/${GREEDY_RUN_TAG}/runs}"
TEMP06_RUN_ROOT="${TEMP06_RUN_ROOT:-/dev/shm/trace_rlvr/${TEMP06_RUN_TAG}/runs}"
GREEDY_BENCHMARK_ROOT="${GREEDY_BENCHMARK_ROOT:-/dev/shm/trace_rlvr/${GREEDY_RUN_TAG}_score/benchmark}"
TEMP06_BENCHMARK_ROOT="${TEMP06_BENCHMARK_ROOT:-/dev/shm/trace_rlvr/${TEMP06_RUN_TAG}_score/benchmark}"

echo "[suite] tag=${SUITE_TAG}"
echo "[suite] log_root=${LOG_ROOT}"
echo "[suite] data_root=${DATA_ROOT}"
echo "[suite] gpu_groups=${GPU_GROUPS}"

run_generation_for_decode "greedy" "${GREEDY_RUN_ROOT}" "0" "1" "-1" "0" "1"
run_score_for_decode "greedy" "${GREEDY_RUN_ROOT}" "${GREEDY_BENCHMARK_ROOT}" "${GREEDY_RUN_TAG}_score"

run_generation_for_decode "temp06" "${TEMP06_RUN_ROOT}" "0.6" "1.0" "-1" "0.0" "1.0"
run_score_for_decode "temp06" "${TEMP06_RUN_ROOT}" "${TEMP06_BENCHMARK_ROOT}" "${TEMP06_RUN_TAG}_score"

python /home/shadeform/trace/scripts/summarize_trace_grounding_greedy_temp06_results.py \
  --greedy-benchmark-root "${GREEDY_BENCHMARK_ROOT}" \
  --greedy-run-root "${GREEDY_RUN_ROOT}" \
  --temp06-benchmark-root "${TEMP06_BENCHMARK_ROOT}" \
  --temp06-run-root "${TEMP06_RUN_ROOT}" \
  --markdown "${RESULTS_ROOT}/trace_ocr_screenspotv2_qwen25vl3b_base_answer_annotation_greedy_temp06.md" \
  --excel "${RESULTS_ROOT}/trace_ocr_screenspotv2_qwen25vl3b_base_answer_annotation_greedy_temp06.xlsx" \
  --subset-root "${DATA_ROOT}" \
  --run-set full \
  --title "TRACE OCRBench-v2 MINI / ScreenSpot-v2 3B Base / Answer / Annotation Results" \
  --only "${BENCHMARKS[@]}" \
  2>&1 | tee "${LOG_ROOT}/summarize.log"

echo "[suite:done] greedy_run_root=${GREEDY_RUN_ROOT}"
echo "[suite:done] greedy_benchmark_root=${GREEDY_BENCHMARK_ROOT}"
echo "[suite:done] temp06_run_root=${TEMP06_RUN_ROOT}"
echo "[suite:done] temp06_benchmark_root=${TEMP06_BENCHMARK_ROOT}"
echo "[suite:done] results=${RESULTS_ROOT}/trace_ocr_screenspotv2_qwen25vl3b_base_answer_annotation_greedy_temp06.xlsx"
