#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"

MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-7B-Instruct}"
MODEL_SLUG="${MODEL_SLUG:-qwen25vl7b-base}"

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_TAG="${RUN_TAG:-trace_video4_temp06_seed42_${MODEL_SLUG}_${RUN_STAMP}}"
RUN_ATTEMPT_ID="${RUN_ATTEMPT_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
TMP_ROOT="${TMP_ROOT:-/dev/shm/trace_rlvr}"
RUN_ROOT="${RUN_ROOT:-${TMP_ROOT}/${RUN_TAG}/runs}"
SCORE_ROOT="${SCORE_ROOT:-${TMP_ROOT}/${RUN_TAG}_score}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-${SCORE_ROOT}/benchmark}"
LOG_ROOT="${LOG_ROOT:-${REPO_ROOT}/logs/benchmark/${RUN_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-${REPO_ROOT}/results}"
LATEST_LINK="${LATEST_LINK:-${TMP_ROOT}/trace_video4_temp06_seed42_${MODEL_SLUG}_latest}"
PERSIST_RUN_ROOT="${PERSIST_RUN_ROOT:-${RESULTS_ROOT}/benchmark-runs/${RUN_TAG}/runs}"
PERSIST_SCORE_ROOT="${PERSIST_SCORE_ROOT:-${RESULTS_ROOT}/benchmark-runs/${RUN_TAG}/score}"

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
GEN_MAX_IMAGE_PIXELS="${GEN_MAX_IMAGE_PIXELS:-1000000}"
GEN_MAX_IMAGE_SIDE="${GEN_MAX_IMAGE_SIDE:-1280}"
GEN_IMAGE_JPEG_QUALITY="${GEN_IMAGE_JPEG_QUALITY:-85}"
GEN_MAX_TOKENS="${GEN_MAX_TOKENS:-4096}"
GEN_TEMPERATURE="${GEN_TEMPERATURE:-0.6}"
GEN_TOP_P="${GEN_TOP_P:-1.0}"
GEN_TOP_K="${GEN_TOP_K:--1}"
GEN_PRESENCE_PENALTY="${GEN_PRESENCE_PENALTY:-0.0}"
GEN_REPETITION_PENALTY="${GEN_REPETITION_PENALTY:-1.0}"
GENERATION_SEED="${GENERATION_SEED:-42}"
GEN_PARALLELISM_PER_ENDPOINT="${GEN_PARALLELISM_PER_ENDPOINT:-16}"
GEN_ENDPOINT_FAILURE_THRESHOLD="${GEN_ENDPOINT_FAILURE_THRESHOLD:-2}"

VLLM_CPU_THREADS_PER_PROCESS="${VLLM_CPU_THREADS_PER_PROCESS:-8}"
VLLM_CPU_AFFINITY_GROUPS="${VLLM_CPU_AFFINITY_GROUPS:-auto}"

JUDGE_MODEL="${JUDGE_MODEL:-Qwen/Qwen3-32B}"
JUDGE_SERVED_MODEL_NAME="${JUDGE_SERVED_MODEL_NAME:-qwen3-32b-judge}"
JUDGE_GPU_MEMORY_UTILIZATION="${JUDGE_GPU_MEMORY_UTILIZATION:-0.90}"
JUDGE_MAX_MODEL_LEN="${JUDGE_MAX_MODEL_LEN:-8192}"
JUDGE_MAX_NUM_SEQS="${JUDGE_MAX_NUM_SEQS:-128}"
JUDGE_MAX_NUM_BATCHED_TOKENS="${JUDGE_MAX_NUM_BATCHED_TOKENS:-32768}"
JUDGE_MAX_TOKENS="${JUDGE_MAX_TOKENS:-128}"
JUDGE_API_PARALLELISM="${JUDGE_API_PARALLELISM:-16}"
EVAL_NPROC="${EVAL_NPROC:-16}"
SCORE_WORKERS="${SCORE_WORKERS:-auto}"
JUDGE_REASONING_PARSER="${JUDGE_REASONING_PARSER-qwen3}"
JUDGE_CHAT_TEMPLATE="${JUDGE_CHAT_TEMPLATE-${REPO_ROOT}/rlvr/examples/prompts/chat_template_no_think.jinja}"

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

mkdir -p "${RUN_ROOT}" "${PERSIST_RUN_ROOT}" "${BENCHMARK_ROOT}" "${PERSIST_SCORE_ROOT}" "${LOG_ROOT}" "${RESULTS_ROOT}" "${TMP_ROOT}/lmudata"

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

restore_persistent_artifacts() {
  if [[ "${NO_RESUME}" != "1" && -d "${PERSIST_RUN_ROOT}" ]]; then
    rsync -a "${PERSIST_RUN_ROOT}/" "${RUN_ROOT}/"
  fi
  if [[ "${NO_RESUME}" != "1" && -d "${PERSIST_SCORE_ROOT}" ]]; then
    rsync -a "${PERSIST_SCORE_ROOT}/" "${SCORE_ROOT}/"
  fi
}

persist_run_artifacts() {
  if [[ -d "${RUN_ROOT}" ]]; then
    mkdir -p "${PERSIST_RUN_ROOT}"
    rsync -a --delete "${RUN_ROOT}/" "${PERSIST_RUN_ROOT}/"
  fi
  if [[ -d "${SCORE_ROOT}" ]]; then
    mkdir -p "${PERSIST_SCORE_ROOT}"
    rsync -a --delete "${SCORE_ROOT}/" "${PERSIST_SCORE_ROOT}/"
  fi
}

cleanup_and_persist() {
  local status=$?
  set +e
  cleanup_current_pool
  persist_run_artifacts
  return "${status}"
}
trap cleanup_and_persist EXIT

split_gpu_groups() {
  if [[ "${GPU_GROUPS}" == *";"* ]]; then
    IFS=';' read -r -a GROUP_ARRAY <<< "${GPU_GROUPS}"
  else
    read -r -a GROUP_ARRAY <<< "${GPU_GROUPS}"
  fi
}

derive_cpu_affinity_groups() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    return 0
  fi
  local gpu_count cpu_count cpus_per_gpu
  gpu_count="$(nvidia-smi -L 2>/dev/null | wc -l)"
  cpu_count="$(nproc)"
  if [[ "${gpu_count}" -le 0 || $((cpu_count % gpu_count)) -ne 0 ]]; then
    return 0
  fi
  cpus_per_gpu=$((cpu_count / gpu_count))
  split_gpu_groups
  local -a affinity_groups=()
  local group id start end joined
  for group in "${GROUP_ARRAY[@]}"; do
    joined=""
    IFS=',' read -r -a gpu_ids <<< "${group}"
    for id in "${gpu_ids[@]}"; do
      if [[ ! "${id}" =~ ^[0-9]+$ || "${id}" -ge "${gpu_count}" ]]; then
        return 0
      fi
      start=$((id * cpus_per_gpu))
      end=$((start + cpus_per_gpu - 1))
      joined+="${joined:+,}${start}-${end}"
    done
    affinity_groups+=("${joined}")
  done
  local IFS=';'
  echo "${affinity_groups[*]}"
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
  local reasoning_parser="${11:-}"
  local chat_template="${12:-}"
  local cpu_affinity="${VLLM_CPU_AFFINITY_GROUPS}"
  if [[ "${cpu_affinity}" == "auto" ]]; then
    cpu_affinity="$(derive_cpu_affinity_groups)"
  elif [[ "${cpu_affinity}" == "none" ]]; then
    cpu_affinity=""
  fi

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
  CPU_THREADS_PER_PROCESS="${VLLM_CPU_THREADS_PER_PROCESS}" \
  CPU_AFFINITY_GROUPS="${cpu_affinity}" \
  REASONING_PARSER="${reasoning_parser}" \
  CHAT_TEMPLATE="${chat_template}" \
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
  echo "[generation] gpu_groups=${GPU_GROUPS} parallelism_per_endpoint=${GEN_PARALLELISM_PER_ENDPOINT} max_images=${GEN_MAX_IMAGES} max_image_pixels=${GEN_MAX_IMAGE_PIXELS} max_image_side=${GEN_MAX_IMAGE_SIDE}"
  echo "[generation] LMUData=${LMUData} HF_HUB_CACHE=${HF_HUB_CACHE}"
  echo "[generation] persistent_run_root=${PERSIST_RUN_ROOT} cpu_threads_per_process=${VLLM_CPU_THREADS_PER_PROCESS} cpu_affinity=${VLLM_CPU_AFFINITY_GROUPS}"

  start_pool "${MODEL_PATH}" "${MODEL_SLUG}" "${GEN_PORT_START}" "${LOG_ROOT}/attempts/${RUN_ATTEMPT_ID}/vllm_generation_${MODEL_SLUG}" "${GEN_GPU_MEMORY_UTILIZATION}" "${GEN_MAX_MODEL_LEN}" "${GEN_MAX_NUM_SEQS}" "${GEN_MAX_NUM_BATCHED_TOKENS}" "${GEN_MAX_IMAGES}" "${GEN_MAX_VIDEOS}"

  python "${REPO_ROOT}/scripts/run_external_benchmark_generation_api_queue.py" \
    --model "${MODEL_PATH}" \
    --model-slug "${MODEL_SLUG}" \
    --api-model "${MODEL_SLUG}" \
    "${api_args[@]}" \
    --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
    --endpoint-failure-threshold "${GEN_ENDPOINT_FAILURE_THRESHOLD}" \
    --run-set trace_video4 \
    --run-root "${RUN_ROOT}" \
    --result-mirror-root "${PERSIST_RUN_ROOT}" \
    --exact-only \
    --only "${VIDEO_BENCHMARKS[@]}" \
    --temperature "${GEN_TEMPERATURE}" \
    --top-p "${GEN_TOP_P}" \
    --top-k "${GEN_TOP_K}" \
    --presence-penalty "${GEN_PRESENCE_PENALTY}" \
    --repetition-penalty "${GEN_REPETITION_PENALTY}" \
    --max-tokens "${GEN_MAX_TOKENS}" \
    --max-image-pixels "${GEN_MAX_IMAGE_PIXELS}" \
    --max-image-side "${GEN_MAX_IMAGE_SIDE}" \
    --image-jpeg-quality "${GEN_IMAGE_JPEG_QUALITY}" \
    --seed "${GENERATION_SEED}" \
    "${LIMIT_ARGS[@]}" \
    "${NO_RESUME_ARGS[@]}" \
    2>&1 | tee -a "${LOG_ROOT}/generation_${MODEL_SLUG}.log"

  stop_pool
  ln -sfn "$(dirname "${RUN_ROOT}")" "${LATEST_LINK}"
  echo "[generation:done] run_root=${RUN_ROOT}"
}

run_score() {
  local -a judge_endpoint_args
  build_endpoint_args "${JUDGE_PORT_START}" "--judge-api-base" judge_endpoint_args

  echo "[score:start] model_slug=${MODEL_SLUG}"
  echo "[score] benchmark_root=${BENCHMARK_ROOT}"
  echo "[score] judge_pool=${JUDGE_MODEL} served=${JUDGE_SERVED_MODEL_NAME} reasoning_parser=${JUDGE_REASONING_PARSER:-none} chat_template=${JUDGE_CHAT_TEMPLATE:-model-default}"

  start_pool "${JUDGE_MODEL}" "${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_PORT_START}" "${LOG_ROOT}/attempts/${RUN_ATTEMPT_ID}/vllm_${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_GPU_MEMORY_UTILIZATION}" "${JUDGE_MAX_MODEL_LEN}" "${JUDGE_MAX_NUM_SEQS}" "${JUDGE_MAX_NUM_BATCHED_TOKENS}" 0 0 "${JUDGE_REASONING_PARSER}" "${JUDGE_CHAT_TEMPLATE}"

  # Stock VLMEvalKit video scorers that build a judge read one
  # OPENAI_API_BASE. Run independent queue workers so the four benchmark jobs
  # can use different endpoints instead of leaving the rest of the pool idle.
  split_gpu_groups
  local score_worker_count="${SCORE_WORKERS}"
  if [[ "${score_worker_count}" == "auto" ]]; then
    score_worker_count="${#GROUP_ARRAY[@]}"
    if [[ "${score_worker_count}" -gt "${#VIDEO_BENCHMARKS[@]}" ]]; then
      score_worker_count="${#VIDEO_BENCHMARKS[@]}"
    fi
  fi
  if [[ ! "${score_worker_count}" =~ ^[1-9][0-9]*$ || "${score_worker_count}" -gt "${#GROUP_ARRAY[@]}" ]]; then
    echo "SCORE_WORKERS must be auto or an integer from 1 to ${#GROUP_ARRAY[@]}" >&2
    stop_pool
    return 2
  fi
  echo "[score] workers=${score_worker_count} queue=${RUN_TAG}_${MODEL_SLUG}_official_direct"

  local -a score_pids=()
  local offset worker_log
  for ((offset = 0; offset < score_worker_count; offset++)); do
    worker_log="${LOG_ROOT}/attempts/${RUN_ATTEMPT_ID}/score_official_direct_${MODEL_SLUG}_worker_${offset}.log"
    (
      OPENAI_API_BASE="http://${HOST}:$((JUDGE_PORT_START + offset))/v1/chat/completions" \
      OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}" \
      LOCAL_LLM="${JUDGE_SERVED_MODEL_NAME}" \
      python "${REPO_ROOT}/scripts/run_external_benchmark_score_multi_model_queue.py" \
        "${MODEL_ARGS[@]}" \
        --worker-id "${MODEL_SLUG}-${RUN_ATTEMPT_ID}-${offset}" \
        --queue-name "${RUN_TAG}_${MODEL_SLUG}_official_direct" \
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
        --stop-on-error \
        "${judge_endpoint_args[@]}" \
        "${NO_RESUME_ARGS[@]}" \
        2>&1 | tee -a "${worker_log}" "${LOG_ROOT}/score_official_direct.log"
    ) &
    score_pids+=("$!")
  done

  local score_status=0 pid
  for pid in "${score_pids[@]}"; do
    if ! wait "${pid}"; then
      score_status=1
    fi
  done

  stop_pool
  if [[ "${score_status}" -ne 0 ]]; then
    return "${score_status}"
  fi
  echo "[score:done] benchmark_root=${BENCHMARK_ROOT}"
}

run_summary() {
  local markdown="${RESULTS_ROOT}/${RUN_TAG}_${MODEL_SLUG}_results.md"
  local excel="${RESULTS_ROOT}/${RUN_TAG}_${MODEL_SLUG}_results.xlsx"

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
    2>&1 | tee -a "${LOG_ROOT}/summarize.log"

  echo "[summary:done] markdown=${markdown}"
  echo "[summary:done] excel=${excel}"
}

echo "[suite] tag=${RUN_TAG}"
echo "[suite] attempt_id=${RUN_ATTEMPT_ID}"
echo "[suite] model_slug=${MODEL_SLUG}"
echo "[suite] model_path=${MODEL_PATH}"
echo "[suite] run_root=${RUN_ROOT}"
echo "[suite] persistent_run_root=${PERSIST_RUN_ROOT}"
echo "[suite] score_root=${SCORE_ROOT}"
echo "[suite] persistent_score_root=${PERSIST_SCORE_ROOT}"
echo "[suite] log_root=${LOG_ROOT}"
echo "[suite] latest_link=${LATEST_LINK}"

restore_persistent_artifacts

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
