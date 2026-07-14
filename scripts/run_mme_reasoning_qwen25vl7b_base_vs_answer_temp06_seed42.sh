#!/usr/bin/env bash
set -euo pipefail

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_TAG="${RUN_TAG:-trace_mme_reasoning_temp06_seed42_qwen25vl7b_base_vs_answer_${RUN_STAMP}}"
TMP_ROOT="${TMP_ROOT:-/dev/shm/trace_rlvr}"
RUN_ROOT="${RUN_ROOT:-${TMP_ROOT}/${RUN_TAG}/runs}"
SCORE_ROOT="${SCORE_ROOT:-${TMP_ROOT}/${RUN_TAG}_score}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-${SCORE_ROOT}/benchmark}"
RESULTS_ROOT="${RESULTS_ROOT:-/home/shadeform/trace/results/${RUN_TAG}}"
LOG_ROOT="${LOG_ROOT:-/home/shadeform/trace/logs/benchmark/${RUN_TAG}}"
LMU_DATA_ROOT="${LMU_DATA_ROOT:-${TMP_ROOT}/lmudata}"

BASE_MODEL_PATH="${BASE_MODEL_PATH:-Qwen/Qwen2.5-VL-7B-Instruct}"
BASE_MODEL_SLUG="${BASE_MODEL_SLUG:-qwen25vl7b-base}"
ANSWER_MODEL_PATH="${ANSWER_MODEL_PATH:-/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500}"
ANSWER_MODEL_SLUG="${ANSWER_MODEL_SLUG:-trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500}"

HOST="${HOST:-127.0.0.1}"
BASE_PORT_START="${BASE_PORT_START:-18000}"
ANSWER_PORT_START="${ANSWER_PORT_START:-18004}"
JUDGE_PORT_START="${JUDGE_PORT_START:-18100}"
BASE_GPU_GROUPS="${BASE_GPU_GROUPS:-0 1 2 3}"
ANSWER_GPU_GROUPS="${ANSWER_GPU_GROUPS:-4 5 6 7}"
JUDGE_GPU_GROUPS="${JUDGE_GPU_GROUPS:-0 1 2 3 4 5 6 7}"

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
JUDGE_API_PARALLELISM="${JUDGE_API_PARALLELISM:-128}"

mkdir -p "${RUN_ROOT}" "${BENCHMARK_ROOT}" "${RESULTS_ROOT}" "${LOG_ROOT}" "${LMU_DATA_ROOT}"

if [[ -z "${HF_TOKEN:-}" && -f /home/shadeform/trace/hf-token.txt ]]; then
  export HF_TOKEN
  HF_TOKEN="$(tr -d '\n\r' < /home/shadeform/trace/hf-token.txt)"
fi
export LMUData="${LMU_DATA_ROOT}"

PID_FILES=()
cleanup_pools() {
  for pid_file in "${PID_FILES[@]:-}"; do
    if [[ -f "${pid_file}" ]]; then
      PID_FILE="${pid_file}" bash /home/shadeform/trace/scripts/stop_vllm_endpoint_pool.sh || true
    fi
  done
}
trap cleanup_pools EXIT

endpoint_args() {
  local port_start="$1"
  local groups="$2"
  local flag="$3"
  local -n out="$4"
  out=()
  local group_array=()
  if [[ "${groups}" == *";"* ]]; then
    IFS=';' read -r -a group_array <<< "${groups}"
  else
    read -r -a group_array <<< "${groups}"
  fi
  for offset in "${!group_array[@]}"; do
    out+=("${flag}" "http://${HOST}:$((port_start + offset))/v1")
  done
}

start_pool() {
  local model_path="$1"
  local served_name="$2"
  local port_start="$3"
  local gpu_groups="$4"
  local log_dir="$5"
  local gpu_mem="$6"
  local max_model_len="$7"
  local max_num_seqs="$8"
  local max_num_batched_tokens="$9"

  local pid_file="${log_dir}/pids.txt"
  PID_FILES+=("${pid_file}")
  MODEL_PATH="${model_path}" \
  SERVED_MODEL_NAME="${served_name}" \
  HOST="${HOST}" \
  PORT_START="${port_start}" \
  GPU_GROUPS="${gpu_groups}" \
  GPU_MEMORY_UTILIZATION="${gpu_mem}" \
  MAX_MODEL_LEN="${max_model_len}" \
  MAX_NUM_SEQS="${max_num_seqs}" \
  MAX_NUM_BATCHED_TOKENS="${max_num_batched_tokens}" \
  LOG_DIR="${log_dir}" \
  PID_FILE="${pid_file}" \
    bash /home/shadeform/trace/scripts/start_vllm_endpoint_pool.sh
}

stop_all_pools() {
  cleanup_pools
  PID_FILES=()
}

run_generation_for_model() {
  local model_path="$1"
  local model_slug="$2"
  shift 2
  local -a api_args=("$@")
  python /home/shadeform/trace/scripts/run_mme_reasoning_eval.py generate \
    --model "${model_path}" \
    --model-slug "${model_slug}" \
    --api-model "${model_slug}" \
    "${api_args[@]}" \
    --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
    --run-root "${RUN_ROOT}" \
    --temperature "${GEN_TEMPERATURE}" \
    --top-p "${GEN_TOP_P}" \
    --top-k "${GEN_TOP_K}" \
    --presence-penalty "${GEN_PRESENCE_PENALTY}" \
    --repetition-penalty "${GEN_REPETITION_PENALTY}" \
    --max-tokens "${GEN_MAX_TOKENS}" \
    --seed "${GENERATION_SEED}"
}

run_score_for_model() {
  local model_path="$1"
  local model_slug="$2"
  shift 2
  local -a judge_args=("$@")
  python /home/shadeform/trace/scripts/run_mme_reasoning_eval.py score \
    --model "${model_path}" \
    --model-slug "${model_slug}" \
    --run-root "${RUN_ROOT}" \
    --benchmark-root "${BENCHMARK_ROOT}" \
    --judge-model "${JUDGE_MODEL}" \
    --judge-api-model "${JUDGE_SERVED_MODEL_NAME}" \
    --judge-api-tokenizer-model "${JUDGE_MODEL}" \
    --judge-api-parallelism "${JUDGE_API_PARALLELISM}" \
    "${judge_args[@]}"
}

if [[ "${ANSWER_MODEL_PATH}" == /* && ! -d "${ANSWER_MODEL_PATH}" ]]; then
  echo "[error] missing answer model path: ${ANSWER_MODEL_PATH}" >&2
  exit 1
fi

echo "[suite] tag=${RUN_TAG}"
echo "[suite] run_root=${RUN_ROOT}"
echo "[suite] benchmark_root=${BENCHMARK_ROOT}"
echo "[suite] results_root=${RESULTS_ROOT}"
echo "[suite] decoding temp=${GEN_TEMPERATURE} top_p=${GEN_TOP_P} top_k=${GEN_TOP_K} max_tokens=${GEN_MAX_TOKENS} seed=${GENERATION_SEED}"

base_api_args=()
answer_api_args=()
endpoint_args "${BASE_PORT_START}" "${BASE_GPU_GROUPS}" "--api-base" base_api_args
endpoint_args "${ANSWER_PORT_START}" "${ANSWER_GPU_GROUPS}" "--api-base" answer_api_args

echo "[generation:start] base_gpus=${BASE_GPU_GROUPS} answer_gpus=${ANSWER_GPU_GROUPS}"
start_pool "${BASE_MODEL_PATH}" "${BASE_MODEL_SLUG}" "${BASE_PORT_START}" "${BASE_GPU_GROUPS}" "${LOG_ROOT}/vllm_generation_${BASE_MODEL_SLUG}" "${GEN_GPU_MEMORY_UTILIZATION}" "${GEN_MAX_MODEL_LEN}" "${GEN_MAX_NUM_SEQS}" "${GEN_MAX_NUM_BATCHED_TOKENS}"
start_pool "${ANSWER_MODEL_PATH}" "${ANSWER_MODEL_SLUG}" "${ANSWER_PORT_START}" "${ANSWER_GPU_GROUPS}" "${LOG_ROOT}/vllm_generation_${ANSWER_MODEL_SLUG}" "${GEN_GPU_MEMORY_UTILIZATION}" "${GEN_MAX_MODEL_LEN}" "${GEN_MAX_NUM_SEQS}" "${GEN_MAX_NUM_BATCHED_TOKENS}"

run_generation_for_model "${BASE_MODEL_PATH}" "${BASE_MODEL_SLUG}" "${base_api_args[@]}" 2>&1 | tee "${LOG_ROOT}/generation_${BASE_MODEL_SLUG}.log" &
base_gen_pid=$!
run_generation_for_model "${ANSWER_MODEL_PATH}" "${ANSWER_MODEL_SLUG}" "${answer_api_args[@]}" 2>&1 | tee "${LOG_ROOT}/generation_${ANSWER_MODEL_SLUG}.log" &
answer_gen_pid=$!
wait "${base_gen_pid}"
wait "${answer_gen_pid}"
stop_all_pools
echo "[generation:done]"

judge_api_args=()
endpoint_args "${JUDGE_PORT_START}" "${JUDGE_GPU_GROUPS}" "--judge-api-base" judge_api_args
echo "[score:start] judge_gpus=${JUDGE_GPU_GROUPS}"
start_pool "${JUDGE_MODEL}" "${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_PORT_START}" "${JUDGE_GPU_GROUPS}" "${LOG_ROOT}/vllm_${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_GPU_MEMORY_UTILIZATION}" "${JUDGE_MAX_MODEL_LEN}" "${JUDGE_MAX_NUM_SEQS}" "${JUDGE_MAX_NUM_BATCHED_TOKENS}"

run_score_for_model "${BASE_MODEL_PATH}" "${BASE_MODEL_SLUG}" "${judge_api_args[@]}" 2>&1 | tee "${LOG_ROOT}/score_${BASE_MODEL_SLUG}.log" &
base_score_pid=$!
run_score_for_model "${ANSWER_MODEL_PATH}" "${ANSWER_MODEL_SLUG}" "${judge_api_args[@]}" 2>&1 | tee "${LOG_ROOT}/score_${ANSWER_MODEL_SLUG}.log" &
answer_score_pid=$!
wait "${base_score_pid}"
wait "${answer_score_pid}"
stop_all_pools
echo "[score:done]"

python /home/shadeform/trace/scripts/run_mme_reasoning_eval.py summary \
  --benchmark-root "${BENCHMARK_ROOT}" \
  --output-dir "${RESULTS_ROOT}" \
  --model-slug "${BASE_MODEL_SLUG}" \
  --model-slug "${ANSWER_MODEL_SLUG}" \
  2>&1 | tee "${LOG_ROOT}/summary.log"

echo "[suite:done] results=${RESULTS_ROOT}"
