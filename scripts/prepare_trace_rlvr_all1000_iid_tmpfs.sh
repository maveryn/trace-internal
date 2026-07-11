#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

WORKERS="${WORKERS:-96}"
MAX_IN_FLIGHT="${MAX_IN_FLIGHT:-$((WORKERS * 2))}"
PARQUET_CPU_COUNT="${PARQUET_CPU_COUNT:-96}"
export TRACE_EXPORT_PARQUET_ROW_WORKERS="${TRACE_EXPORT_PARQUET_ROW_WORKERS:-$PARQUET_CPU_COUNT}"
export TRACE_BUILD_PROGRESS="${TRACE_BUILD_PROGRESS:-1}"
export TRACE_EXPORT_PROGRESS="${TRACE_EXPORT_PROGRESS:-1}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
export ARROW_NUM_THREADS="${ARROW_NUM_THREADS:-$PARQUET_CPU_COUNT}"

TMPFS_ROOT="${TMPFS_ROOT:-/dev/shm/trace_rlvr}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$TMPFS_ROOT/builds/all1000_iid}"
DATASET_DIR="${DATASET_DIR:-$TMPFS_ROOT/datasets}"
IMAGE_CAP="${IMAGE_CAP:-1280000}"
RESET="${RESET:-0}"

TRAIN_SEED="${TRAIN_SEED:-42}"
TRAIN_NUM_INSTANCES="${TRAIN_NUM_INSTANCES:-64000}"
TRAIN_NAME="${TRAIN_NAME:-trace_rlvr_train_64000_all1000_seed${TRAIN_SEED}}"
TRAIN_PARQUET="${TRAIN_PARQUET:-$DATASET_DIR/${TRAIN_NAME}.parquet}"

VAL_SEED="${VAL_SEED:-1042}"
VAL_NUM_INSTANCES="${VAL_NUM_INSTANCES:-2000}"
VAL_NAME="${VAL_NAME:-trace_rlvr_validation_iid_2000_all1000_seed${VAL_SEED}}"
VAL_PARQUET="${VAL_PARQUET:-$DATASET_DIR/${VAL_NAME}.parquet}"

CODE_HASH="${CODE_HASH:-$(git rev-parse --short=12 HEAD 2>/dev/null || echo local)}"
PYTHON_BIN="${PYTHON_BIN:-/home/shadeform/venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN=python3
fi

mkdir -p "$OUTPUT_ROOT" "$DATASET_DIR"

write_manifest() {
  local role="$1"
  local name="$2"
  local rows="$3"
  local seed="$4"
  local parquet="$5"
  local manifest="${parquet}.manifest.json"

  "$PYTHON_BIN" - "$role" "$name" "$rows" "$seed" "$parquet" "$manifest" <<'PY'
import json
import sys
from pathlib import Path

role, name, rows, seed, parquet, manifest = sys.argv[1:]
payload = {
    "dataset_name": name,
    "recipe": "trace_rlvr_all1000_iid_tmpfs",
    "split_role": role,
    "task_count": 1000,
    "rows": int(rows),
    "samples_per_task": int(rows) // 1000,
    "seed": int(seed),
    "parquet": parquet,
    "prompt_storage": (
        "RLVR export stores prompt_active, prompt_answer, "
        "prompt_answer_only, and prompt_answer_and_annotation."
    ),
    "image_storage_mode": "embedded_bytes",
    "max_embedded_image_pixels": 1280000,
}
Path(manifest).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"[manifest] {manifest}")
PY
}

run_dataset() {
  local role="$1"
  local name="$2"
  local rows="$3"
  local seed="$4"
  local parquet="$5"
  shift 5

  if [[ -s "$parquet" && "$RESET" != "1" ]]; then
    echo "[skip] ${role}: existing parquet ${parquet}"
    write_manifest "$role" "$name" "$rows" "$seed" "$parquet"
    return
  fi

  local reset_args=()
  if [[ "$RESET" == "1" ]]; then
    reset_args=(--reset)
  fi

  echo "[build:${role}] name=${name} rows=${rows} seed=${seed}"
  echo "[build:${role}] output_root=${OUTPUT_ROOT}/${role}"
  echo "[build:${role}] parquet=${parquet}"
  echo "[build:${role}] workers=${WORKERS} max_in_flight=${MAX_IN_FLIGHT} parquet_cpu_count=${PARQUET_CPU_COUNT}"

  "$PYTHON_BIN" scripts/prepare_trace_rlvr_train.py \
    --output-root "$OUTPUT_ROOT/$role" \
    --dataset-name "$name" \
    --num-instances "$rows" \
    --task-sampling-policy equal \
    --sampling-seed "$seed" \
    --workers "$WORKERS" \
    --max-in-flight "$MAX_IN_FLIGHT" \
    --code-hash "$CODE_HASH" \
    --rlvr-output "$parquet" \
    --prompt-variant answer_and_annotation \
    --image-path-mode relative \
    --image-storage-mode embedded_bytes \
    --parquet-cpu-count "$PARQUET_CPU_COUNT" \
    --max-embedded-image-pixels "$IMAGE_CAP" \
    "${reset_args[@]}"

  write_manifest "$role" "$name" "$rows" "$seed" "$parquet"
}

echo "[all1000-iid] tmpfs_root=${TMPFS_ROOT}"
echo "[all1000-iid] output_root=${OUTPUT_ROOT}"
echo "[all1000-iid] dataset_dir=${DATASET_DIR}"
echo "[all1000-iid] code_hash=${CODE_HASH}"

run_dataset train "$TRAIN_NAME" "$TRAIN_NUM_INSTANCES" "$TRAIN_SEED" "$TRAIN_PARQUET"
run_dataset validation_iid "$VAL_NAME" "$VAL_NUM_INSTANCES" "$VAL_SEED" "$VAL_PARQUET"

echo "[done] train=${TRAIN_PARQUET}"
echo "[done] validation_iid=${VAL_PARQUET}"
