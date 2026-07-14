#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"

MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-7B-Instruct}"
MODEL_SLUG="${MODEL_SLUG:-qwen25vl7b-base}"

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_TAG="${RUN_TAG:-trace_video4_temp06_seed42_${MODEL_SLUG}_${RUN_STAMP}}"
TMP_ROOT="${TMP_ROOT:-/dev/shm/trace_rlvr}"
RUN_ROOT="${RUN_ROOT:-${TMP_ROOT}/${RUN_TAG}/runs}"
SCORE_ROOT="${SCORE_ROOT:-${TMP_ROOT}/${RUN_TAG}_score}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-${SCORE_ROOT}/benchmark}"
LOG_ROOT="${LOG_ROOT:-${REPO_ROOT}/logs/benchmark/${RUN_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-${REPO_ROOT}/results}"
LATEST_LINK="${LATEST_LINK:-${TMP_ROOT}/trace_video4_temp06_seed42_${MODEL_SLUG}_latest}"

HOST="${HOST:-127.0.0.1}"
GEN_PORT_START="${GEN_PORT_START:-18200}"
JUDGE_PORT_START="${JUDGE_PORT_START:-18300}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"

GEN_GPU_MEMORY_UTILIZATION="${GEN_GPU_MEMORY_UTILIZATION:-0.85}"
GEN_MAX_MODEL_LEN="${GEN_MAX_MODEL_LEN:-32768}"
GEN_MAX_NUM_SEQS="${GEN_MAX_NUM_SEQS:-128}"
GEN_MAX_NUM_BATCHED_TOKENS="${GEN_MAX_NUM_BATCHED_TOKENS:-32768}"
GEN_MAX_IMAGES="${GEN_MAX_IMAGES:-16}"
GEN_MAX_VIDEOS="${GEN_MAX_VIDEOS:-0}"
GEN_MAX_TOKENS="${GEN_MAX_TOKENS:-4096}"
GEN_TEMPERATURE="${GEN_TEMPERATURE:-0.6}"
GEN_TOP_P="${GEN_TOP_P:-1.0}"
GEN_TOP_K="${GEN_TOP_K:--1}"
GEN_PRESENCE_PENALTY="${GEN_PRESENCE_PENALTY:-0.0}"
GEN_REPETITION_PENALTY="${GEN_REPETITION_PENALTY:-1.0}"
GENERATION_SEED="${GENERATION_SEED:-42}"
GEN_PARALLELISM_PER_ENDPOINT="${GEN_PARALLELISM_PER_ENDPOINT:-16}"

JUDGE_MODEL="${JUDGE_MODEL:-Qwen/Qwen3-32B}"
JUDGE_SERVED_MODEL_NAME="${JUDGE_SERVED_MODEL_NAME:-qwen3-32b-judge}"
JUDGE_GPU_MEMORY_UTILIZATION="${JUDGE_GPU_MEMORY_UTILIZATION:-0.90}"
JUDGE_MAX_MODEL_LEN="${JUDGE_MAX_MODEL_LEN:-8192}"
JUDGE_MAX_NUM_SEQS="${JUDGE_MAX_NUM_SEQS:-128}"
JUDGE_MAX_NUM_BATCHED_TOKENS="${JUDGE_MAX_NUM_BATCHED_TOKENS:-32768}"
JUDGE_MAX_TOKENS="${JUDGE_MAX_TOKENS:-128}"
JUDGE_API_PARALLELISM="${JUDGE_API_PARALLELISM:-16}"
EVAL_NPROC="${EVAL_NPROC:-16}"

RUN_GENERATION="${RUN_GENERATION:-1}"
RUN_SCORE="${RUN_SCORE:-1}"
RUN_SUMMARY="${RUN_SUMMARY:-1}"
LIMIT="${LIMIT:-}"
NO_RESUME="${NO_RESUME:-0}"

VIDEO_BENCHMARKS=(
  qbench_video
  videommmu
  video_tt
  tempcompass
)

mkdir -p "${RUN_ROOT}" "${BENCHMARK_ROOT}" "${LOG_ROOT}" "${RESULTS_ROOT}" "${TMP_ROOT}/lmudata"

export LMUData="${LMUData:-${TMP_ROOT}/lmudata}"
export HF_HOME="${HF_HOME:-${TMP_ROOT}/cache/huggingface_home}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-${TMP_ROOT}/cache/huggingface/hub}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HUB_CACHE}}"
mkdir -p "${HF_HOME}" "${HF_HUB_CACHE}"

if [[ -z "${HF_TOKEN:-}" && -f "${REPO_ROOT}/hf-token.txt" ]]; then
  export HF_TOKEN
  HF_TOKEN="$(tr -d '[:space:]' < "${REPO_ROOT}/hf-token.txt")"
fi
if [[ -n "${HF_TOKEN:-}" ]]; then
  export HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-${HF_TOKEN}}"
  export HUGGINGFACE_HUB_TOKEN="${HUGGINGFACE_HUB_TOKEN:-${HF_TOKEN}}"
fi

MODEL_ARGS=(--model-entry "${MODEL_SLUG}=${MODEL_PATH}")
LIMIT_ARGS=()
if [[ -n "${LIMIT}" ]]; then
  LIMIT_ARGS=(--limit "${LIMIT}" --sample-seed "${GENERATION_SEED}")
fi
NO_RESUME_ARGS=()
if [[ "${NO_RESUME}" == "1" ]]; then
  NO_RESUME_ARGS=(--no-resume)
fi

current_pid_file=""
cleanup_current_pool() {
  if [[ -n "${current_pid_file}" && -f "${current_pid_file}" ]]; then
    PID_FILE="${current_pid_file}" bash "${REPO_ROOT}/scripts/stop_vllm_endpoint_pool.sh" || true
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

start_pool() {
  local model="$1"
  local served_name="$2"
  local port_start="$3"
  local log_dir="$4"
  local gpu_mem="$5"
  local max_model_len="$6"
  local max_num_seqs="$7"
  local max_num_batched_tokens="$8"
  local max_images="$9"
  local max_videos="${10}"

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
  MAX_IMAGES="${max_images}" \
  MAX_VIDEOS="${max_videos}" \
  LOG_DIR="${log_dir}" \
  PID_FILE="${current_pid_file}" \
    bash "${REPO_ROOT}/scripts/start_vllm_endpoint_pool.sh"
}

stop_pool() {
  if [[ -n "${current_pid_file}" && -f "${current_pid_file}" ]]; then
    PID_FILE="${current_pid_file}" bash "${REPO_ROOT}/scripts/stop_vllm_endpoint_pool.sh"
  fi
  current_pid_file=""
}

run_generation() {
  local -a api_args
  build_endpoint_args "${GEN_PORT_START}" "--api-base" api_args

  echo "[generation:start] model_slug=${MODEL_SLUG} model=${MODEL_PATH}"
  echo "[generation] run_root=${RUN_ROOT}"
  echo "[generation] benchmarks=${VIDEO_BENCHMARKS[*]}"
  echo "[generation] decoding temperature=${GEN_TEMPERATURE} top_p=${GEN_TOP_P} top_k=${GEN_TOP_K} presence_penalty=${GEN_PRESENCE_PENALTY} repetition_penalty=${GEN_REPETITION_PENALTY} max_tokens=${GEN_MAX_TOKENS} seed=${GENERATION_SEED}"
  echo "[generation] gpu_groups=${GPU_GROUPS} parallelism_per_endpoint=${GEN_PARALLELISM_PER_ENDPOINT} max_images=${GEN_MAX_IMAGES}"
  echo "[generation] LMUData=${LMUData} HF_HUB_CACHE=${HF_HUB_CACHE}"

  start_pool "${MODEL_PATH}" "${MODEL_SLUG}" "${GEN_PORT_START}" "${LOG_ROOT}/vllm_generation_${MODEL_SLUG}" "${GEN_GPU_MEMORY_UTILIZATION}" "${GEN_MAX_MODEL_LEN}" "${GEN_MAX_NUM_SEQS}" "${GEN_MAX_NUM_BATCHED_TOKENS}" "${GEN_MAX_IMAGES}" "${GEN_MAX_VIDEOS}"

  python "${REPO_ROOT}/scripts/run_external_benchmark_generation_api_queue.py" \
    --model "${MODEL_PATH}" \
    --model-slug "${MODEL_SLUG}" \
    --api-model "${MODEL_SLUG}" \
    "${api_args[@]}" \
    --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
    --run-set trace_video4 \
    --run-root "${RUN_ROOT}" \
    --exact-only \
    --only "${VIDEO_BENCHMARKS[@]}" \
    --temperature "${GEN_TEMPERATURE}" \
    --top-p "${GEN_TOP_P}" \
    --top-k "${GEN_TOP_K}" \
    --presence-penalty "${GEN_PRESENCE_PENALTY}" \
    --repetition-penalty "${GEN_REPETITION_PENALTY}" \
    --max-tokens "${GEN_MAX_TOKENS}" \
    --seed "${GENERATION_SEED}" \
    "${LIMIT_ARGS[@]}" \
    "${NO_RESUME_ARGS[@]}" \
    2>&1 | tee "${LOG_ROOT}/generation_${MODEL_SLUG}.log"

  stop_pool
  ln -sfn "$(dirname "${RUN_ROOT}")" "${LATEST_LINK}"
  echo "[generation:done] run_root=${RUN_ROOT}"
}

run_score() {
  local -a judge_endpoint_args
  build_endpoint_args "${JUDGE_PORT_START}" "--judge-api-base" judge_endpoint_args

  echo "[score:start] model_slug=${MODEL_SLUG}"
  echo "[score] benchmark_root=${BENCHMARK_ROOT}"
  echo "[score] judge_pool=${JUDGE_MODEL} served=${JUDGE_SERVED_MODEL_NAME}"

  start_pool "${JUDGE_MODEL}" "${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_PORT_START}" "${LOG_ROOT}/vllm_${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_GPU_MEMORY_UTILIZATION}" "${JUDGE_MAX_MODEL_LEN}" "${JUDGE_MAX_NUM_SEQS}" "${JUDGE_MAX_NUM_BATCHED_TOKENS}" 0 0

  # Stock VLMEvalKit video scorers that build a judge read these OpenAI-compatible env vars.
  OPENAI_API_BASE="http://${HOST}:${JUDGE_PORT_START}/v1/chat/completions" \
  OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}" \
  LOCAL_LLM="${JUDGE_SERVED_MODEL_NAME}" \
  python "${REPO_ROOT}/scripts/run_external_benchmark_score_multi_model_queue.py" \
    "${MODEL_ARGS[@]}" \
    --queue-name "${RUN_TAG}_official_direct" \
    --run-set trace_video4 \
    --run-root "${RUN_ROOT}" \
    --benchmark-root "${BENCHMARK_ROOT}" \
    --exact-only \
    --only "${VIDEO_BENCHMARKS[@]}" \
    --eval-judge-model "${JUDGE_SERVED_MODEL_NAME}" \
    --eval-nproc "${EVAL_NPROC}" \
    --judge-model "${JUDGE_MODEL}" \
    --judge-max-tokens "${JUDGE_MAX_TOKENS}" \
    --judge-api-model "${JUDGE_SERVED_MODEL_NAME}" \
    --judge-api-tokenizer-model "${JUDGE_MODEL}" \
    --judge-api-parallelism "${JUDGE_API_PARALLELISM}" \
    "${judge_endpoint_args[@]}" \
    "${NO_RESUME_ARGS[@]}" \
    2>&1 | tee "${LOG_ROOT}/score_official_direct.log"

  stop_pool
  echo "[score:done] benchmark_root=${BENCHMARK_ROOT}"
}

run_summary() {
  local markdown="${RESULTS_ROOT}/${RUN_TAG}_results.md"
  local excel="${RESULTS_ROOT}/${RUN_TAG}_results.xlsx"

  python "${REPO_ROOT}/scripts/summarize_trace_candidate37_200_results.py" \
    --benchmark-root "${BENCHMARK_ROOT}" \
    --run-root "${RUN_ROOT}" \
    --suite-name "trace_video4_temp06_seed42" \
    --run-set trace_video4 \
    --subset-label "full VLMEvalKit video4 eval; frame-based aliases with TRACE temp0.6 seed42 decoding" \
    --title "TRACE Video4 Temp0.6 Seed42 Benchmark Results: ${MODEL_SLUG}" \
    --markdown "${markdown}" \
    --excel "${excel}" \
    --models "${MODEL_SLUG}" \
    --only "${VIDEO_BENCHMARKS[@]}" \
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
