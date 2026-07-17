#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTHON_BIN="$(command -v "${PYTHON_BIN}" || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "[baseline-queue:fatal] PYTHON_BIN is not executable" >&2
  exit 1
fi
TMP_ROOT="${TMP_ROOT:-/dev/shm/trace_rlvr}"
MODEL_ROOT="${MODEL_ROOT:-${TMP_ROOT}/final25_models}"
LMU_DATA="${LMUData:-${TMP_ROOT}/LMUData}"
DATASET_MANIFEST="${DATASET_MANIFEST:-${LMU_DATA}/trace_eval_v1_dataset_manifest.json}"
VLMEVALKIT_ROOT="${VLMEVALKIT_ROOT:-${REPO_ROOT}/external/VLMEvalKit}"
EVAL_DEPS_ROOT="${EVAL_DEPS_ROOT:-${REPO_ROOT}/.tmp/eval_deps}"
TOKEN_FILE="${TOKEN_FILE:-${REPO_ROOT}/hf-token.txt}"
PAPER_REPO="${PAPER_REPO:-maveryn/trace-eval-runs}"

RUN_TAG="${RUN_TAG:-trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717}"
PUBLIC_RUN_ID="${PUBLIC_RUN_ID:-qwen2.5-vl-7b-rl-baselines-temp06-seeds42-44-v1}"
CAMPAIGN_ROOT="${CAMPAIGN_ROOT:-${TMP_ROOT}/${RUN_TAG}}"
SCORE_ROOT="${SCORE_ROOT:-${CAMPAIGN_ROOT}/scoring}"
ARCHIVE_ROOT="${LOCAL_ARCHIVE_SPOOL_ROOT:-${CAMPAIGN_ROOT}/hf_archive}"
LOG_ROOT="${LOG_ROOT:-${REPO_ROOT}/logs/benchmark/${RUN_TAG}}"
PUBLISH_ROOT="${PUBLISH_ROOT:-${REPO_ROOT}/logs/publish/${PUBLIC_RUN_ID}}"
LOCK_ROOT="${LOCK_ROOT:-${HOME}/.cache/trace-eval-queue/locks}"

GAME_SLUG="${GAME_SLUG:-game-rl-qwen25vl7b}"
GAME_PATH="${GAME_PATH:-${TMP_ROOT}/runtime_models/game-rl-qwen25vl7b-processor-alias}"
GAME_REV="${GAME_REV:-sha256set:a9c97c8bd921fcaeaf5160c1ed644b34f292ae05302a00980c4ded899a837f8f}"
GAME_UPSTREAM_REV="${GAME_UPSTREAM_REV:-205b5934ce70504cfd6ae26b16f705d0b98b9306}"
GAME_REPO="${GAME_REPO:-OpenMOSS-Team/Game-RL-Qwen2.5-VL-7B}"

SPHINX_SLUG="${SPHINX_SLUG:-sphinx-qwen7b-500}"
SPHINX_PATH="${SPHINX_PATH:-${MODEL_ROOT}/${SPHINX_SLUG}}"
SPHINX_REV="${SPHINX_REV:-6ffefb03d5cb0767683bfb42a084ea86b707ef9a}"
SPHINX_REPO="${SPHINX_REPO:-xashru/sphinx_qwen7b_500}"

PCGRPO_SLUG="${PCGRPO_SLUG:-pcgrpo-qwen25vl7b-jigsaw-care}"
PCGRPO_PATH="${PCGRPO_PATH:-${MODEL_ROOT}/${PCGRPO_SLUG}}"
PCGRPO_REV="${PCGRPO_REV:-921bbced4176f5d362e98c843a57656c5d78dad7}"
PCGRPO_REPO="${PCGRPO_REPO:-armenjeddi/PCGRPO-Qwen2.5-VL-7B-Jigsaw-with-curriculum-with-grpo-care}"

JUDGE_PATH="${JUDGE_PATH:-${MODEL_ROOT}/qwen3-32b-judge}"
JUDGE_REV="${JUDGE_REV:-9216db5781bf21249d130ec9da846c4624c16137}"

print_config() {
  printf '%s\n' \
    "repo_root=${REPO_ROOT}" \
    "python_bin=${PYTHON_BIN}" \
    "campaign_root=${CAMPAIGN_ROOT}" \
    "dataset_manifest=${DATASET_MANIFEST}" \
    "game=${GAME_SLUG}|${GAME_PATH}|${GAME_REV}|${GAME_REPO}@${GAME_UPSTREAM_REV}" \
    "sphinx=${SPHINX_SLUG}|${SPHINX_PATH}|${SPHINX_REV}|${SPHINX_REPO}@${SPHINX_REV}" \
    "pcgrpo=${PCGRPO_SLUG}|${PCGRPO_PATH}|${PCGRPO_REV}|${PCGRPO_REPO}@${PCGRPO_REV}" \
    "judge=${JUDGE_PATH}|${JUDGE_REV}" \
    "paper_repo=${PAPER_REPO}" \
    "public_run_id=${PUBLIC_RUN_ID}"
}

if [[ "${TRACE_RL_BASELINES_PRINT_CONFIG:-0}" == "1" ]]; then
  print_config
  exit 0
fi

mkdir -p "${LOG_ROOT}" "${PUBLISH_ROOT}" "${LOCK_ROOT}"
exec 9>"${LOCK_ROOT}/rl-baselines.lock"
if ! flock -n 9; then
  echo "[baseline-queue:fatal] another RL baseline campaign owns the queue lock" >&2
  exit 1
fi

export PYTHON_BIN TMP_ROOT MODEL_ROOT LMUData="${LMU_DATA}" DATASET_MANIFEST
export VLMEVALKIT_ROOT EVAL_DEPS_ROOT CAMPAIGN_ROOT SCORE_ROOT LOG_ROOT
export LOCAL_ARCHIVE_SPOOL_ROOT="${ARCHIVE_ROOT}"
export RUN_GENERATION=1 RUN_SCORING=1 RUN_SUMMARY=1 RUN_LOCAL_ARCHIVE=1
unset RUN_HF_ARCHIVE HF_ARCHIVE_REPO_ID

write_phase() {
  local phase="$1"
  printf '%s phase=%s pid=%s run_tag=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${phase}" "$$" "${RUN_TAG}" \
    >"${LOG_ROOT}/queue.status"
  echo "[baseline-queue] phase=${phase}"
}

gpu_compute_pids() {
  nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits 2>/dev/null \
    | sed '/^[[:space:]]*$/d' | sort -u
}

busy_eval_ports() {
  ss -ltnH 2>/dev/null \
    | awk '$4 ~ /:(1800[0-7]|1810[0-7])$/ {print $4}'
}

write_phase waiting_for_gpus
while [[ -n "$(gpu_compute_pids)" || -n "$(busy_eval_ports)" ]]; do
  echo "[baseline-queue:wait] existing GPU process or evaluation endpoint is still active"
  sleep 15
done

write_phase preflight
"${PYTHON_BIN}" "${REPO_ROOT}/scripts/prepare_trace_final25_models.py" verify --deep \
  --entry "${GAME_SLUG}=${GAME_PATH}=${GAME_REV}" \
  --entry "${SPHINX_SLUG}=${SPHINX_PATH}=${SPHINX_REV}" \
  --entry "${PCGRPO_SLUG}=${PCGRPO_PATH}=${PCGRPO_REV}" \
  --entry "qwen3-32b-judge=${JUDGE_PATH}=${JUDGE_REV}"
export MODEL_VERIFY_DEEP=0

publisher_pid=""
cleanup() {
  local status=$?
  if [[ "${status}" -ne 0 && -n "${publisher_pid}" ]]; then
    kill -TERM "${publisher_pid}" 2>/dev/null || true
  fi
  return "${status}"
}
trap cleanup EXIT

write_phase starting_publisher
"${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_trace_eval_publish_worker.py" \
  --campaign-root "${CAMPAIGN_ROOT}" \
  --score-root "${SCORE_ROOT}" \
  --archive-spool-root "${ARCHIVE_ROOT}" \
  --dataset-manifest "${DATASET_MANIFEST}" \
  --vlmeval-root "${VLMEVALKIT_ROOT}" \
  --work-root "${PUBLISH_ROOT}" \
  --source-run-id "${RUN_TAG}" \
  --public-run-id "${PUBLIC_RUN_ID}" \
  --seed 42 --seed 43 --seed 44 \
  --model "${GAME_SLUG}" "${GAME_PATH}" "${GAME_REV}" \
    game-rl-qwen2.5-vl-7b "${GAME_UPSTREAM_REV}" "Game-RL Qwen2.5-VL-7B" "${GAME_REPO}" "${GAME_UPSTREAM_REV}" \
  --model "${SPHINX_SLUG}" "${SPHINX_PATH}" "${SPHINX_REV}" \
    sphinx-qwen2.5-vl-7b "${SPHINX_REV}" "Sphinx Qwen2.5-VL-7B 500" "${SPHINX_REPO}" "${SPHINX_REV}" \
  --model "${PCGRPO_SLUG}" "${PCGRPO_PATH}" "${PCGRPO_REV}" \
    pcgrpo-qwen2.5-vl-7b "${PCGRPO_REV}" "PCGRPO Qwen2.5-VL-7B Jigsaw CARE" "${PCGRPO_REPO}" "${PCGRPO_REV}" \
  --judge qwen3-32b-judge Qwen/Qwen3-32B "${JUDGE_REV}" \
  --token-file "${TOKEN_FILE}" \
  --paper-repo "${PAPER_REPO}" \
  --timeout-seconds 172800 \
  --allow-paper-run-upload \
  --confirm-paper-run "UPLOAD ${PAPER_REPO}/${PUBLIC_RUN_ID}" \
  >>"${PUBLISH_ROOT}/worker.log" 2>&1 &
publisher_pid=$!
printf '%s\n' "${publisher_pid}" >"${PUBLISH_ROOT}/worker.pid"

write_phase evaluating
bash "${REPO_ROOT}/scripts/run_trace_eval.sh" \
  --model "${GAME_SLUG}" "${GAME_PATH}" "${GAME_REV}" \
    "${GAME_REPO}@${GAME_UPSTREAM_REV}" "Game-RL Qwen2.5-VL-7B" \
  --model "${SPHINX_SLUG}" "${SPHINX_PATH}" "${SPHINX_REV}" \
    "${SPHINX_REPO}@${SPHINX_REV}" "Sphinx Qwen2.5-VL-7B 500" \
  --model "${PCGRPO_SLUG}" "${PCGRPO_PATH}" "${PCGRPO_REV}" \
    "${PCGRPO_REPO}@${PCGRPO_REV}" "PCGRPO Qwen2.5-VL-7B Jigsaw CARE" \
  --seeds 42 43 44 \
  --run-tag "${RUN_TAG}"

write_phase waiting_for_publisher
wait "${publisher_pid}"
publisher_pid=""
write_phase complete
