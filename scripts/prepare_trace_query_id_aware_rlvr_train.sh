#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || "$1" == "-h" || "$1" == "--help" ]]; then
  cat <<'EOF'
Usage:
  scripts/prepare_trace_query_id_aware_rlvr_train.sh <alpha> [cpu_count]

Example:
  scripts/prepare_trace_query_id_aware_rlvr_train.sh 0.5
  scripts/prepare_trace_query_id_aware_rlvr_train.sh 0.5 180

Optional environment overrides:
  NUM_INSTANCES=200000
  SAMPLING_SEED=20260504
  PROMPT_VARIANT=answer
  OUTPUT_ROOT=./out
  WORKERS=0
  MAX_IN_FLIGHT=0
  PARQUET_CPU_COUNT=0
  QUERY_ID_COUNT_PROBE_SAMPLES=8
  IMAGE_STORAGE_MODE=embedded_bytes
  RESET=1
EOF
  exit 0
fi

ALPHA="$1"
CPU_COUNT="${2:-}"
NUM_INSTANCES="${NUM_INSTANCES:-200000}"
SAMPLING_SEED="${SAMPLING_SEED:-20260504}"
PROMPT_VARIANT="${PROMPT_VARIANT:-answer}"
OUTPUT_ROOT="${OUTPUT_ROOT:-./out}"
if [[ -n "${CPU_COUNT}" ]]; then
  WORKERS="${WORKERS:-${CPU_COUNT}}"
  PARQUET_CPU_COUNT="${PARQUET_CPU_COUNT:-${CPU_COUNT}}"
else
  WORKERS="${WORKERS:-0}"
  PARQUET_CPU_COUNT="${PARQUET_CPU_COUNT:-0}"
fi
MAX_IN_FLIGHT="${MAX_IN_FLIGHT:-0}"
QUERY_ID_COUNT_PROBE_SAMPLES="${QUERY_ID_COUNT_PROBE_SAMPLES:-8}"
IMAGE_STORAGE_MODE="${IMAGE_STORAGE_MODE:-embedded_bytes}"
RESET="${RESET:-1}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

ALPHA_TAG="$(printf '%s' "${ALPHA}" | sed 's/[^0-9A-Za-z]/_/g; s/_*$//; s/^_*//')"
if [[ -z "${ALPHA_TAG}" ]]; then
  echo "Invalid alpha tag derived from: ${ALPHA}" >&2
  exit 2
fi

DATASET_NAME="${DATASET_NAME:-trace_rlvr_train_${NUM_INSTANCES}_query_id_alpha${ALPHA_TAG}_${PROMPT_VARIANT}_seed${SAMPLING_SEED}}"
RLVR_OUTPUT="${RLVR_OUTPUT:-rlvr/dataset/train/${DATASET_NAME}.parquet}"

cmd=(
  python scripts/prepare_trace_rlvr_train.py
  --output-root "${OUTPUT_ROOT}"
  --dataset-name "${DATASET_NAME}"
  --num-instances "${NUM_INSTANCES}"
  --task-sampling-policy query_id_aware
  --query-id-weight-alpha "${ALPHA}"
  --query-id-count-probe-samples "${QUERY_ID_COUNT_PROBE_SAMPLES}"
  --sampling-seed "${SAMPLING_SEED}"
  --workers "${WORKERS}"
  --max-in-flight "${MAX_IN_FLIGHT}"
  --parquet-cpu-count "${PARQUET_CPU_COUNT}"
  --prompt-variant "${PROMPT_VARIANT}"
  --image-storage-mode "${IMAGE_STORAGE_MODE}"
  --rlvr-output "${RLVR_OUTPUT}"
)

if [[ "${RESET}" != "0" && "${RESET,,}" != "false" && "${RESET,,}" != "no" ]]; then
  cmd+=(--reset)
fi

echo "TRACE query-id-aware RLVR build"
echo "  alpha: ${ALPHA}"
echo "  dataset: ${DATASET_NAME}"
echo "  rows: ${NUM_INSTANCES}"
echo "  output: ${RLVR_OUTPUT}"
echo "  workers: ${WORKERS} (0=all CPUs)"
echo "  parquet_cpu_count: ${PARQUET_CPU_COUNT} (0=all CPUs)"

PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" "${cmd[@]}"
