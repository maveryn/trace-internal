#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
PYTHON_BIN="${PYTHON_BIN:-/home/shadeform/venv/bin/python}"
RUN_TAG="${RUN_TAG:-trace_final25_temp06_seed42_44_8models_v2}"
TMP_ROOT="${TMP_ROOT:-/dev/shm/trace_rlvr}"
CAMPAIGN_ROOT="${CAMPAIGN_ROOT:-${TMP_ROOT}/${RUN_TAG}}"
LOG_ROOT="${LOG_ROOT:-${REPO_ROOT}/logs/benchmark/${RUN_TAG}}"
RESULTS_ROOT="${RESULTS_ROOT:-${REPO_ROOT}/results}"
REUSE_SEARCH_ROOT="${REUSE_SEARCH_ROOT:-${TMP_ROOT}}"
EVAL_DEPS_ROOT="${EVAL_DEPS_ROOT:-${REPO_ROOT}/.tmp/eval_deps}"
FINAL25_MODEL_ROOT="${FINAL25_MODEL_ROOT:-${TMP_ROOT}/final25_models}"
FINAL25_MODEL_MANIFEST="${FINAL25_MODEL_MANIFEST:-${REPO_ROOT}/rlvr/experiments/final_answer_only_manifest.json}"
export LMUData="${LMUData:-${TMP_ROOT}/LMUData}"
FINAL25_DATASET_MANIFEST="${FINAL25_DATASET_MANIFEST:-${LMUData}/trace_final25_dataset_manifest.json}"
MODEL_VERIFY_DEEP="${MODEL_VERIFY_DEEP:-1}"
EXPECTED_VLMEVALKIT_COMMIT="a8b12bf1c3737a33fc1de967c202f9c592b22e86"

SUITE="${SUITE:-frozen}"
case "${SUITE}" in
  frozen)
    SUITE_RUN_SET="trace_final25"
    SUITE_DATASET_VIEW="frozen"
    SUITE_BENCHMARK_COUNT=25
    ;;
  all26)
    SUITE_RUN_SET="trace_final26"
    SUITE_DATASET_VIEW="all26"
    SUITE_BENCHMARK_COUNT=26
    ;;
  *)
    echo "[fatal] SUITE must be frozen or all26, got: ${SUITE}" >&2
    exit 1
    ;;
esac

export PYTHONPATH="${EVAL_DEPS_ROOT}:${REPO_ROOT}:${REPO_ROOT}/scripts:${REPO_ROOT}/external/VLMEvalKit:${REPO_ROOT}/external/VLMEvalKit/scripts:${PYTHONPATH:-}"

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
GEN_ENDPOINT_FAILURE_THRESHOLD="${GEN_ENDPOINT_FAILURE_THRESHOLD:-2}"
GEN_PREPARATION_WORKERS="${GEN_PREPARATION_WORKERS:-32}"
GEN_QUEUE_CAPACITY="${GEN_QUEUE_CAPACITY:-256}"
GEN_PERSISTENCE_WORKERS="${GEN_PERSISTENCE_WORKERS:-16}"
GEN_FINALIZATION_WORKERS="${GEN_FINALIZATION_WORKERS:-2}"
GEN_MEDIA_TRANSPORT="${GEN_MEDIA_TRANSPORT:-file-url}"
GEN_ALLOWED_LOCAL_MEDIA_PATH="${GEN_ALLOWED_LOCAL_MEDIA_PATH:-${LMUData}}"
GEN_MIN_IMAGE_PIXELS="${GEN_MIN_IMAGE_PIXELS:-1003520}"
GEN_MAX_IMAGE_PIXELS="${GEN_MAX_IMAGE_PIXELS:-12845056}"
GEN_MAX_TOKENS="${GEN_MAX_TOKENS:-4096}"
GEN_TEMPERATURE="${GEN_TEMPERATURE:-0.6}"
GEN_TOP_P="${GEN_TOP_P:-1.0}"
GEN_TOP_K="${GEN_TOP_K:--1}"
GEN_PRESENCE_PENALTY="${GEN_PRESENCE_PENALTY:-0.0}"
GEN_REPETITION_PENALTY="${GEN_REPETITION_PENALTY:-1.0}"

JUDGE_MODEL_SOURCE="${JUDGE_MODEL_SOURCE:-Qwen/Qwen3-32B}"
JUDGE_MODEL_REVISION="${JUDGE_MODEL_REVISION:-9216db5781bf21249d130ec9da846c4624c16137}"
JUDGE_MODEL="${JUDGE_MODEL:-${FINAL25_MODEL_ROOT}/qwen3-32b-judge}"
JUDGE_SERVED_MODEL_NAME="${JUDGE_SERVED_MODEL_NAME:-qwen3-32b-judge}"
JUDGE_GPU_MEMORY_UTILIZATION="${JUDGE_GPU_MEMORY_UTILIZATION:-0.90}"
JUDGE_MAX_MODEL_LEN="${JUDGE_MAX_MODEL_LEN:-8192}"
JUDGE_MAX_NUM_SEQS="${JUDGE_MAX_NUM_SEQS:-128}"
JUDGE_MAX_NUM_BATCHED_TOKENS="${JUDGE_MAX_NUM_BATCHED_TOKENS:-32768}"
JUDGE_API_PARALLELISM="${JUDGE_API_PARALLELISM:-64}"
JUDGE_API_BATCH_SIZE="${JUDGE_API_BATCH_SIZE:-64}"
JUDGE_API_BATCHES_PER_ENDPOINT="${JUDGE_API_BATCHES_PER_ENDPOINT:-1}"
JUDGE_API_MAX_BATCH_CHARS="${JUDGE_API_MAX_BATCH_CHARS:-200000}"
JUDGE_API_ENDPOINT_FAILURE_THRESHOLD="${JUDGE_API_ENDPOINT_FAILURE_THRESHOLD:-3}"
JUDGE_API_ENDPOINT_COOLDOWN_SECONDS="${JUDGE_API_ENDPOINT_COOLDOWN_SECONDS:-30}"
JUDGE_CACHE_CONTRACT_VERSION="${JUDGE_CACHE_CONTRACT_VERSION:-trace-persistent-judge-v2}"
EXTRACTION_API_PARALLELISM="${EXTRACTION_API_PARALLELISM:-32}"
EXTRACTION_API_QUEUE_CAPACITY="${EXTRACTION_API_QUEUE_CAPACITY:-16}"
EXTRACTION_API_RETRY_BASE_DELAY="${EXTRACTION_API_RETRY_BASE_DELAY:-0.5}"
EXTRACTION_JUDGE_MAX_TOKENS="${EXTRACTION_JUDGE_MAX_TOKENS:-256}"
DIRECT_SCORE_WORKERS="${DIRECT_SCORE_WORKERS:-2}"
DIRECT_EVAL_NPROC="${DIRECT_EVAL_NPROC:-12}"
MME_MODEL_CONCURRENCY="${MME_MODEL_CONCURRENCY:-2}"

VLLM_CPU_THREADS_PER_PROCESS="${VLLM_CPU_THREADS_PER_PROCESS:-8}"
VLLM_CPU_AFFINITY_GROUPS="${VLLM_CPU_AFFINITY_GROUPS:-0-19;20-39;40-59;60-79;96-115;116-135;136-155;156-175}"
EVAL_CPUSET="${EVAL_CPUSET:-80-95,176-183}"
HF_ARCHIVE_CPUSET="${HF_ARCHIVE_CPUSET:-184-191}"

RUN_HF_ARCHIVE="${RUN_HF_ARCHIVE:-1}"
HF_ARCHIVE_LOCAL_ONLY="${HF_ARCHIVE_LOCAL_ONLY:-0}"
HF_ARCHIVE_REPO_ID="${HF_ARCHIVE_REPO_ID:-maveryn/trace-final25-eval-runs}"
HF_ARCHIVE_REVISION="${HF_ARCHIVE_REVISION:-main}"
HF_ARCHIVE_TOKEN_FILE="${HF_ARCHIVE_TOKEN_FILE:-${REPO_ROOT}/hf-token.txt}"
HF_ARCHIVE_SPOOL_ROOT="${HF_ARCHIVE_SPOOL_ROOT:-${CAMPAIGN_ROOT}/hf_archive}"
HF_ARCHIVE_BATCH_SIZE="${HF_ARCHIVE_BATCH_SIZE:-48}"
HF_ARCHIVE_UPLOAD_THREADS="${HF_ARCHIVE_UPLOAD_THREADS:-8}"
HF_ARCHIVE_POLL_SECONDS="${HF_ARCHIVE_POLL_SECONDS:-30}"
HF_ARCHIVE_INIT_ATTEMPTS="${HF_ARCHIVE_INIT_ATTEMPTS:-5}"
HF_ARCHIVE_INIT_RETRY_SECONDS="${HF_ARCHIVE_INIT_RETRY_SECONDS:-10}"
HF_ARCHIVE_ALLOW_CACHED_PRIVATE_INIT="${HF_ARCHIVE_ALLOW_CACHED_PRIVATE_INIT:-0}"

RUN_REUSE="${RUN_REUSE:-0}"
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
  "${MODEL_QWEN25VL3B_BASE_PATH:-${FINAL25_MODEL_ROOT}/qwen25vl3b-base}"
  "${MODEL_TRACE_QWEN25VL3B_PATH:-${TMP_ROOT}/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500}"
  "${MODEL_QWEN25VL7B_BASE_PATH:-${FINAL25_MODEL_ROOT}/qwen25vl7b-base}"
  "${MODEL_TRACE_QWEN25VL7B_PATH:-${TMP_ROOT}/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500}"
  "${MODEL_GAME_RL_PATH:-${FINAL25_MODEL_ROOT}/game-rl-qwen25vl7b}"
  "${MODEL_SPHINX_PATH:-${FINAL25_MODEL_ROOT}/sphinx-qwen7b-500}"
  "${MODEL_PCGRPO_PATH:-${FINAL25_MODEL_ROOT}/pcgrpo-qwen25vl7b-jigsaw-care}"
  "${MODEL_VERO_PATH:-${FINAL25_MODEL_ROOT}/vero-qwen25-7b}"
)

model_metadata_from_marker() {
  local model_path="$1"
  local field="$2"
  local fallback="$3"
  local marker="${model_path}/.trace_model_revision.json"
  if [[ -f "${marker}" ]]; then
    "${PYTHON_BIN}" -c \
      'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]])' \
      "${marker}" "${field}"
  else
    printf '%s\n' "${fallback}"
  fi
}

MODEL_SOURCES=(
  "$(model_metadata_from_marker "${MODEL_PATHS[0]}" source "${MODEL_QWEN25VL3B_BASE_SOURCE:-Qwen/Qwen2.5-VL-3B-Instruct}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[1]}" source "${MODEL_TRACE_QWEN25VL3B_SOURCE:-trace-merged-checkpoint}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[2]}" source "${MODEL_QWEN25VL7B_BASE_SOURCE:-Qwen/Qwen2.5-VL-7B-Instruct}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[3]}" source "${MODEL_TRACE_QWEN25VL7B_SOURCE:-trace-merged-checkpoint}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[4]}" source "${MODEL_GAME_RL_SOURCE:-OpenMOSS-Team/Game-RL-Qwen2.5-VL-7B}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[5]}" source "${MODEL_SPHINX_SOURCE:-xashru/sphinx_qwen7b_500}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[6]}" source "${MODEL_PCGRPO_SOURCE:-armenjeddi/PCGRPO-Qwen2.5-VL-7B-Jigsaw-with-curriculum-with-grpo-care}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[7]}" source "${MODEL_VERO_SOURCE:-zlab-princeton/Vero-Qwen25-7B}")"
)

MODEL_REVISIONS=(
  "$(model_metadata_from_marker "${MODEL_PATHS[0]}" immutable_revision "${MODEL_QWEN25VL3B_BASE_REVISION:-66285546d2b821cf421d4f5eb2576359d3770cd3}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[1]}" immutable_revision "${MODEL_TRACE_QWEN25VL3B_REVISION:-sha256set:814bf037a6c3faa56aac4f20cb71d957a62065daff40186b271c76161dde53eb}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[2]}" immutable_revision "${MODEL_QWEN25VL7B_BASE_REVISION:-cc594898137f460bfe9f0759e9844b3ce807cfb5}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[3]}" immutable_revision "${MODEL_TRACE_QWEN25VL7B_REVISION:-sha256set:671693323a0b051794a6e8587e2412cbbff81802f4e3ff9032051a77f52d7fcb}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[4]}" immutable_revision "${MODEL_GAME_RL_REVISION:-205b5934ce70504cfd6ae26b16f705d0b98b9306}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[5]}" immutable_revision "${MODEL_SPHINX_REVISION:-6ffefb03d5cb0767683bfb42a084ea86b707ef9a}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[6]}" immutable_revision "${MODEL_PCGRPO_REVISION:-921bbced4176f5d362e98c843a57656c5d78dad7}")"
  "$(model_metadata_from_marker "${MODEL_PATHS[7]}" immutable_revision "${MODEL_VERO_REVISION:-180e84be5acb2aa887cf51015b84b6a6e453ee90}")"
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

# Opt-in single-model mode. The default arrays above remain unchanged for the
# frozen eight-model campaign.
if [[ -n "${SINGLE_MODEL_SLUG:-}${SINGLE_MODEL_PATH:-}${SINGLE_MODEL_REVISION:-}${SINGLE_MODEL_SOURCE:-}${SINGLE_MODEL_LABEL:-}" ]]; then
  : "${SINGLE_MODEL_SLUG:?Set SINGLE_MODEL_SLUG for single-model mode.}"
  : "${SINGLE_MODEL_PATH:?Set SINGLE_MODEL_PATH for single-model mode.}"
  : "${SINGLE_MODEL_REVISION:?Set SINGLE_MODEL_REVISION for single-model mode.}"
  : "${SINGLE_MODEL_SOURCE:?Set SINGLE_MODEL_SOURCE for single-model mode.}"
  : "${SINGLE_MODEL_LABEL:?Set SINGLE_MODEL_LABEL for single-model mode.}"
  MODEL_SLUGS=("${SINGLE_MODEL_SLUG}")
  MODEL_PATHS=("${SINGLE_MODEL_PATH}")
  MODEL_SOURCES=("${SINGLE_MODEL_SOURCE}")
  MODEL_REVISIONS=("${SINGLE_MODEL_REVISION}")
  MODEL_LABELS=("${SINGLE_MODEL_LABEL}")
fi

compute_final25_code_hash() {
  {
    find "${REPO_ROOT}/scripts" -maxdepth 1 -type f \
      \( -name 'benchmark_queue_lib.py' \
      -o -name 'trace_final25_contract.py' \
      -o -name 'run_external_benchmark_*queue.py' \
      -o -name 'run_llm_extracted_benchmark_score_queue.py' \
      -o -name 'run_mme_reasoning_eval.py' \
      -o -name 'final25_*.py' \
      -o -name 'start_vllm_endpoint_pool.sh' \
      -o -name 'stop_vllm_endpoint_pool.sh' \
      -o -name 'run_trace_final25_temp06_3seed_8models.sh' \) -print
    find "${REPO_ROOT}/external/VLMEvalKit/vlmeval" -type f -name '*.py' -print
    find "${REPO_ROOT}/external/VLMEvalKit/scripts" -maxdepth 1 -type f \
      -name 'batched_*.py' -print
    printf '%s\n' "${REPO_ROOT}/evaluation/final25/suite.v1.json"
  } | LC_ALL=C sort | while IFS= read -r path; do
    sha256sum "${path}"
  done | sha256sum | awk '{print $1}'
}

compute_campaign_config_hash() {
  {
    printf '%s\n' \
      "run_tag=${RUN_TAG}" \
      "suite=${SUITE}" \
      "seeds=${SEEDS[*]}" \
      "gpu_groups=${GPU_GROUPS}" \
      "generation=${GEN_TEMPERATURE},${GEN_TOP_P},${GEN_TOP_K},${GEN_PRESENCE_PENALTY},${GEN_REPETITION_PENALTY},${GEN_MAX_TOKENS}" \
      "generation_media=${GEN_MEDIA_TRANSPORT},${GEN_ALLOWED_LOCAL_MEDIA_PATH},${GEN_MIN_IMAGE_PIXELS},${GEN_MAX_IMAGE_PIXELS}" \
      "generation_pipeline=${GEN_PARALLELISM_PER_ENDPOINT},${GEN_PREPARATION_WORKERS},${GEN_QUEUE_CAPACITY},${GEN_PERSISTENCE_WORKERS},${GEN_FINALIZATION_WORKERS}" \
      "judge=${JUDGE_MODEL_SOURCE},${JUDGE_MODEL_REVISION},${JUDGE_MODEL},${JUDGE_SERVED_MODEL_NAME},${JUDGE_API_PARALLELISM},${JUDGE_API_BATCH_SIZE},${JUDGE_API_BATCHES_PER_ENDPOINT},${JUDGE_API_MAX_BATCH_CHARS},${JUDGE_API_ENDPOINT_FAILURE_THRESHOLD},${JUDGE_API_ENDPOINT_COOLDOWN_SECONDS},${JUDGE_CACHE_CONTRACT_VERSION}" \
      "extraction_pipeline=${EXTRACTION_API_PARALLELISM},${EXTRACTION_API_QUEUE_CAPACITY},${EXTRACTION_API_RETRY_BASE_DELAY}" \
      "dataset_revision=${TRACE_FINAL25_DATASET_REVISION}" \
      "code_hash=${TRACE_FINAL25_CODE_HASH}"
    printf 'extraction_max_tokens=%s\n' "${EXTRACTION_JUDGE_MAX_TOKENS}"
    printf 'model_slug=%s\n' "${MODEL_SLUGS[@]}"
    printf 'model_path=%s\n' "${MODEL_PATHS[@]}"
    printf 'model_source=%s\n' "${MODEL_SOURCES[@]}"
    printf 'model_revision=%s\n' "${MODEL_REVISIONS[@]}"
  } | sha256sum | awk '{print $1}'
}

TRACE_GIT_COMMIT="${TRACE_GIT_COMMIT:-$(git -C "${REPO_ROOT}" rev-parse HEAD)}"
TRACE_VLMEVALKIT_GIT_COMMIT="${TRACE_VLMEVALKIT_GIT_COMMIT:-$(git -C "${REPO_ROOT}/external/VLMEvalKit" rev-parse HEAD)}"
TRACE_FINAL25_CODE_HASH="${TRACE_FINAL25_CODE_HASH:-$(compute_final25_code_hash)}"
TRACE_FINAL25_DATASET_SNAPSHOT="${TRACE_FINAL25_DATASET_SNAPSHOT:-$(
  "${PYTHON_BIN}" -c \
    'import sys; from final25_media_contract import load_dataset_manifest; p=load_dataset_manifest(__import__("pathlib").Path(sys.argv[1])); print(p["view_snapshot_sha256"][sys.argv[2]])' \
    "${FINAL25_DATASET_MANIFEST}" "${SUITE_DATASET_VIEW}"
)}"
TRACE_FINAL25_DATASET_REVISION="${TRACE_FINAL25_DATASET_REVISION:-trace-final25-datasets-v2:${TRACE_FINAL25_DATASET_SNAPSHOT}}"
TRACE_FINAL25_CAMPAIGN_CONFIG_HASH="${TRACE_FINAL25_CAMPAIGN_CONFIG_HASH:-$(compute_campaign_config_hash)}"
TRACE_FINAL25_MODEL_REVISIONS_JSON="$(
  "${PYTHON_BIN}" -c \
    'import json,sys; n=int(sys.argv[1]); print(json.dumps(dict(zip(sys.argv[2:2+n], sys.argv[2+n:])) ,sort_keys=True))' \
    "${#MODEL_SLUGS[@]}" "${MODEL_SLUGS[@]}" "${MODEL_REVISIONS[@]}"
)"
TRACE_FINAL25_MODEL_SOURCES_JSON="$(
  "${PYTHON_BIN}" -c \
    'import json,sys; n=int(sys.argv[1]); print(json.dumps(dict(zip(sys.argv[2:2+n], sys.argv[2+n:])), sort_keys=True))' \
    "${#MODEL_SLUGS[@]}" "${MODEL_SLUGS[@]}" "${MODEL_SOURCES[@]}"
)"

export TRACE_GIT_COMMIT TRACE_VLMEVALKIT_GIT_COMMIT
export TRACE_FINAL25_CAMPAIGN_CONFIG_HASH TRACE_FINAL25_DATASET_REVISION TRACE_FINAL25_CODE_HASH
export TRACE_FINAL25_DATASET_SNAPSHOT FINAL25_DATASET_MANIFEST
export TRACE_FINAL25_MODEL_REVISIONS_JSON TRACE_FINAL25_MODEL_SOURCES_JSON
if [[ "${RUN_HF_ARCHIVE}" == "1" ]]; then
  export TRACE_FINAL25_HF_SPOOL_ROOT="${HF_ARCHIVE_SPOOL_ROOT}"
  export TRACE_FINAL25_RUN_ID="${RUN_TAG}"
  export TRACE_FINAL25_HF_REPO_ID="${HF_ARCHIVE_REPO_ID}"
  export TRACE_FINAL25_HF_REVISION="${HF_ARCHIVE_REVISION}"
else
  unset TRACE_FINAL25_HF_SPOOL_ROOT
fi

mkdir -p \
  "${CAMPAIGN_ROOT}" "${LOG_ROOT}" "${RESULTS_ROOT}" "${TMP_ROOT}/tmp" \
  "${HF_ARCHIVE_SPOOL_ROOT}"
export TMPDIR="${TMPDIR:-${TMP_ROOT}/tmp}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

current_pid_file=""
archive_pid=""
background_pids=()

eval_python() {
  if [[ -n "${EVAL_CPUSET}" && "${EVAL_CPUSET}" != "none" ]]; then
    taskset --cpu-list "${EVAL_CPUSET}" "${PYTHON_BIN}" "$@"
  else
    "${PYTHON_BIN}" "$@"
  fi
}

archive_python() {
  if [[ -n "${HF_ARCHIVE_CPUSET}" && "${HF_ARCHIVE_CPUSET}" != "none" ]]; then
    taskset --cpu-list "${HF_ARCHIVE_CPUSET}" "${PYTHON_BIN}" \
      "${REPO_ROOT}/scripts/final25_hf_archive.py" "$@"
  else
    "${PYTHON_BIN}" "${REPO_ROOT}/scripts/final25_hf_archive.py" "$@"
  fi
}

archive_args() {
  local -n output_array="$1"
  output_array=(
    --spool-root "${HF_ARCHIVE_SPOOL_ROOT}"
    --repo-id "${HF_ARCHIVE_REPO_ID}"
    --revision "${HF_ARCHIVE_REVISION}"
    --token-file "${HF_ARCHIVE_TOKEN_FILE}"
    --batch-size "${HF_ARCHIVE_BATCH_SIZE}"
    --upload-threads "${HF_ARCHIVE_UPLOAD_THREADS}"
  )
}

archive_coverage_complete() {
  local stage="${1:-}"
  local model_slug="${2:-}"
  local expected_seed="${3:-}"
  local expected_benchmark="${4:-}"
  if [[ "${RUN_HF_ARCHIVE}" != "1" ]]; then
    return 1
  fi
  if [[ "${HF_ARCHIVE_LOCAL_ONLY}" == "1" ]]; then
    return 0
  fi
  local -a args coverage_args=(
    --expect-run-id "${RUN_TAG}"
    --expect-campaign-config-hash "${TRACE_FINAL25_CAMPAIGN_CONFIG_HASH}"
    --expect-dataset-revision "${TRACE_FINAL25_DATASET_REVISION}"
  )
  archive_args args
  local slug seed
  if [[ -n "${expected_benchmark}" ]]; then
    coverage_args+=(--expect-benchmark "${expected_benchmark}")
  else
    coverage_args+=(--expect-final25)
  fi
  if [[ -n "${model_slug}" ]]; then
    coverage_args+=(--expect-model-slug "${model_slug}")
  else
    for slug in "${MODEL_SLUGS[@]}"; do
      coverage_args+=(--expect-model-slug "${slug}")
    done
  fi
  if [[ -n "${expected_seed}" ]]; then
    coverage_args+=(--expect-seed "${expected_seed}")
  else
    for seed in "${SEEDS[@]}"; do
      coverage_args+=(--expect-seed "${seed}")
    done
  fi
  if [[ -n "${stage}" ]]; then
    coverage_args+=(--expect-stage "${stage}")
  fi
  archive_python "${args[@]}" coverage "${coverage_args[@]}" >/dev/null 2>&1 || return 1
  if [[ "${SUITE}" == "all26" && -z "${expected_benchmark}" ]]; then
    local -a mmvp_coverage_args=()
    local value
    for value in "${coverage_args[@]}"; do
      if [[ "${value}" == "--expect-final25" ]]; then
        mmvp_coverage_args+=(--expect-benchmark mmvp)
      else
        mmvp_coverage_args+=("${value}")
      fi
    done
    archive_python "${args[@]}" coverage "${mmvp_coverage_args[@]}" >/dev/null 2>&1
  fi
}

cached_private_archive_attestation() {
  local campaign_log="${LOG_ROOT}/campaign.log"
  local ledger="${HF_ARCHIVE_SPOOL_ROOT}/ledger.sqlite3"
  [[ -f "${campaign_log}" && -f "${ledger}" ]] || return 1
  "${PYTHON_BIN}" - "${campaign_log}" "${ledger}" "${HF_ARCHIVE_REPO_ID}" <<'PY'
import json
import sqlite3
import sys
from pathlib import Path

log_path, ledger_path, repo_id = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
attested = False
for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
    if not line.lstrip().startswith("{"):
        continue
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        continue
    if record.get("private") is True and record.get("repo_id") == repo_id:
        attested = True
        break
if not attested:
    raise SystemExit(1)
with sqlite3.connect(ledger_path) as connection:
    uploaded = connection.execute(
        "SELECT COUNT(*) FROM slices WHERE status='uploaded'"
    ).fetchone()[0]
raise SystemExit(0 if uploaded > 0 else 1)
PY
}

start_archive_daemon() {
  if [[ "${RUN_HF_ARCHIVE}" != "1" ]]; then
    echo "[archive:disabled] RUN_HF_ARCHIVE=${RUN_HF_ARCHIVE}"
    return
  fi
  if [[ "${HF_ARCHIVE_LOCAL_ONLY}" == "1" ]]; then
    echo "[archive:local-only] remote init/upload disabled spool=${HF_ARCHIVE_SPOOL_ROOT}"
    return
  fi
  if [[ ! -f "${HF_ARCHIVE_TOKEN_FILE}" ]]; then
    echo "[fatal] missing HF archive token file: ${HF_ARCHIVE_TOKEN_FILE}" >&2
    exit 1
  fi
  local -a args
  archive_args args
  echo "[archive:init] repo=${HF_ARCHIVE_REPO_ID} revision=${HF_ARCHIVE_REVISION} spool=${HF_ARCHIVE_SPOOL_ROOT}"
  local attempt
  for ((attempt = 1; attempt <= HF_ARCHIVE_INIT_ATTEMPTS; attempt++)); do
    if archive_python "${args[@]}" init 2>&1 | tee -a "${LOG_ROOT}/hf_archive_init.log"; then
      break
    fi
    if [[ "${attempt}" -ge "${HF_ARCHIVE_INIT_ATTEMPTS}" ]]; then
      if [[ "${HF_ARCHIVE_ALLOW_CACHED_PRIVATE_INIT}" == "1" ]] \
        && cached_private_archive_attestation; then
        echo "[archive:init-cached] live HF check unavailable; using prior private attestation and uploaded ledger state" >&2
        break
      fi
      echo "[fatal] HF archive initialization failed after ${attempt} attempts" >&2
      return 1
    fi
    echo "[archive:init-retry] attempt=${attempt}/${HF_ARCHIVE_INIT_ATTEMPTS} sleep=${HF_ARCHIVE_INIT_RETRY_SECONDS}s" >&2
    sleep "${HF_ARCHIVE_INIT_RETRY_SECONDS}"
  done
  local -a daemon_command=("${PYTHON_BIN}" "${REPO_ROOT}/scripts/final25_hf_archive.py")
  if [[ -n "${HF_ARCHIVE_CPUSET}" && "${HF_ARCHIVE_CPUSET}" != "none" ]]; then
    daemon_command=(taskset --cpu-list "${HF_ARCHIVE_CPUSET}" "${daemon_command[@]}")
  fi
  "${daemon_command[@]}" "${args[@]}" daemon --poll-seconds "${HF_ARCHIVE_POLL_SECONDS}" \
    >> "${LOG_ROOT}/hf_archive_daemon.log" 2>&1 &
  archive_pid="$!"
  echo "[archive:started] pid=${archive_pid} log=${LOG_ROOT}/hf_archive_daemon.log"
}

stop_archive_daemon() {
  if [[ -z "${archive_pid}" ]]; then
    return
  fi
  local pid="${archive_pid}"
  archive_pid=""
  if kill -0 "${pid}" 2>/dev/null; then
    kill -TERM "${pid}" 2>/dev/null || true
  fi
  wait "${pid}"
}

finalize_archive() {
  if [[ "${RUN_HF_ARCHIVE}" != "1" ]]; then
    return
  fi
  if [[ "${HF_ARCHIVE_LOCAL_ONLY}" == "1" ]]; then
    local descriptor_count
    descriptor_count="$(find "${HF_ARCHIVE_SPOOL_ROOT}/ready" -type f -name '*.ready.json' 2>/dev/null | wc -l)"
    echo "[archive:local-only] descriptors=${descriptor_count} spool=${HF_ARCHIVE_SPOOL_ROOT} remote_flush=deferred"
    return
  fi
  local daemon_status=0
  if ! stop_archive_daemon; then
    daemon_status=1
    echo "[archive:warning] daemon exited unsuccessfully; running final flush and verification" >&2
  fi
  local -a args
  archive_args args
  echo "[archive:flush]"
  archive_python "${args[@]}" flush 2>&1 | tee "${LOG_ROOT}/hf_archive_flush.log"
  echo "[archive:verify]"
  local -a coverage_args=(
    --expect-run-id "${RUN_TAG}"
    --expect-final25
    --expect-campaign-config-hash "${TRACE_FINAL25_CAMPAIGN_CONFIG_HASH}"
    --expect-dataset-revision "${TRACE_FINAL25_DATASET_REVISION}"
  )
  local slug seed
  for slug in "${MODEL_SLUGS[@]}"; do
    coverage_args+=(--expect-model-slug "${slug}")
  done
  for seed in "${SEEDS[@]}"; do
    coverage_args+=(--expect-seed "${seed}")
  done
  archive_python "${args[@]}" verify "${coverage_args[@]}" \
    2>&1 | tee "${LOG_ROOT}/hf_archive_verify.log"
  if [[ "${SUITE}" == "all26" ]]; then
    local -a mmvp_coverage_args=()
    local value
    for value in "${coverage_args[@]}"; do
      if [[ "${value}" == "--expect-final25" ]]; then
        mmvp_coverage_args+=(--expect-benchmark mmvp)
      else
        mmvp_coverage_args+=("${value}")
      fi
    done
    archive_python "${args[@]}" verify "${mmvp_coverage_args[@]}" \
      2>&1 | tee "${LOG_ROOT}/hf_archive_verify_mmvp.log"
  fi
  return "${daemon_status}"
}

track_background_pid() {
  background_pids+=("$1")
}

forget_background_pid() {
  local forgotten="$1"
  local -a remaining=()
  local pid
  for pid in "${background_pids[@]}"; do
    if [[ "${pid}" != "${forgotten}" ]]; then
      remaining+=("${pid}")
    fi
  done
  background_pids=("${remaining[@]}")
}

wait_for_background_jobs() {
  local status=0
  local pid
  for pid in "$@"; do
    if ! wait "${pid}"; then
      status=1
    fi
    forget_background_pid "${pid}"
  done
  return "${status}"
}

terminate_background_jobs() {
  terminate_process_tree() {
    local parent="$1"
    local signal="$2"
    local child
    while read -r child; do
      [[ -n "${child}" ]] && terminate_process_tree "${child}" "${signal}"
    done < <(pgrep -P "${parent}" 2>/dev/null || true)
    kill "-${signal}" "${parent}" 2>/dev/null || true
  }
  local pid
  for pid in "${background_pids[@]}"; do
    terminate_process_tree "${pid}" TERM
  done
  sleep 2
  for pid in "${background_pids[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      terminate_process_tree "${pid}" KILL
    fi
  done
  for pid in "${background_pids[@]}"; do
    wait "${pid}" 2>/dev/null || true
  done
  background_pids=()
}

cleanup_current_pool() {
  if [[ -n "${current_pid_file}" && -f "${current_pid_file}" ]]; then
    PID_FILE="${current_pid_file}" bash "${REPO_ROOT}/scripts/stop_vllm_endpoint_pool.sh" || true
  fi
}

cleanup_services() {
  local status=$?
  set +e
  terminate_background_jobs
  cleanup_current_pool
  stop_archive_daemon
  return "${status}"
}
trap cleanup_services EXIT

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
  PYTHON_BIN="${PYTHON_BIN}" \
  CPU_THREADS_PER_PROCESS="${VLLM_CPU_THREADS_PER_PROCESS}" \
  CPU_AFFINITY_GROUPS="${VLLM_CPU_AFFINITY_GROUPS}" \
  ALLOWED_LOCAL_MEDIA_PATH="${GEN_ALLOWED_LOCAL_MEDIA_PATH}" \
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
  local -a verify_args=()
  local i
  if [[ "${#MODEL_SLUGS[@]}" -ne "${#MODEL_PATHS[@]}" \
    || "${#MODEL_SLUGS[@]}" -ne "${#MODEL_REVISIONS[@]}" \
    || "${#MODEL_SLUGS[@]}" -ne "${#MODEL_SOURCES[@]}" \
    || "${#MODEL_SLUGS[@]}" -ne "${#MODEL_LABELS[@]}" ]]; then
    echo "[fatal] model slug/path/revision/source/label arrays have different lengths" >&2
    exit 1
  fi
  for i in "${!MODEL_SLUGS[@]}"; do
    verify_args+=(--entry "${MODEL_SLUGS[$i]}=${MODEL_PATHS[$i]}=${MODEL_REVISIONS[$i]}")
  done
  if [[ "${RUN_SCORING}" == "1" ]]; then
    verify_args+=(--entry "qwen3-32b-judge=${JUDGE_MODEL}=${JUDGE_MODEL_REVISION}")
  fi
  if [[ "${MODEL_VERIFY_DEEP}" == "1" ]]; then
    verify_args+=(--deep)
  fi
  eval_python "${REPO_ROOT}/scripts/prepare_trace_final25_models.py" verify "${verify_args[@]}"
}

validate_eval_environment() {
  bash "${REPO_ROOT}/scripts/setup_trace_final25_eval_env.sh" --verify-only
  if [[ "$(git -C "${REPO_ROOT}/external/VLMEvalKit" rev-parse HEAD)" != "${EXPECTED_VLMEVALKIT_COMMIT}" ]]; then
    echo "[fatal] unexpected VLMEvalKit commit" >&2
    exit 1
  fi
  eval_python "${REPO_ROOT}/scripts/prepare_trace_final25_datasets.py" \
    --view "${SUITE_DATASET_VIEW}" \
    --lmu-root "${LMUData}" \
    --manifest "${FINAL25_DATASET_MANIFEST}" \
    --verify-only
  validate_models
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
  eval_python "${REPO_ROOT}/scripts/reuse_trace_final25_generation_rows.py" \
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
  local model="$2"
  local revision="$3"
  eval_python "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" \
    --phase generation \
    --suite "${SUITE}" \
    --model-slug "${slug}" \
    --model-entry "${slug}=${model}=${revision}" \
    --seeds "${SEEDS[@]}"
}

generation_complete_for_model_seed() {
  local slug="$1"
  local seed="$2"
  local model="$3"
  local revision="$4"
  eval_python "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" \
    --phase generation \
    --suite "${SUITE}" \
    --model-slug "${slug}" \
    --model-entry "${slug}=${model}=${revision}" \
    --seeds "${seed}"
}

run_generation() {
  local -a api_args
  local -a generation_finalize_pids=()
  build_endpoint_args "${GEN_PORT_START}" --api-base api_args
  for i in "${!MODEL_SLUGS[@]}"; do
    local slug="${MODEL_SLUGS[$i]}"
    local model="${MODEL_PATHS[$i]}"
    local revision="${MODEL_REVISIONS[$i]}"
    if generation_complete_for_model "${slug}" "${model}" "${revision}" \
      && { [[ "${RUN_HF_ARCHIVE}" != "1" ]] || archive_coverage_complete generation "${slug}"; }; then
      echo "[generation:skip-model] slug=${slug} all seeds complete"
      continue
    fi
    echo "[generation:model-start] slug=${slug} model=${model}"
    start_pool \
      "${model}" "${slug}" "${GEN_PORT_START}" "${LOG_ROOT}/vllm_generation_${slug}" \
      "${GEN_GPU_MEMORY_UTILIZATION}" "${GEN_MAX_MODEL_LEN}" "${GEN_MAX_NUM_SEQS}" "${GEN_MAX_NUM_BATCHED_TOKENS}"
    for seed in "${SEEDS[@]}"; do
      if generation_complete_for_model_seed "${slug}" "${seed}" "${model}" "${revision}" \
        && { [[ "${RUN_HF_ARCHIVE}" != "1" ]] || archive_coverage_complete generation "${slug}" "${seed}"; }; then
        echo "[generation:skip-seed] slug=${slug} seed=${seed} complete"
        continue
      fi
      local run_root="${CAMPAIGN_ROOT}/seed_${seed}/runs"
      mkdir -p "${run_root}"
      echo "[generation:start] slug=${slug} seed=${seed} run_root=${run_root}"
      eval_python "${REPO_ROOT}/scripts/run_external_benchmark_generation_api_queue.py" \
        --model "${model}" \
        --model-slug "${slug}" \
        --api-model "${slug}" \
        "${api_args[@]}" \
        --parallelism-per-endpoint "${GEN_PARALLELISM_PER_ENDPOINT}" \
        --endpoint-failure-threshold "${GEN_ENDPOINT_FAILURE_THRESHOLD}" \
        --preparation-workers "${GEN_PREPARATION_WORKERS}" \
        --queue-capacity "${GEN_QUEUE_CAPACITY}" \
        --persistence-workers "${GEN_PERSISTENCE_WORKERS}" \
        --finalization-workers "${GEN_FINALIZATION_WORKERS}" \
        --media-transport "${GEN_MEDIA_TRANSPORT}" \
        --allowed-local-media-path "${GEN_ALLOWED_LOCAL_MEDIA_PATH}" \
        --dataset-manifest "${FINAL25_DATASET_MANIFEST}" \
        --dataset-manifest-view "${SUITE_DATASET_VIEW}" \
        --min-image-pixels "${GEN_MIN_IMAGE_PIXELS}" \
        --max-image-pixels "${GEN_MAX_IMAGE_PIXELS}" \
        --run-set "${SUITE_RUN_SET}" \
        --run-root "${run_root}" \
        --temperature "${GEN_TEMPERATURE}" \
        --top-p "${GEN_TOP_P}" \
        --top-k "${GEN_TOP_K}" \
        --presence-penalty "${GEN_PRESENCE_PENALTY}" \
        --repetition-penalty "${GEN_REPETITION_PENALTY}" \
        --max-tokens "${GEN_MAX_TOKENS}" \
        --seed "${seed}" \
        --compact-prediction-tables \
        --defer-finalization \
        2>&1 | tee "${LOG_ROOT}/generation_${slug}_seed${seed}.log"

      echo "[generation:finalize-async] slug=${slug} seed=${seed}"
      (
        set -o pipefail
        eval_python "${REPO_ROOT}/scripts/run_external_benchmark_generation_api_queue.py" \
          --model "${model}" \
          --model-slug "${slug}" \
          --api-model "${slug}" \
          --finalize-only \
          --finalization-workers "${GEN_FINALIZATION_WORKERS}" \
          --preparation-workers "${GEN_PREPARATION_WORKERS}" \
          --queue-capacity "${GEN_QUEUE_CAPACITY}" \
          --persistence-workers "${GEN_PERSISTENCE_WORKERS}" \
          --media-transport "${GEN_MEDIA_TRANSPORT}" \
          --allowed-local-media-path "${GEN_ALLOWED_LOCAL_MEDIA_PATH}" \
          --dataset-manifest "${FINAL25_DATASET_MANIFEST}" \
          --dataset-manifest-view "${SUITE_DATASET_VIEW}" \
          --min-image-pixels "${GEN_MIN_IMAGE_PIXELS}" \
          --max-image-pixels "${GEN_MAX_IMAGE_PIXELS}" \
          --run-set "${SUITE_RUN_SET}" \
          --run-root "${run_root}" \
          --temperature "${GEN_TEMPERATURE}" \
          --top-p "${GEN_TOP_P}" \
          --top-k "${GEN_TOP_K}" \
          --presence-penalty "${GEN_PRESENCE_PENALTY}" \
          --repetition-penalty "${GEN_REPETITION_PENALTY}" \
          --max-tokens "${GEN_MAX_TOKENS}" \
          --seed "${seed}" \
          --compact-prediction-tables \
          2>&1 | tee "${LOG_ROOT}/generation_finalize_${slug}_seed${seed}.log"
      ) &
      local finalize_pid="$!"
      generation_finalize_pids+=("${finalize_pid}")
      track_background_pid "${finalize_pid}"
    done
    stop_pool
    echo "[generation:model-done] slug=${slug}"
  done

  if [[ "${#generation_finalize_pids[@]}" -gt 0 ]] \
    && ! wait_for_background_jobs "${generation_finalize_pids[@]}"; then
    echo "[generation:error] one or more asynchronous finalizers failed" >&2
    return 1
  fi

  local verify_args=()
  for i in "${!MODEL_SLUGS[@]}"; do
    verify_args+=(
      --model-slug "${MODEL_SLUGS[$i]}"
      --model-entry "${MODEL_SLUGS[$i]}=${MODEL_PATHS[$i]}=${MODEL_REVISIONS[$i]}"
    )
  done
  eval_python "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" --phase generation --suite "${SUITE}" \
    "${verify_args[@]}" --seeds "${SEEDS[@]}"
}

run_mme_scoring() {
  local -a judge_args
  build_endpoint_args "${JUDGE_PORT_START}" --judge-api-base judge_args
  for seed in "${SEEDS[@]}"; do
    local run_root="${CAMPAIGN_ROOT}/seed_${seed}/runs"
    local benchmark_root="${CAMPAIGN_ROOT}/seed_${seed}/benchmark"
    local -a pair_pids=()
    for i in "${!MODEL_SLUGS[@]}"; do
      local slug="${MODEL_SLUGS[$i]}"
      local model="${MODEL_PATHS[$i]}"
      local score_file="${benchmark_root}/mme_reasoning/${slug}/vlmevalkit_defaults_qwen32b_judge/scores.json"
      if [[ -f "${score_file}" ]] \
        && { [[ "${RUN_HF_ARCHIVE}" != "1" ]] \
          || { archive_coverage_complete extraction "${slug}" "${seed}" mme_reasoning \
            && archive_coverage_complete score "${slug}" "${seed}" mme_reasoning; }; }; then
        echo "[mme-score:skip] seed=${seed} slug=${slug} score=${score_file}"
        continue
      fi
      echo "[mme-score:start] seed=${seed} slug=${slug}"
      (
        set -o pipefail
        eval_python "${REPO_ROOT}/scripts/run_mme_reasoning_eval.py" score \
          --model "${model}" \
          --model-slug "${slug}" \
          --seed "${seed}" \
          --run-root "${run_root}" \
          --benchmark-root "${benchmark_root}" \
          --judge-model "${JUDGE_MODEL}" \
          --judge-api-model "${JUDGE_SERVED_MODEL_NAME}" \
          --judge-api-tokenizer-model "${JUDGE_MODEL}" \
          --judge-api-parallelism "${JUDGE_API_PARALLELISM}" \
          --judge-api-batch-size "${JUDGE_API_BATCH_SIZE}" \
          --judge-api-batches-per-endpoint "${JUDGE_API_BATCHES_PER_ENDPOINT}" \
          --judge-api-max-batch-chars "${JUDGE_API_MAX_BATCH_CHARS}" \
          --judge-api-endpoint-failure-threshold "${JUDGE_API_ENDPOINT_FAILURE_THRESHOLD}" \
          --judge-api-endpoint-cooldown-seconds "${JUDGE_API_ENDPOINT_COOLDOWN_SECONDS}" \
          --judge-cache-contract-version "${JUDGE_CACHE_CONTRACT_VERSION}" \
          "${judge_args[@]}" \
          2>&1 | tee "${LOG_ROOT}/score_mme_${slug}_seed${seed}.log"
      ) &
      local pid="$!"
      pair_pids+=("${pid}")
      track_background_pid "${pid}"
      if [[ "${#pair_pids[@]}" -ge "${MME_MODEL_CONCURRENCY}" ]]; then
        if ! wait_for_background_jobs "${pair_pids[@]}"; then
          echo "[mme-score:error] seed=${seed} one or more paired model jobs failed" >&2
          return 1
        fi
        pair_pids=()
      fi
    done
    if [[ "${#pair_pids[@]}" -gt 0 ]] && ! wait_for_background_jobs "${pair_pids[@]}"; then
      echo "[mme-score:error] seed=${seed} one or more paired model jobs failed" >&2
      return 1
    fi
  done
}

prepare_llm_extraction_manifests() {
  local -n model_args_ref="$1"
  for seed in "${SEEDS[@]}"; do
    local run_root="${CAMPAIGN_ROOT}/seed_${seed}/runs"
    local benchmark_root="${CAMPAIGN_ROOT}/seed_${seed}/benchmark"
    local output_root="${CAMPAIGN_ROOT}/seed_${seed}/llm_extracted"
    local queue_root="${CAMPAIGN_ROOT}/seed_${seed}/queues"
    mkdir -p "${benchmark_root}" "${output_root}" "${queue_root}"
    echo "[score:llm-extract:prepare] seed=${seed}"
    eval_python "${REPO_ROOT}/scripts/run_llm_extracted_benchmark_score_queue.py" \
      --prepare --final25 \
      --seed "${seed}" \
      --queue-name "${RUN_TAG}_seed${seed}_llm_extract" \
      --queue-root "${queue_root}" \
      --run-root "${run_root}" \
      --output-root "${output_root}" \
      --benchmark-root "${benchmark_root}" \
      "${model_args_ref[@]}" \
      --judge-model "${JUDGE_MODEL}" \
      --api-model "${JUDGE_SERVED_MODEL_NAME}" \
      --api-tokenizer-model "${JUDGE_MODEL}" \
      --execution-backend api \
      --judge-max-tokens "${EXTRACTION_JUDGE_MAX_TOKENS}" \
      2>&1 | tee "${LOG_ROOT}/score_llm_extract_prepare_seed${seed}.log"
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
  if eval_python "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" --phase score --suite "${SUITE}" \
    "${verify_args[@]}" --seeds "${SEEDS[@]}" \
    && { [[ "${RUN_HF_ARCHIVE}" != "1" ]] || archive_coverage_complete "" ""; }; then
    echo "[score:skip] all ${SUITE_BENCHMARK_COUNT} suite scores already complete"
    return
  fi
  build_endpoint_args "${JUDGE_PORT_START}" --judge-api-base judge_args
  build_endpoint_args "${JUDGE_PORT_START}" --api-base llm_api_args

  echo "[score:llm-extract:prepare:start] seeds=${SEEDS[*]}"
  (
    set -o pipefail
    prepare_llm_extraction_manifests all_model_args
  ) &
  local prepare_pid="$!"
  track_background_pid "${prepare_pid}"

  echo "[judge:start] model=${JUDGE_MODEL} endpoints=${GPU_GROUPS}"
  start_pool \
    "${JUDGE_MODEL}" "${JUDGE_SERVED_MODEL_NAME}" "${JUDGE_PORT_START}" "${LOG_ROOT}/vllm_judge" \
    "${JUDGE_GPU_MEMORY_UTILIZATION}" "${JUDGE_MAX_MODEL_LEN}" "${JUDGE_MAX_NUM_SEQS}" "${JUDGE_MAX_NUM_BATCHED_TOKENS}"

  if ! wait_for_background_jobs "${prepare_pid}"; then
    echo "[score:llm-extract:prepare:error] manifest preparation failed" >&2
    return 1
  fi
  echo "[score:llm-extract:prepare:done] seeds=${SEEDS[*]}"

  local -a finalize_pids=()
  for seed in "${SEEDS[@]}"; do
    local run_root="${CAMPAIGN_ROOT}/seed_${seed}/runs"
    local benchmark_root="${CAMPAIGN_ROOT}/seed_${seed}/benchmark"
    local output_root="${CAMPAIGN_ROOT}/seed_${seed}/llm_extracted"
    local queue_root="${CAMPAIGN_ROOT}/seed_${seed}/queues"
    mkdir -p "${benchmark_root}" "${output_root}" "${queue_root}"

    echo "[score:direct:start] seed=${seed} workers=${DIRECT_SCORE_WORKERS}"
    local -a direct_pids=()
    local worker_index
    for ((worker_index = 0; worker_index < DIRECT_SCORE_WORKERS; worker_index++)); do
      (
        set -o pipefail
        eval_python "${REPO_ROOT}/scripts/run_external_benchmark_score_multi_model_queue.py" \
          "${all_model_args[@]}" \
          --worker-id "${RUN_TAG}-seed${seed}-direct-${worker_index}" \
          --queue-name "${RUN_TAG}_seed${seed}_direct_${TRACE_FINAL25_CAMPAIGN_CONFIG_HASH:0:16}" \
          --queue-root "${queue_root}" \
          --run-set trace_final25 \
          --seed "${seed}" \
          --run-root "${run_root}" \
          --benchmark-root "${benchmark_root}" \
          --eval-nproc "${DIRECT_EVAL_NPROC}" \
          --judge-model "${JUDGE_MODEL}" \
          --judge-api-model "${JUDGE_SERVED_MODEL_NAME}" \
          --judge-api-tokenizer-model "${JUDGE_MODEL}" \
          --judge-api-parallelism "${JUDGE_API_PARALLELISM}" \
          --judge-api-batch-size "${JUDGE_API_BATCH_SIZE}" \
          --judge-api-batches-per-endpoint "${JUDGE_API_BATCHES_PER_ENDPOINT}" \
          --judge-api-max-batch-chars "${JUDGE_API_MAX_BATCH_CHARS}" \
          --judge-api-endpoint-failure-threshold "${JUDGE_API_ENDPOINT_FAILURE_THRESHOLD}" \
          --judge-api-endpoint-cooldown-seconds "${JUDGE_API_ENDPOINT_COOLDOWN_SECONDS}" \
          --judge-cache-contract-version "${JUDGE_CACHE_CONTRACT_VERSION}" \
          "${judge_args[@]}" \
          --stop-on-error \
          2>&1 | tee "${LOG_ROOT}/score_direct_seed${seed}_worker${worker_index}.log"
      ) &
      local direct_pid="$!"
      direct_pids+=("${direct_pid}")
      track_background_pid "${direct_pid}"
    done

    if [[ "${SUITE}" == "all26" ]]; then
      (
        set -o pipefail
        eval_python "${REPO_ROOT}/scripts/run_external_benchmark_score_multi_model_queue.py" \
          "${all_model_args[@]}" \
          --worker-id "${RUN_TAG}-seed${seed}-direct-mmvp" \
          --queue-name "${RUN_TAG}_seed${seed}_direct_mmvp_${TRACE_FINAL25_CAMPAIGN_CONFIG_HASH:0:16}" \
          --queue-root "${queue_root}" \
          --run-set trace_final26 \
          --only mmvp \
          --exact-only \
          --seed "${seed}" \
          --run-root "${run_root}" \
          --benchmark-root "${benchmark_root}" \
          --eval-nproc "${DIRECT_EVAL_NPROC}" \
          --judge-model "${JUDGE_MODEL}" \
          --judge-api-model "${JUDGE_SERVED_MODEL_NAME}" \
          --judge-api-tokenizer-model "${JUDGE_MODEL}" \
          --judge-api-parallelism "${JUDGE_API_PARALLELISM}" \
          --judge-api-batch-size "${JUDGE_API_BATCH_SIZE}" \
          --judge-api-batches-per-endpoint "${JUDGE_API_BATCHES_PER_ENDPOINT}" \
          --judge-api-max-batch-chars "${JUDGE_API_MAX_BATCH_CHARS}" \
          --judge-api-endpoint-failure-threshold "${JUDGE_API_ENDPOINT_FAILURE_THRESHOLD}" \
          --judge-api-endpoint-cooldown-seconds "${JUDGE_API_ENDPOINT_COOLDOWN_SECONDS}" \
          --judge-cache-contract-version "${JUDGE_CACHE_CONTRACT_VERSION}" \
          "${judge_args[@]}" \
          --stop-on-error \
          2>&1 | tee "${LOG_ROOT}/score_direct_mmvp_seed${seed}.log"
      ) &
      local mmvp_direct_pid="$!"
      direct_pids+=("${mmvp_direct_pid}")
      track_background_pid "${mmvp_direct_pid}"
    fi

    echo "[score:llm-extract:api] seed=${seed}"
    eval_python "${REPO_ROOT}/scripts/run_llm_extracted_benchmark_score_queue.py" \
      --api-run --final25 \
      --seed "${seed}" \
      --queue-name "${RUN_TAG}_seed${seed}_llm_extract" \
      --queue-root "${queue_root}" \
      --run-root "${run_root}" \
      --output-root "${output_root}" \
      --benchmark-root "${benchmark_root}" \
      "${all_model_args[@]}" \
      --api-model "${JUDGE_SERVED_MODEL_NAME}" \
      --api-tokenizer-model "${JUDGE_MODEL}" \
      --api-parallelism "${EXTRACTION_API_PARALLELISM}" \
      --api-batch-size "${JUDGE_API_BATCH_SIZE}" \
      --api-batches-per-endpoint "${JUDGE_API_BATCHES_PER_ENDPOINT}" \
      --api-max-batch-chars "${JUDGE_API_MAX_BATCH_CHARS}" \
      --api-queue-capacity "${EXTRACTION_API_QUEUE_CAPACITY}" \
      --api-endpoint-failure-threshold "${JUDGE_API_ENDPOINT_FAILURE_THRESHOLD}" \
      --api-endpoint-cooldown-seconds "${JUDGE_API_ENDPOINT_COOLDOWN_SECONDS}" \
      --api-retry-base-delay "${EXTRACTION_API_RETRY_BASE_DELAY}" \
      --judge-model "${JUDGE_MODEL}" \
      --execution-backend api \
      --judge-max-tokens "${EXTRACTION_JUDGE_MAX_TOKENS}" \
      "${llm_api_args[@]}" \
      2>&1 | tee "${LOG_ROOT}/score_llm_extract_api_seed${seed}.log"

    if ! wait_for_background_jobs "${direct_pids[@]}"; then
      echo "[score:direct:error] seed=${seed} one or more workers failed" >&2
      return 1
    fi

    echo "[score:llm-extract:finalize] seed=${seed}"
    (
      set -o pipefail
      eval_python "${REPO_ROOT}/scripts/run_llm_extracted_benchmark_score_queue.py" \
        --finalize --final25 \
        --seed "${seed}" \
        --queue-name "${RUN_TAG}_seed${seed}_llm_extract" \
        --queue-root "${queue_root}" \
        --run-root "${run_root}" \
        --output-root "${output_root}" \
        --benchmark-root "${benchmark_root}" \
        "${all_model_args[@]}" \
        --judge-model "${JUDGE_MODEL}" \
        --judge-max-tokens "${EXTRACTION_JUDGE_MAX_TOKENS}" \
        2>&1 | tee "${LOG_ROOT}/score_llm_extract_finalize_seed${seed}.log"
    ) &
    local finalize_pid="$!"
    finalize_pids+=("${finalize_pid}")
    track_background_pid "${finalize_pid}"
  done

  # Keep the judge pool busy while the CPU-only extraction finalizers finish.
  run_mme_scoring

  if ! wait_for_background_jobs "${finalize_pids[@]}"; then
    echo "[score:llm-extract:error] one or more finalizers failed" >&2
    return 1
  fi
  stop_pool

  eval_python "${REPO_ROOT}/scripts/verify_trace_final25_campaign.py" \
    --campaign-root "${CAMPAIGN_ROOT}" --phase score --suite "${SUITE}" \
    "${verify_args[@]}" --seeds "${SEEDS[@]}"
}

run_summary() {
  local -a summary_model_args=()
  for i in "${!MODEL_SLUGS[@]}"; do
    summary_model_args+=(--model-entry "${MODEL_SLUGS[$i]}=${MODEL_LABELS[$i]}")
  done
  eval_python "${REPO_ROOT}/scripts/summarize_trace_final25_multiseed.py" \
    --score-root-base "${CAMPAIGN_ROOT}" \
    "${summary_model_args[@]}" \
    --suite "${SUITE}" \
    --seeds "${SEEDS[@]}" \
    --excel "${RESULTS_ROOT}/${RUN_TAG}_results.xlsx" \
    --markdown "${RESULTS_ROOT}/${RUN_TAG}_results.md" \
    2>&1 | tee "${LOG_ROOT}/summary.log"
}

echo "[campaign] tag=${RUN_TAG}"
echo "[campaign] root=${CAMPAIGN_ROOT}"
echo "[campaign] logs=${LOG_ROOT}"
echo "[campaign] suite=${SUITE} seeds=${SEEDS[*]} models=${#MODEL_SLUGS[@]} benchmarks=${SUITE_BENCHMARK_COUNT}"
echo "[campaign] generation=temp${GEN_TEMPERATURE},top_p${GEN_TOP_P},top_k${GEN_TOP_K},max${GEN_MAX_TOKENS}"
echo "[campaign] judge=${JUDGE_MODEL},temperature0"
echo "[campaign] extraction=in_flight_batches:${EXTRACTION_API_QUEUE_CAPACITY},parallelism:${EXTRACTION_API_PARALLELISM}"
echo "[campaign] cpu=vllm:${VLLM_CPU_AFFINITY_GROUPS} eval:${EVAL_CPUSET} archive:${HF_ARCHIVE_CPUSET}"
echo "[campaign] provenance=trace:${TRACE_GIT_COMMIT} vlmevalkit:${TRACE_VLMEVALKIT_GIT_COMMIT} code:${TRACE_FINAL25_CODE_HASH} config:${TRACE_FINAL25_CAMPAIGN_CONFIG_HASH}"

if [[ ! "${DIRECT_SCORE_WORKERS}" =~ ^[1-9][0-9]*$ ]]; then
  echo "[fatal] DIRECT_SCORE_WORKERS must be a positive integer" >&2
  exit 1
fi
if [[ ! "${MME_MODEL_CONCURRENCY}" =~ ^[1-9][0-9]*$ ]]; then
  echo "[fatal] MME_MODEL_CONCURRENCY must be a positive integer" >&2
  exit 1
fi

if [[ "${RUN_GENERATION}" == "1" || "${RUN_SCORING}" == "1" ]]; then
  validate_eval_environment
fi

start_archive_daemon

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

finalize_archive
echo "[campaign:done] results=${RESULTS_ROOT}/${RUN_TAG}_results.xlsx"
