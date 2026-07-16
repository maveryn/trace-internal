#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
PYTHON_BIN="${PYTHON_BIN:-/home/shadeform/venv/bin/python}"
TMP_ROOT="${TMP_ROOT:-/dev/shm/trace_rlvr}"
RUN_TAG="${RUN_TAG:-trace_final31_temp06_seed42_44_3models_v1}"
CAMPAIGN_ROOT="${CAMPAIGN_ROOT:-${TMP_ROOT}/${RUN_TAG}}"
SCORE_ROOT="${SCORE_ROOT:-${CAMPAIGN_ROOT}/scoring}"
LOG_ROOT="${LOG_ROOT:-${REPO_ROOT}/logs/benchmark/${RUN_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-${REPO_ROOT}/results}"
EVAL_DEPS_ROOT="${EVAL_DEPS_ROOT:-${REPO_ROOT}/.tmp/eval_deps}"
MODEL_ROOT="${MODEL_ROOT:-${TMP_ROOT}/final25_models}"
export LMUData="${LMUData:-${TMP_ROOT}/LMUData}"
DATASET_MANIFEST="${DATASET_MANIFEST:-${LMUData}/trace_final31_dataset_manifest.json}"
SEEDS=(${SEEDS:-42 43 44})

HOST="${HOST:-127.0.0.1}"
GEN_PORT_START="${GEN_PORT_START:-18000}"
JUDGE_PORT_START="${JUDGE_PORT_START:-18100}"
GPU_GROUPS="${GPU_GROUPS:-0 1 2 3 4 5 6 7}"
CPU_AFFINITY_GROUPS="${CPU_AFFINITY_GROUPS:-0-19;20-39;40-59;60-79;96-115;116-135;136-155;156-175}"
EVAL_CPUSET="${EVAL_CPUSET:-80-95,176-183}"
ARCHIVE_CPUSET="${ARCHIVE_CPUSET:-184-191}"

GEN_PARALLELISM_PER_ENDPOINT="${GEN_PARALLELISM_PER_ENDPOINT:-32}"
GEN_PREPARATION_WORKERS="${GEN_PREPARATION_WORKERS:-32}"
GEN_PERSISTENCE_WORKERS="${GEN_PERSISTENCE_WORKERS:-16}"
GEN_FINALIZATION_WORKERS="${GEN_FINALIZATION_WORKERS:-4}"
FINALIZER_JOBS="${FINALIZER_JOBS:-2}"
GEN_QUEUE_CAPACITY="${GEN_QUEUE_CAPACITY:-256}"
GEN_MAX_MODEL_LEN="${GEN_MAX_MODEL_LEN:-32768}"
GEN_MAX_NUM_SEQS="${GEN_MAX_NUM_SEQS:-256}"
GEN_MAX_NUM_BATCHED_TOKENS="${GEN_MAX_NUM_BATCHED_TOKENS:-32768}"
GEN_GPU_MEMORY_UTILIZATION="${GEN_GPU_MEMORY_UTILIZATION:-0.90}"

JUDGE_MODEL="${JUDGE_MODEL:-${MODEL_ROOT}/qwen3-32b-judge}"
JUDGE_REVISION="${JUDGE_REVISION:-9216db5781bf21249d130ec9da846c4624c16137}"
JUDGE_SERVED_NAME="${JUDGE_SERVED_NAME:-qwen3-32b-judge}"
JUDGE_MAX_MODEL_LEN="${JUDGE_MAX_MODEL_LEN:-8192}"
JUDGE_MAX_NUM_SEQS="${JUDGE_MAX_NUM_SEQS:-128}"
JUDGE_MAX_NUM_BATCHED_TOKENS="${JUDGE_MAX_NUM_BATCHED_TOKENS:-32768}"
JUDGE_GPU_MEMORY_UTILIZATION="${JUDGE_GPU_MEMORY_UTILIZATION:-0.90}"

RUN_GENERATION="${RUN_GENERATION:-1}"
RUN_SCORING="${RUN_SCORING:-1}"
RUN_SUMMARY="${RUN_SUMMARY:-1}"
MODEL_VERIFY_DEEP="${MODEL_VERIFY_DEEP:-1}"
RUN_HF_ARCHIVE="${RUN_HF_ARCHIVE:-1}"
REQUIRE_REMOTE_ARCHIVE="${REQUIRE_REMOTE_ARCHIVE:-0}"
HF_ARCHIVE_REPO_ID="${HF_ARCHIVE_REPO_ID:-maveryn/trace-final25-eval-runs}"
HF_ARCHIVE_TOKEN_FILE="${HF_ARCHIVE_TOKEN_FILE:-${REPO_ROOT}/hf-token.txt}"
HF_ARCHIVE_SPOOL_ROOT="${HF_ARCHIVE_SPOOL_ROOT:-${CAMPAIGN_ROOT}/hf_archive}"

BASE_SLUG="qwen25vl7b-base"
TRACE_SLUG="trace-qwen25vl7b-answer-step500-rerun-20260715"
VERO_SLUG="vero-qwen25-7b"
MODEL_SLUGS=("${BASE_SLUG}" "${TRACE_SLUG}" "${VERO_SLUG}")
MODEL_PATHS=(
  "${BASE_MODEL_PATH:-${MODEL_ROOT}/qwen25vl7b-base}"
  "${TRACE_MODEL_PATH:-${TMP_ROOT}/easyr1_checkpoints/trace_qwen25vl7b_easyr1_all1000_answer_nokl_step500_bsz128_rollout8_iidval2000_rerun_20260715T161252Z/global_step_500/actor/huggingface}"
  "${VERO_MODEL_PATH:-${MODEL_ROOT}/vero-qwen25-7b}"
)
MODEL_REVISIONS=(
  "cc594898137f460bfe9f0759e9844b3ce807cfb5"
  "sha256set:8396b0be6a760ff7cbbdff02b3017b6b5bc352c87291480aba18fd3e3b6a13b5"
  "180e84be5acb2aa887cf51015b84b6a6e453ee90"
)
MODEL_SOURCES=(
  "Qwen/Qwen2.5-VL-7B-Instruct@cc594898137f460bfe9f0759e9844b3ce807cfb5"
  "maveryn/trace-qwen2.5-vl-7b@4d0f1ae8ee25022058090dbdbff61957ece7331d"
  "zlab-princeton/Vero-Qwen25-7B@180e84be5acb2aa887cf51015b84b6a6e453ee90"
)
MODEL_LABELS=("Qwen2.5-VL-7B Base" "TRACE Qwen2.5-VL-7B" "VERO Qwen2.5-VL-7B")

export PYTHONPATH="${EVAL_DEPS_ROOT}:${REPO_ROOT}:${REPO_ROOT}/scripts:${REPO_ROOT}/external/VLMEvalKit:${REPO_ROOT}/external/VLMEvalKit/scripts:${PYTHONPATH:-}"
export TMPDIR="${TMPDIR:-${TMP_ROOT}/tmp}"
export TOKENIZERS_PARALLELISM=false
export FINAL25_DATASET_MANIFEST="${DATASET_MANIFEST}"
mkdir -p "${CAMPAIGN_ROOT}" "${SCORE_ROOT}" "${LOG_ROOT}" "${RESULTS_ROOT}" "${TMPDIR}" "${HF_ARCHIVE_SPOOL_ROOT}"

eval_python() {
  if [[ -n "${EVAL_CPUSET}" && "${EVAL_CPUSET}" != "none" ]]; then
    taskset --cpu-list "${EVAL_CPUSET}" "${PYTHON_BIN}" "$@"
  else
    "${PYTHON_BIN}" "$@"
  fi
}

dataset_snapshot="$(${PYTHON_BIN} - "${DATASET_MANIFEST}" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
print(payload["view_snapshot_sha256"]["all31"])
PY
)"
dataset_schema="$(${PYTHON_BIN} - "${DATASET_MANIFEST}" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["schema_version"])
PY
)"
TRACE_GIT_COMMIT="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
TRACE_VLMEVALKIT_GIT_COMMIT="$(git -C "${REPO_ROOT}/external/VLMEvalKit" rev-parse HEAD)"
TRACE_FINAL25_CODE_HASH="$({
  find "${REPO_ROOT}/scripts" -maxdepth 1 -type f \( -name '*benchmark*queue*.py' -o -name 'final25_*.py' -o -name 'run_trace_final*.py' -o -name 'run_trace_final*.sh' -o -name 'screenspot_json_contract.py' -o -name 'trace_final25_contract.py' \) -print
  printf '%s\n' "${REPO_ROOT}/evaluation/final25/suite.v1.json"
} | LC_ALL=C sort | xargs sha256sum | sha256sum | awk '{print $1}')"
TRACE_FINAL25_DATASET_SNAPSHOT="${dataset_snapshot}"
TRACE_FINAL25_DATASET_REVISION="${dataset_schema}:${dataset_snapshot}"
TRACE_FINAL25_MODEL_REVISIONS_JSON="$(${PYTHON_BIN} - "${MODEL_SLUGS[@]}" -- "${MODEL_REVISIONS[@]}" <<'PY'
import json, sys
split = sys.argv.index("--")
print(json.dumps(dict(zip(sys.argv[1:split], sys.argv[split + 1:])), sort_keys=True))
PY
)"
TRACE_FINAL25_MODEL_SOURCES_JSON="$(${PYTHON_BIN} - "${MODEL_SLUGS[@]}" -- "${MODEL_SOURCES[@]}" <<'PY'
import json, sys
split = sys.argv.index("--")
print(json.dumps(dict(zip(sys.argv[1:split], sys.argv[split + 1:])), sort_keys=True))
PY
)"
TRACE_FINAL25_CAMPAIGN_CONFIG_HASH="$({
  printf '%s\n' \
    "run_tag=${RUN_TAG}" "suite=all31" "seeds=${SEEDS[*]}" \
    "models=${MODEL_SLUGS[*]}" "revisions=${MODEL_REVISIONS[*]}" \
    "generation=temp0.6,top_p1,top_k-1,max4096,gui_max16384" \
    "media=file-url,3136,12845056" "dataset=${TRACE_FINAL25_DATASET_REVISION}" \
    "code=${TRACE_FINAL25_CODE_HASH}"
} | sha256sum | awk '{print $1}')"
export TRACE_GIT_COMMIT TRACE_VLMEVALKIT_GIT_COMMIT TRACE_FINAL25_CODE_HASH
export TRACE_FINAL25_DATASET_SNAPSHOT TRACE_FINAL25_DATASET_REVISION
export TRACE_FINAL25_MODEL_REVISIONS_JSON TRACE_FINAL25_MODEL_SOURCES_JSON
export TRACE_FINAL25_CAMPAIGN_CONFIG_HASH
if [[ "${RUN_HF_ARCHIVE}" == "1" ]]; then
  export TRACE_FINAL25_HF_SPOOL_ROOT="${HF_ARCHIVE_SPOOL_ROOT}"
  export TRACE_FINAL25_RUN_ID="${RUN_TAG}"
  export TRACE_FINAL25_HF_REPO_ID="${HF_ARCHIVE_REPO_ID}"
  export TRACE_FINAL25_HF_REVISION=main
fi

current_pid_file=""
archive_pid=""
monitor_pid=""
finalizer_pids=()

stop_pool() {
  if [[ -n "${current_pid_file}" && -f "${current_pid_file}" ]]; then
    PID_FILE="${current_pid_file}" bash "${REPO_ROOT}/scripts/stop_vllm_endpoint_pool.sh" || true
  fi
  current_pid_file=""
}

stop_background_pid() {
  local pid="${1:-}"
  [[ -n "${pid}" ]] || return 0
  kill -TERM "${pid}" 2>/dev/null || true
  for _ in {1..20}; do
    kill -0 "${pid}" 2>/dev/null || { wait "${pid}" 2>/dev/null || true; return 0; }
    sleep 0.5
  done
  kill -KILL "${pid}" 2>/dev/null || true
  wait "${pid}" 2>/dev/null || true
}

cleanup() {
  local status=$?
  set +e
  for pid in "${finalizer_pids[@]:-}"; do stop_background_pid "${pid}"; done
  stop_pool
  stop_background_pid "${monitor_pid}"
  stop_background_pid "${archive_pid}"
  return "${status}"
}
trap cleanup EXIT

start_pool() {
  local model="$1" served="$2" port="$3" log_dir="$4" max_len="$5" max_seqs="$6" max_tokens="$7" memory="$8"
  local reasoning_parser="${9:-}" chat_template="${10:-}"
  current_pid_file="${log_dir}/pids.txt"
  MODEL_PATH="${model}" SERVED_MODEL_NAME="${served}" HOST="${HOST}" PORT_START="${port}" \
  GPU_GROUPS="${GPU_GROUPS}" CPU_AFFINITY_GROUPS="${CPU_AFFINITY_GROUPS}" \
  GPU_MEMORY_UTILIZATION="${memory}" MAX_MODEL_LEN="${max_len}" MAX_NUM_SEQS="${max_seqs}" \
  MAX_NUM_BATCHED_TOKENS="${max_tokens}" CPU_THREADS_PER_PROCESS=8 \
  ALLOWED_LOCAL_MEDIA_PATH="${LMUData}" PYTHON_BIN="${PYTHON_BIN}" \
  REASONING_PARSER="${reasoning_parser}" CHAT_TEMPLATE="${chat_template}" \
  LOG_DIR="${log_dir}" PID_FILE="${current_pid_file}" \
    bash "${REPO_ROOT}/scripts/start_vllm_endpoint_pool.sh"
}

endpoint_args() {
  local port_start="$1" flag="$2"
  local offset=0
  for _group in ${GPU_GROUPS}; do
    printf '%s\n' "${flag}" "http://${HOST}:$((port_start + offset))/v1"
    offset=$((offset + 1))
  done
}

validate_environment() {
  bash "${REPO_ROOT}/scripts/setup_trace_final25_eval_env.sh" --verify-only
  eval_python "${REPO_ROOT}/scripts/prepare_trace_final25_datasets.py" \
    --view all31 --lmu-root "${LMUData}" --manifest "${DATASET_MANIFEST}" --verify-only
  local verify_args=()
  for i in "${!MODEL_SLUGS[@]}"; do
    verify_args+=(--entry "${MODEL_SLUGS[$i]}=${MODEL_PATHS[$i]}=${MODEL_REVISIONS[$i]}")
  done
  verify_args+=(--entry "qwen3-32b-judge=${JUDGE_MODEL}=${JUDGE_REVISION}")
  [[ "${MODEL_VERIFY_DEEP}" == "1" ]] && verify_args+=(--deep)
  eval_python "${REPO_ROOT}/scripts/prepare_trace_final25_models.py" verify "${verify_args[@]}"
}

start_archive() {
  [[ "${RUN_HF_ARCHIVE}" == "1" ]] || return 0
  if [[ ! -f "${HF_ARCHIVE_TOKEN_FILE}" ]]; then
    echo "[archive:warning] token file missing; slices will remain in local spool" >&2
    return 0
  fi
  local command=("${PYTHON_BIN}" "${REPO_ROOT}/scripts/final25_hf_archive.py" \
    --spool-root "${HF_ARCHIVE_SPOOL_ROOT}" --repo-id "${HF_ARCHIVE_REPO_ID}" \
    --token-file "${HF_ARCHIVE_TOKEN_FILE}" --batch-size 48 --upload-threads 8 daemon --poll-seconds 30)
  if [[ -n "${ARCHIVE_CPUSET}" && "${ARCHIVE_CPUSET}" != "none" ]]; then
    command=(taskset --cpu-list "${ARCHIVE_CPUSET}" "${command[@]}")
  fi
  "${command[@]}" >>"${LOG_ROOT}/hf_archive_daemon.log" 2>&1 &
  archive_pid=$!
  echo "[archive:started] pid=${archive_pid} spool=${HF_ARCHIVE_SPOOL_ROOT}"
}

flush_archive() {
  [[ "${RUN_HF_ARCHIVE}" == "1" && -f "${HF_ARCHIVE_TOKEN_FILE}" ]] || return 0
  local command=("${PYTHON_BIN}" "${REPO_ROOT}/scripts/final25_hf_archive.py" \
    --spool-root "${HF_ARCHIVE_SPOOL_ROOT}" --repo-id "${HF_ARCHIVE_REPO_ID}" \
    --token-file "${HF_ARCHIVE_TOKEN_FILE}" --batch-size 48 --upload-threads 8 flush)
  if [[ -n "${ARCHIVE_CPUSET}" && "${ARCHIVE_CPUSET}" != "none" ]]; then
    command=(taskset --cpu-list "${ARCHIVE_CPUSET}" "${command[@]}")
  fi
  if ! "${command[@]}" >>"${LOG_ROOT}/hf_archive_flush.log" 2>&1; then
    if [[ "${REQUIRE_REMOTE_ARCHIVE}" == "1" ]]; then
      echo "[archive:error] final archive flush failed" >&2
      return 1
    fi
    echo "[archive:warning] final archive flush failed; slices remain in local spool" >&2
  fi
}

start_monitor() {
  eval_python "${REPO_ROOT}/scripts/status_trace_final31_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" --score-root "${SCORE_ROOT}" \
    --dataset-manifest "${DATASET_MANIFEST}" --archive-spool-root "${HF_ARCHIVE_SPOOL_ROOT}" \
    --watch 30 >>"${LOG_ROOT}/status.log" 2>&1 &
  monitor_pid=$!
}

generation_complete() {
  local slug="$1" model="$2" revision="$3" seed="$4"
  eval_python "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" --phase generation --suite all31 \
    --model-slug "${slug}" --model-entry "${slug}=${model}=${revision}" \
    --dataset-manifest "${DATASET_MANIFEST}" --seeds "${seed}" >/dev/null 2>&1
}

run_generation_pass() {
  local mode="$1" slug="$2" model="$3" seed="$4" max_tokens="$5"
  local -a endpoints selectors
  mapfile -t endpoints < <(endpoint_args "${GEN_PORT_START}" --api-base)
  if [[ "${mode}" == "gui" ]]; then
    selectors=(--only screenspot screenspotpro screenspot_v2)
  else
    selectors=(--exclude screenspot screenspotpro screenspot_v2)
  fi
  local run_root="${CAMPAIGN_ROOT}/seed_${seed}/runs"
  mkdir -p "${run_root}"
  eval_python "${REPO_ROOT}/scripts/run_external_benchmark_generation_api_queue.py" \
    --model "${model}" --model-slug "${slug}" --api-model "${slug}" \
    "${endpoints[@]}" --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
    --preparation-workers "${GEN_PREPARATION_WORKERS}" --queue-capacity "${GEN_QUEUE_CAPACITY}" \
    --persistence-workers "${GEN_PERSISTENCE_WORKERS}" --finalization-workers "${GEN_FINALIZATION_WORKERS}" \
    --media-transport file-url --allowed-local-media-path "${LMUData}" \
    --dataset-manifest "${DATASET_MANIFEST}" --dataset-manifest-view all31 \
    --min-image-pixels 3136 --max-image-pixels 12845056 \
    --run-set trace_final31 --run-root "${run_root}" "${selectors[@]}" \
    --temperature 0.6 --top-p 1 --top-k -1 --presence-penalty 0 \
    --repetition-penalty 1 --max-tokens "${max_tokens}" --seed "${seed}" \
    --compact-prediction-tables --defer-finalization \
    2>&1 | tee "${LOG_ROOT}/generation_${slug}_seed${seed}_${mode}.log"

  while [[ "${#finalizer_pids[@]}" -ge "${FINALIZER_JOBS}" ]]; do
    local oldest="${finalizer_pids[0]}"
    if ! wait "${oldest}"; then
      echo "[generation:error] asynchronous finalizer ${oldest} failed" >&2
      return 1
    fi
    finalizer_pids=("${finalizer_pids[@]:1}")
  done
  (
    set -o pipefail
    eval_python "${REPO_ROOT}/scripts/run_external_benchmark_generation_api_queue.py" \
      --model "${model}" --model-slug "${slug}" --api-model "${slug}" --finalize-only \
      --finalization-workers "${GEN_FINALIZATION_WORKERS}" --preparation-workers "${GEN_PREPARATION_WORKERS}" \
      --queue-capacity "${GEN_QUEUE_CAPACITY}" --persistence-workers "${GEN_PERSISTENCE_WORKERS}" \
      --media-transport file-url --allowed-local-media-path "${LMUData}" \
      --dataset-manifest "${DATASET_MANIFEST}" --dataset-manifest-view all31 \
      --min-image-pixels 3136 --max-image-pixels 12845056 \
      --run-set trace_final31 --run-root "${run_root}" "${selectors[@]}" \
      --temperature 0.6 --top-p 1 --top-k -1 --presence-penalty 0 \
      --repetition-penalty 1 --max-tokens "${max_tokens}" --seed "${seed}" \
      --compact-prediction-tables \
      2>&1 | tee "${LOG_ROOT}/generation_finalize_${slug}_seed${seed}_${mode}.log"
  ) &
  finalizer_pids+=("$!")
}

run_generation() {
  for i in "${!MODEL_SLUGS[@]}"; do
    local slug="${MODEL_SLUGS[$i]}" model="${MODEL_PATHS[$i]}" revision="${MODEL_REVISIONS[$i]}"
    local all_complete=1
    for seed in "${SEEDS[@]}"; do
      generation_complete "${slug}" "${model}" "${revision}" "${seed}" || all_complete=0
    done
    if [[ "${all_complete}" == "1" ]]; then
      echo "[generation:skip-model] ${slug}"
      continue
    fi
    echo "[generation:model-start] ${slug} eight TP1 replicas"
    start_pool "${model}" "${slug}" "${GEN_PORT_START}" "${LOG_ROOT}/vllm_generation_${slug}" \
      "${GEN_MAX_MODEL_LEN}" "${GEN_MAX_NUM_SEQS}" "${GEN_MAX_NUM_BATCHED_TOKENS}" "${GEN_GPU_MEMORY_UTILIZATION}"
    for seed in "${SEEDS[@]}"; do
      if generation_complete "${slug}" "${model}" "${revision}" "${seed}"; then
        echo "[generation:skip-seed] ${slug} seed=${seed}"
        continue
      fi
      run_generation_pass default "${slug}" "${model}" "${seed}" 4096
      run_generation_pass gui "${slug}" "${model}" "${seed}" 16384
    done
    stop_pool
  done
  local failed=0
  for pid in "${finalizer_pids[@]}"; do
    wait "${pid}" || failed=1
  done
  finalizer_pids=()
  [[ "${failed}" == "0" ]] || { echo "[generation:error] asynchronous finalizer failed" >&2; return 1; }
  for i in "${!MODEL_SLUGS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      generation_complete "${MODEL_SLUGS[$i]}" "${MODEL_PATHS[$i]}" "${MODEL_REVISIONS[$i]}" "${seed}"
    done
  done
}

run_scoring() {
  local -a judge_endpoints campaigns
  mapfile -t judge_endpoints < <(endpoint_args "${JUDGE_PORT_START}" --judge-endpoint)
  for i in "${!MODEL_SLUGS[@]}"; do
    campaigns+=(--campaign "${MODEL_PATHS[$i]}" "${MODEL_SLUGS[$i]}" "${CAMPAIGN_ROOT}")
  done
  start_pool "${JUDGE_MODEL}" "${JUDGE_SERVED_NAME}" "${JUDGE_PORT_START}" "${LOG_ROOT}/vllm_judge" \
    "${JUDGE_MAX_MODEL_LEN}" "${JUDGE_MAX_NUM_SEQS}" "${JUDGE_MAX_NUM_BATCHED_TOKENS}" "${JUDGE_GPU_MEMORY_UTILIZATION}" \
    qwen3 "${REPO_ROOT}/rlvr/examples/prompts/chat_template_no_think.jinja"
  for seed in "${SEEDS[@]}"; do
    eval_python "${REPO_ROOT}/scripts/run_trace_final26_official_score_campaign.py" \
      --suite all31 --seed "${seed}" --shared-seed-root --resume --emit-archive \
      "${campaigns[@]}" --score-root "${SCORE_ROOT}" --dataset-manifest "${DATASET_MANIFEST}" \
      --judge-model "${JUDGE_MODEL}" --judge-api-model "${JUDGE_SERVED_NAME}" \
      "${judge_endpoints[@]}" --official-workers 8 --direct-workers 8 --mme-workers 3 \
      --eval-nproc 16 --judge-api-parallelism 64 --judge-api-batch-size 64 \
      2>&1 | tee "${LOG_ROOT}/scoring_seed${seed}.log"
  done
  stop_pool
}

run_summary() {
  eval_python "${REPO_ROOT}/scripts/summarize_trace_final25_multiseed.py" \
    --score-root-base "${SCORE_ROOT}" --suite all31 --seeds "${SEEDS[@]}" \
    --model-entry "${BASE_SLUG}=${MODEL_LABELS[0]}" \
    --model-entry "${TRACE_SLUG}=${MODEL_LABELS[1]}" \
    --model-entry "${VERO_SLUG}=${MODEL_LABELS[2]}" \
    --delta "TRACE - Base=${TRACE_SLUG}=${BASE_SLUG}" \
    --delta "TRACE - VERO=${TRACE_SLUG}=${VERO_SLUG}" \
    --excel "${RESULTS_ROOT}/${RUN_TAG}_results.xlsx" \
    --markdown "${RESULTS_ROOT}/${RUN_TAG}_results.md" \
    2>&1 | tee "${LOG_ROOT}/summary.log"
}

verify_archive_coverage() {
  [[ "${RUN_HF_ARCHIVE}" == "1" ]] || return 0
  local -a args=(--spool-root "${HF_ARCHIVE_SPOOL_ROOT}" --repo-id "${HF_ARCHIVE_REPO_ID}" \
    --token-file "${HF_ARCHIVE_TOKEN_FILE}" coverage --expect-run-id "${RUN_TAG}" \
    --expect-campaign-config-hash "${TRACE_FINAL25_CAMPAIGN_CONFIG_HASH}" \
    --expect-dataset-revision "${TRACE_FINAL25_DATASET_REVISION}")
  local slug seed key
  for slug in "${MODEL_SLUGS[@]}"; do args+=(--expect-model-slug "${slug}"); done
  for seed in "${SEEDS[@]}"; do args+=(--expect-seed "${seed}"); done
  while read -r key; do args+=(--expect-benchmark "${key}"); done < <(
    "${PYTHON_BIN}" - <<'PY'
from benchmark_queue_lib import TRACE_FINAL31_BENCHMARKS
print(*TRACE_FINAL31_BENCHMARKS, sep="\n")
PY
  )
  eval_python "${REPO_ROOT}/scripts/final25_hf_archive.py" "${args[@]}"
  if [[ "${REQUIRE_REMOTE_ARCHIVE}" == "1" ]]; then
    local verify_args=("${args[@]}")
    for i in "${!verify_args[@]}"; do
      [[ "${verify_args[$i]}" == "coverage" ]] && verify_args[$i]=verify
    done
    eval_python "${REPO_ROOT}/scripts/final25_hf_archive.py" "${verify_args[@]}"
  fi
}

echo "[campaign] tag=${RUN_TAG} suite=all31 models=3 seeds=${SEEDS[*]} rows_per_model_seed=40527"
echo "[campaign] generation=eight_tp1_per_model scoring=eight_tp1_qwen3 archive=asynchronous"
if [[ ! "${FINALIZER_JOBS}" =~ ^[1-9][0-9]*$ ]]; then
  echo "[fatal] FINALIZER_JOBS must be a positive integer" >&2
  exit 1
fi
validate_environment
start_archive
start_monitor
[[ "${RUN_GENERATION}" == "1" ]] && run_generation
[[ "${RUN_SCORING}" == "1" ]] && run_scoring
[[ "${RUN_SUMMARY}" == "1" ]] && run_summary
stop_background_pid "${archive_pid}"
archive_pid=""
flush_archive
if ! verify_archive_coverage; then
  if [[ "${REQUIRE_REMOTE_ARCHIVE}" == "1" ]]; then
    echo "[archive:error] required archive verification failed" >&2
    exit 1
  fi
  echo "[archive:warning] archive coverage is incomplete; evaluation artifacts remain authoritative" >&2
fi
eval_python "${REPO_ROOT}/scripts/status_trace_final31_campaign.py" \
  --campaign-root "${CAMPAIGN_ROOT}" --score-root "${SCORE_ROOT}" \
  --dataset-manifest "${DATASET_MANIFEST}" --archive-spool-root "${HF_ARCHIVE_SPOOL_ROOT}" \
  --fail-if-incomplete
echo "[campaign:done] ${RESULTS_ROOT}/${RUN_TAG}_results.xlsx"
