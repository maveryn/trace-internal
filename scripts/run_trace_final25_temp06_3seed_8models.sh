#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
PYTHON_BIN="${PYTHON_BIN:-/home/shadeform/venv/bin/python}"
RUN_TAG="${RUN_TAG:-trace_final25_temp06_seed42_44_8models_v1}"
TMP_ROOT="${TMP_ROOT:-/dev/shm/trace_rlvr}"
CAMPAIGN_ROOT="${CAMPAIGN_ROOT:-${TMP_ROOT}/${RUN_TAG}}"
LOG_ROOT="${LOG_ROOT:-${REPO_ROOT}/logs/benchmark/${RUN_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-${REPO_ROOT}/results}"
REUSE_SEARCH_ROOT="${REUSE_SEARCH_ROOT:-${TMP_ROOT}}"

HOST="${HOST:-127.0.0.1}"
GEN_PORT_START="${GEN_PORT_START:-18000}"
JUDGE_PORT_START="${JUDGE_PORT_START:-18100}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"
SEEDS=(${SEEDS:-42 43 44})

GEN_GPU_MEMORY_UTILIZATION="${GEN_GPU_MEMORY_UTILIZATION:-0.90}"
GEN_MAX_MODEL_LEN="${GEN_MAX_MODEL_LEN:-32768}"
GEN_MAX_NUM_SEQS="${GEN_MAX_NUM_SEQS:-256}"
GEN_MAX_NUM_BATCHED_TOKENS="${GEN_MAX_NUM_BATCHED_TOKENS:-32768}"
GEN_PARALLELISM_PER_ENDPOINT="${GEN_PARALLELISM_PER_ENDPOINT:-32}"
GEN_MAX_TOKENS="${GEN_MAX_TOKENS:-4096}"
GEN_TEMPERATURE="${GEN_TEMPERATURE:-0.6}"
GEN_TOP_P="${GEN_TOP_P:-1.0}"
GEN_TOP_K="${GEN_TOP_K:--1}"
GEN_PRESENCE_PENALTY="${GEN_PRESENCE_PENALTY:-0.0}"
GEN_REPETITION_PENALTY="${GEN_REPETITION_PENALTY:-1.0}"

JUDGE_MODEL="${JUDGE_MODEL:-Qwen/Qwen3-32B}"
JUDGE_SERVED_MODEL_NAME="${JUDGE_SERVED_MODEL_NAME:-qwen3-32b-judge}"
JUDGE_GPU_MEMORY_UTILIZATION="${JUDGE_GPU_MEMORY_UTILIZATION:-0.90}"
JUDGE_MAX_MODEL_LEN="${JUDGE_MAX_MODEL_LEN:-8192}"
JUDGE_MAX_NUM_SEQS="${JUDGE_MAX_NUM_SEQS:-128}"
JUDGE_MAX_NUM_BATCHED_TOKENS="${JUDGE_MAX_NUM_BATCHED_TOKENS:-32768}"
JUDGE_API_PARALLELISM="${JUDGE_API_PARALLELISM:-128}"
JUDGE_API_BATCH_SIZE="${JUDGE_API_BATCH_SIZE:-128}"
JUDGE_API_BATCHES_PER_ENDPOINT="${JUDGE_API_BATCHES_PER_ENDPOINT:-2}"
JUDGE_API_MAX_BATCH_CHARS="${JUDGE_API_MAX_BATCH_CHARS:-200000}"

RUN_REUSE="${RUN_REUSE:-1}"
RUN_GENERATION="${RUN_GENERATION:-1}"
RUN_SCORING="${RUN_SCORING:-1}"
RUN_SUMMARY="${RUN_SUMMARY:-1}"

MODEL_SLUGS=(
  qwen25vl3b-base
  trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500
  qwen25vl7b-base
  trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500
  game-rl-qwen25vl7b
  sphinx-qwen7b-500
  pcgrpo-qwen25vl7b-jigsaw-care
  vero-qwen25-7b
)

MODEL_PATHS=(
  Qwen/Qwen2.5-VL-3B-Instruct
  /dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500
  Qwen/Qwen2.5-VL-7B-Instruct
  /dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500
  /dev/shm/trace_rlvr/hf_models/game-rl-qwen25vl7b_patched
  /dev/shm/trace_rlvr/hf_models/sphinx_qwen7b_500
  /dev/shm/trace_rlvr/hf_models/pcgrpo-qwen25vl7b-jigsaw-care
  /dev/shm/trace_rlvr/hf_models/vero-qwen25-7b
)

MODEL_LABELS=(
  "Qwen2.5-VL-3B Base"
  "Qwen2.5-VL-3B Answer GRPO 500"
  "Qwen2.5-VL-7B Base"
  "Qwen2.5-VL-7B Answer GRPO 500"
  "OpenMOSS Game-RL Qwen2.5-VL-7B"
  "Sphinx Qwen2.5-VL-7B 500"
  "PCGRPO Qwen2.5-VL-7B Jigsaw CARE"
  "Vero Qwen2.5-VL-7B"
)

mkdir -p "${CAMPAIGN_ROOT}" "${LOG_ROOT}" "${RESULTS_ROOT}" "${TMP_ROOT}/tmp"
export TMPDIR="${TMPDIR:-${TMP_ROOT}/tmp}"
export LMUData="${LMUData:-${TMP_ROOT}/LMUData}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

current_pid_file=""
cleanup_current_pool() {
  if [[ -n "${current_pid_file}" && -f "${current_pid_file}" ]]; then
    PID_FILE="${current_pid_file}" bash "${REPO_ROOT}/scripts/stop_vllm_endpoint_pool.sh" || true
  fi
}
trap cleanup_current_pool EXIT INT TERM

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
  local -n output_array="$3"
  output_array=()
  split_gpu_groups
  for offset in "${!GROUP_ARRAY[@]}"; do
    output_array+=("${flag}" "http://${HOST}:$((port_start + offset))/v1")
  done
}

start_pool() {
  local model="$1"
  local served_name="$2"
  local port_start="$3"
  local log_dir="$4"
  local gpu_memory_utilization="$5"
  local max_model_len="$6"
  local max_num_seqs="$7"
  local max_num_batched_tokens="$8"

  current_pid_file="${log_dir}/pids.txt"
  MODEL_PATH="${model}" \
  SERVED_MODEL_NAME="${served_name}" \
  HOST="${HOST}" \
  PORT_START="${port_start}" \
  GPU_GROUPS="${GPU_GROUPS}" \
  GPU_MEMORY_UTILIZATION="${gpu_memory_utilization}" \
  MAX_MODEL_LEN="${max_model_len}" \
  MAX_NUM_SEQS="${max_num_seqs}" \
  MAX_NUM_BATCHED_TOKENS="${max_num_batched_tokens}" \
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

validate_models() {
  for model in "${MODEL_PATHS[@]}"; do
    if [[ "${model}" == /* && ! -f "${model}/config.json" ]]; then
      echo "[fatal] missing model config: ${model}/config.json" >&2
      exit 1
    fi
  done
}

model_args() {
  local -n output_array="$1"
  output_array=()
  for i in "${!MODEL_SLUGS[@]}"; do
    output_array+=(--model-entry "${MODEL_SLUGS[$i]}=${MODEL_PATHS[$i]}")
  done
}

reuse_generation() {
  echo "[reuse:start] search_root=${REUSE_SEARCH_ROOT} campaign=${CAMPAIGN_ROOT}"
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/reuse_trace_final25_generation_rows.py" \
    --campaign-root "${CAMPAIGN_ROOT}" \
    --search-root "${REUSE_SEARCH_ROOT}" \
    --seeds "${SEEDS[@]}" \
    --temperature "${GEN_TEMPERATURE}" \
    --top-p "${GEN_TOP_P}" \
    --top-k "${GEN_TOP_K}" \
    --presence-penalty "${GEN_PRESENCE_PENALTY}" \
    --repetition-penalty "${GEN_REPETITION_PENALTY}" \
    --max-tokens "${GEN_MAX_TOKENS}" \
    2>&1 | tee "${LOG_ROOT}/reuse_generation.log"
}

generation_complete_for_model() {
  local slug="$1"
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" \
    --phase generation \
    --model-slug "${slug}" \
    --seeds "${SEEDS[@]}"
}

generation_complete_for_model_seed() {
  local slug="$1"
  local seed="$2"
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" \
    --phase generation \
    --model-slug "${slug}" \
    --seeds "${seed}"
}

run_generation() {
  validate_models
  local -a api_args
  build_endpoint_args "${GEN_PORT_START}" --api-base api_args
  for i in "${!MODEL_SLUGS[@]}"; do
    local slug="${MODEL_SLUGS[$i]}"
    local model="${MODEL_PATHS[$i]}"
    if generation_complete_for_model "${slug}"; then
      echo "[generation:skip-model] slug=${slug} all seeds complete"
      continue
    fi
    echo "[generation:model-start] slug=${slug} model=${model}"
    start_pool \
      "${model}" "${slug}" "${GEN_PORT_START}" "${LOG_ROOT}/vllm_generation_${slug}" \
      "${GEN_GPU_MEMORY_UTILIZATION}" "${GEN_MAX_MODEL_LEN}" "${GEN_MAX_NUM_SEQS}" "${GEN_MAX_NUM_BATCHED_TOKENS}"
    for seed in "${SEEDS[@]}"; do
      if generation_complete_for_model_seed "${slug}" "${seed}"; then
        echo "[generation:skip-seed] slug=${slug} seed=${seed} complete"
        continue
      fi
      local run_root="${CAMPAIGN_ROOT}/seed_${seed}/runs"
      mkdir -p "${run_root}"
      echo "[generation:start] slug=${slug} seed=${seed} run_root=${run_root}"
      "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_external_benchmark_generation_api_queue.py" \
        --model "${model}" \
        --model-slug "${slug}" \
        --api-model "${slug}" \
        "${api_args[@]}" \
        --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
        --run-set trace_final25 \
        --run-root "${run_root}" \
        --temperature "${GEN_TEMPERATURE}" \
        --top-p "${GEN_TOP_P}" \
        --top-k "${GEN_TOP_K}" \
        --presence-penalty "${GEN_PRESENCE_PENALTY}" \
        --repetition-penalty "${GEN_REPETITION_PENALTY}" \
        --max-tokens "${GEN_MAX_TOKENS}" \
        --seed "${seed}" \
        --compact-prediction-tables \
        2>&1 | tee "${LOG_ROOT}/generation_${slug}_seed${seed}.log"
    done
    stop_pool
    echo "[generation:model-done] slug=${slug}"
  done

  local verify_args=()
  for slug in "${MODEL_SLUGS[@]}"; do
    verify_args+=(--model-slug "${slug}")
  done
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" --phase generation \
    "${verify_args[@]}" --seeds "${SEEDS[@]}"
}

run_mme_scoring() {
  local -a judge_args
  build_endpoint_args "${JUDGE_PORT_START}" --judge-api-base judge_args
  for seed in "${SEEDS[@]}"; do
    local run_root="${CAMPAIGN_ROOT}/seed_${seed}/runs"
    local benchmark_root="${CAMPAIGN_ROOT}/seed_${seed}/benchmark"
    for i in "${!MODEL_SLUGS[@]}"; do
      local slug="${MODEL_SLUGS[$i]}"
      local model="${MODEL_PATHS[$i]}"
      local score_file="${benchmark_root}/mme_reasoning/${slug}/vlmevalkit_defaults_qwen32b_judge/scores.json"
      if [[ -f "${score_file}" ]]; then
        echo "[mme-score:skip] seed=${seed} slug=${slug} score=${score_file}"
        continue
      fi
      echo "[mme-score:start] seed=${seed} slug=${slug}"
      "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_mme_reasoning_eval.py" score \
        --model "${model}" \
        --model-slug "${slug}" \
        --run-root "${run_root}" \
        --benchmark-root "${benchmark_root}" \
        --judge-model "${JUDGE_MODEL}" \
        --judge-api-model "${JUDGE_SERVED_MODEL_NAME}" \
        --judge-api-tokenizer-model "${JUDGE_MODEL}" \
        --judge-api-parallelism "${JUDGE_API_PARALLELISM}" \
        "${judge_args[@]}" \
        2>&1 | tee "${LOG_ROOT}/score_mme_${slug}_seed${seed}.log"
    done
  done
}

run_scoring() {
  local -a all_model_args
  local -a judge_args
  local -a llm_api_args
  local -a verify_args=()
  model_args all_model_args
  for slug in "${MODEL_SLUGS[@]}"; do
    verify_args+=(--model-slug "${slug}")
  done
  if "${PYTHON_BIN}" "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" --phase score \
    "${verify_args[@]}" --seeds "${SEEDS[@]}"; then
    echo "[score:skip] all Final25 scores already complete"
    return
  fi
  build_endpoint_args "${JUDGE_PORT_START}" --judge-api-base judge_args
  build_endpoint_args "${JUDGE_PORT_START}" --api-base llm_api_args

  echo "[judge:start] model=${JUDGE_MODEL} endpoints=${GPU_GROUPS}"
  start_pool \
    "${JUDGE_MODEL}" "${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_PORT_START}" "${LOG_ROOT}/vllm_judge" \
    "${JUDGE_GPU_MEMORY_UTILIZATION}" "${JUDGE_MAX_MODEL_LEN}" "${JUDGE_MAX_NUM_SEQS}" "${JUDGE_MAX_NUM_BATCHED_TOKENS}"

  for seed in "${SEEDS[@]}"; do
    local run_root="${CAMPAIGN_ROOT}/seed_${seed}/runs"
    local benchmark_root="${CAMPAIGN_ROOT}/seed_${seed}/benchmark"
    local output_root="${CAMPAIGN_ROOT}/seed_${seed}/llm_extracted"
    local queue_root="${CAMPAIGN_ROOT}/seed_${seed}/queues"
    mkdir -p "${benchmark_root}" "${output_root}" "${queue_root}"

    echo "[score:direct:start] seed=${seed}"
    "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_external_benchmark_score_multi_model_queue.py" \
      "${all_model_args[@]}" \
      --queue-name "${RUN_TAG}_seed${seed}_direct" \
      --queue-root "${queue_root}" \
      --run-set trace_final25 \
      --run-root "${run_root}" \
      --benchmark-root "${benchmark_root}" \
      --judge-model "${JUDGE_MODEL}" \
      --judge-api-model "${JUDGE_SERVED_MODEL_NAME}" \
      --judge-api-tokenizer-model "${JUDGE_MODEL}" \
      --judge-api-parallelism "${JUDGE_API_PARALLELISM}" \
      "${judge_args[@]}" \
      --stop-on-error \
      2>&1 | tee "${LOG_ROOT}/score_direct_seed${seed}.log"

    echo "[score:llm-extract:start] seed=${seed}"
    "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_llm_extracted_benchmark_score_queue.py" \
      --prepare --api-run --finalize --final25 \
      --queue-name "${RUN_TAG}_seed${seed}_llm_extract" \
      --queue-root "${queue_root}" \
      --run-root "${run_root}" \
      --output-root "${output_root}" \
      --benchmark-root "${benchmark_root}" \
      "${all_model_args[@]}" \
      --api-model "${JUDGE_SERVED_MODEL_NAME}" \
      --api-tokenizer-model "${JUDGE_MODEL}" \
      --api-parallelism 16 \
      --api-batch-size "${JUDGE_API_BATCH_SIZE}" \
      --api-batches-per-endpoint "${JUDGE_API_BATCHES_PER_ENDPOINT}" \
      --api-max-batch-chars "${JUDGE_API_MAX_BATCH_CHARS}" \
      --judge-model "${JUDGE_MODEL}" \
      --judge-max-tokens 256 \
      "${llm_api_args[@]}" \
      2>&1 | tee "${LOG_ROOT}/score_llm_extract_seed${seed}.log"
  done

  run_mme_scoring
  stop_pool

  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" --phase score \
    "${verify_args[@]}" --seeds "${SEEDS[@]}"
}

run_summary() {
  local -a summary_model_args=()
  for i in "${!MODEL_SLUGS[@]}"; do
    summary_model_args+=(--model-entry "${MODEL_SLUGS[$i]}=${MODEL_LABELS[$i]}")
  done
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/summarize_trace_final25_multiseed.py" \
    --score-root-base "${CAMPAIGN_ROOT}" \
    "${summary_model_args[@]}" \
    --seeds "${SEEDS[@]}" \
    --excel "${RESULTS_ROOT}/${RUN_TAG}_results.xlsx" \
    --markdown "${RESULTS_ROOT}/${RUN_TAG}_results.md" \
    2>&1 | tee "${LOG_ROOT}/summary.log"
}

echo "[campaign] tag=${RUN_TAG}"
echo "[campaign] root=${CAMPAIGN_ROOT}"
echo "[campaign] logs=${LOG_ROOT}"
echo "[campaign] seeds=${SEEDS[*]} models=${#MODEL_SLUGS[@]} benchmarks=25"
echo "[campaign] generation=temp${GEN_TEMPERATURE},top_p${GEN_TOP_P},top_k${GEN_TOP_K},max${GEN_MAX_TOKENS}"
echo "[campaign] judge=${JUDGE_MODEL},temperature0"

if [[ "${RUN_REUSE}" == "1" ]]; then
  reuse_generation
fi
if [[ "${RUN_GENERATION}" == "1" ]]; then
  run_generation
fi
if [[ "${RUN_SCORING}" == "1" ]]; then
  run_scoring
fi
if [[ "${RUN_SUMMARY}" == "1" ]]; then
  run_summary
fi

echo "[campaign:done] results=${RESULTS_ROOT}/${RUN_TAG}_results.xlsx"
