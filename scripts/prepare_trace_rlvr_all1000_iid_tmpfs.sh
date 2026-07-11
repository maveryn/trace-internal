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
CLEAN_SCHEMA="${CLEAN_SCHEMA:-1}"
SHUFFLE_ROWS="${SHUFFLE_ROWS:-1}"
ROW_ORDER_SEED="${ROW_ORDER_SEED:-20260711}"

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

  "$PYTHON_BIN" - "$role" "$name" "$rows" "$seed" "$parquet" "$manifest" "$SHUFFLE_ROWS" "$ROW_ORDER_SEED" <<'PY'
import json
import sys
from pathlib import Path

role, name, rows, seed, parquet, manifest, shuffle_rows, row_order_seed = sys.argv[1:]
payload = {
    "dataset_name": name,
    "recipe": "trace_rlvr_all1000_iid_tmpfs",
    "schema_profile": "trace_rlvr_viewer_v1",
    "split_role": role,
    "task_count": 1000,
    "rows": int(rows),
    "samples_per_task": int(rows) // 1000,
    "seed": int(seed),
    "parquet": parquet,
    "prompt_storage": (
        "RLVR export stores prompt_answer and prompt_answer_and_annotation."
    ),
    "row_order": "deterministic_shuffle" if shuffle_rows == "1" else "generation_order",
    "row_order_seed": int(row_order_seed) if shuffle_rows == "1" else None,
    "image_storage_mode": "embedded_bytes",
    "max_embedded_image_pixels": 1280000,
    "columns": [
        "images",
        "prompt_answer",
        "prompt_answer_and_annotation",
        "answer_gt",
        "annotation_gt",
        "reward_contract",
        "instance_id",
        "domain",
        "task",
        "scene_id",
        "query_id",
        "scene_variant",
        "trace_ref",
    ],
    "dropped_legacy_columns": [
        "uid",
        "prompt",
        "prompt_active",
        "prompt_answer_only",
        "prompt_mode",
        "difficulty_bin",
        "bucket_id_str",
        "image_sizes_original",
        "image_sizes_exported",
    ],
}
Path(manifest).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"[manifest] {manifest}")
PY
}

clean_schema() {
  local parquet="$1"
  if [[ "$CLEAN_SCHEMA" != "1" ]]; then
    return
  fi
  "$PYTHON_BIN" - "$parquet" "$SHUFFLE_ROWS" "$ROW_ORDER_SEED" <<'PY'
import json
import os
import sys
from pathlib import Path

import pyarrow.parquet as pq

path = Path(sys.argv[1])
shuffle_rows = sys.argv[2] == "1"
row_order_seed = int(sys.argv[3])
columns = [
    "images",
    "prompt_answer",
    "prompt_answer_and_annotation",
    "answer_gt",
    "annotation_gt",
    "reward_contract",
    "instance_id",
    "domain",
    "task",
    "scene_id",
    "query_id",
    "scene_variant",
    "trace_ref",
]
schema_names = set(pq.read_schema(path).names)
missing = [column for column in columns if column not in schema_names]
if missing:
    raise SystemExit(f"cannot clean {path}: missing columns {missing}")
expected_row_order = "deterministic_shuffle" if shuffle_rows else "generation_order"
manifest_path = path.with_suffix(path.suffix + ".manifest.json")
manifest = {}
if manifest_path.exists():
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        manifest = {}
already_final = (
    list(pq.read_schema(path).names) == columns
    and manifest.get("schema_profile") == "trace_rlvr_viewer_v1"
    and manifest.get("row_order") == expected_row_order
    and (not shuffle_rows or int(manifest.get("row_order_seed", -1)) == row_order_seed)
)
if already_final:
    print(f"[clean-schema] skip already-final {path}")
    raise SystemExit(0)
tmp_path = path.with_suffix(path.suffix + ".cleaning")
if shuffle_rows:
    os.environ.setdefault("HF_DATASETS_CACHE", str(path.parent / ".hf_datasets_cache"))
    from datasets import load_dataset

    dataset = load_dataset("parquet", data_files=str(path), split="train")
    dataset = dataset.select_columns(columns).shuffle(seed=row_order_seed)
    row_count = dataset.num_rows
    dataset.to_parquet(str(tmp_path), batch_size=512)
else:
    table = pq.read_table(path, columns=columns)
    row_count = table.num_rows
    pq.write_table(table, tmp_path, compression="zstd", row_group_size=512)
os.replace(tmp_path, path)
print(
    f"[clean-schema] {path} columns={len(columns)} rows={row_count} "
    f"row_order={expected_row_order}"
)
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
    clean_schema "$parquet"
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

  clean_schema "$parquet"
  write_manifest "$role" "$name" "$rows" "$seed" "$parquet"
}

echo "[all1000-iid] tmpfs_root=${TMPFS_ROOT}"
echo "[all1000-iid] output_root=${OUTPUT_ROOT}"
echo "[all1000-iid] dataset_dir=${DATASET_DIR}"
echo "[all1000-iid] code_hash=${CODE_HASH}"
echo "[all1000-iid] clean_schema=${CLEAN_SCHEMA} shuffle_rows=${SHUFFLE_ROWS} row_order_seed=${ROW_ORDER_SEED}"

run_dataset train "$TRAIN_NAME" "$TRAIN_NUM_INSTANCES" "$TRAIN_SEED" "$TRAIN_PARQUET"
run_dataset validation_iid "$VAL_NAME" "$VAL_NUM_INSTANCES" "$VAL_SEED" "$VAL_PARQUET"

echo "[done] train=${TRAIN_PARQUET}"
echo "[done] validation_iid=${VAL_PARQUET}"
