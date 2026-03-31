#!/bin/bash

set -euo pipefail
set -x

export PYTHONUNBUFFERED=1
export WANDB_MODE="${WANDB_MODE:-offline}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RLVR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${RLVR_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${RLVR_ROOT}"

MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-3B-Instruct}"
TRAIN_FILE="${TRAIN_FILE:-mydata/trace_train_128k_multivariant_hf.parquet}"
PROMPT_KEY="${PROMPT_KEY:-prompt}"
NUM_GPUS="${NUM_GPUS:-4}"
MAX_STEPS="${MAX_STEPS:-10}"
ROLLOUT_TP="${ROLLOUT_TP:-1}"
FREEZE_VISION_TOWER="${FREEZE_VISION_TOWER:-false}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.8}"
IMAGE_CHECK_LIMIT="${IMAGE_CHECK_LIMIT:-256}"
TRACE_PREFLIGHT_ONLY="${TRACE_PREFLIGHT_ONLY:-0}"
SAVE_FREQ="${SAVE_FREQ:-10}"
VAL_FREQ="${VAL_FREQ:-10}"
FIND_LAST_CHECKPOINT="${FIND_LAST_CHECKPOINT:-true}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen2_5_vl_3b_trace_128k_4gpu_10steps}"
VAL_FILES_JSON="${VAL_FILES_JSON:-[]}"
TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_and_evidence}"
CURRICULUM_MODE="${CURRICULUM_MODE:-none}"
CURRICULUM_ALPHA0="${CURRICULUM_ALPHA0:-0.995}"
CURRICULUM_EPS_FLOOR="${CURRICULUM_EPS_FLOOR:-}"
CURRICULUM_BETA="${CURRICULUM_BETA:-2.0}"
CURRICULUM_LOG_INTERVAL="${CURRICULUM_LOG_INTERVAL:-10}"

# Fail fast if the exported parquet is malformed or points at missing image paths.
python3 - "${TRAIN_FILE}" "${PROMPT_KEY}" "${IMAGE_CHECK_LIMIT}" "${VAL_FILES_JSON}" <<'PY'
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

parquet_path = Path(sys.argv[1]).resolve()
prompt_key = str(sys.argv[2])
image_check_limit = int(sys.argv[3])
val_files = json.loads(sys.argv[4])

if not parquet_path.exists():
    raise SystemExit(f"TRACE parquet not found: {parquet_path}")
if not isinstance(val_files, list):
    raise SystemExit(f"VAL_FILES_JSON must decode to a list, got: {type(val_files)!r}")

required_columns = (prompt_key, "images", "answer_gt", "evidence_gt", "reward_contract")
parquet_file = pq.ParquetFile(parquet_path)
available_columns = set(parquet_file.schema_arrow.names)
missing_columns = [name for name in required_columns if name not in available_columns]
if missing_columns:
    raise SystemExit(
        "TRACE parquet is missing required columns: "
        + ", ".join(missing_columns)
        + f". Available columns: {sorted(available_columns)}"
    )

sample_rows = min(parquet_file.metadata.num_rows, max(1, image_check_limit))
sampled_rows = []
for batch in parquet_file.iter_batches(batch_size=sample_rows, columns=list(required_columns)):
    sampled_rows.extend(batch.to_pylist())
    if len(sampled_rows) >= sample_rows:
        break

for row_idx, row in enumerate(sampled_rows[:sample_rows]):
    if not row[prompt_key]:
        raise SystemExit(f"Empty prompt at sampled row {row_idx}")

    for key in ("answer_gt", "evidence_gt", "reward_contract"):
        value = row[key]
        if not value:
            raise SystemExit(f"Empty {key} at sampled row {row_idx}")
        try:
            json.loads(value)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in {key} at sampled row {row_idx}: {exc}") from exc

    images = row["images"] or []
    if not images:
        raise SystemExit(f"No images at sampled row {row_idx}")

    for image_idx, image_record in enumerate(images):
        image_bytes = image_record.get("bytes")
        if image_bytes is not None:
            if not image_bytes:
                raise SystemExit(f"Empty image bytes at sampled row {row_idx}, image {image_idx}")
            continue

        image_path = image_record.get("path")
        if not image_path:
            raise SystemExit(f"Missing image bytes/path at sampled row {row_idx}, image {image_idx}")
        resolved = (parquet_path.parent / image_path).resolve() if not Path(image_path).is_absolute() else Path(image_path)
        if not resolved.exists():
            raise SystemExit(
                f"Missing image file at sampled row {row_idx}, image {image_idx}: {resolved}"
            )

for val_idx, raw_path in enumerate(val_files):
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise SystemExit(f"Invalid validation file entry at index {val_idx}: {raw_path!r}")
    resolved = Path(raw_path).expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"Validation parquet not found at index {val_idx}: {resolved}")

print(
    "TRACE preflight passed:",
    f"rows={parquet_file.metadata.num_rows}",
    f"sampled_rows={sample_rows}",
    f"prompt_key={prompt_key}",
    f"path={parquet_path}",
    f"val_files={len(val_files)}",
)
PY

if [[ "${TRACE_PREFLIGHT_ONLY}" == "1" ]]; then
  exit 0
fi

ARGS=(
  python3 -m verl.trainer.main
  config=examples/config_trace.yaml
  data.train_files="${TRAIN_FILE}"
  data.prompt_key="${PROMPT_KEY}"
  data.val_files="${VAL_FILES_JSON}"
  data.curriculum_mode="${CURRICULUM_MODE}"
  data.curriculum_alpha0="${CURRICULUM_ALPHA0}"
  data.curriculum_beta="${CURRICULUM_BETA}"
  data.curriculum_log_interval="${CURRICULUM_LOG_INTERVAL}"
  worker.actor.model.model_path="${MODEL_PATH}"
  worker.actor.model.freeze_vision_tower="${FREEZE_VISION_TOWER}"
  worker.rollout.tensor_parallel_size="${ROLLOUT_TP}"
  worker.rollout.gpu_memory_utilization="${GPU_MEMORY_UTILIZATION}"
  worker.reward.reward_function_kwargs.trace_reward_mode="${TRACE_REWARD_MODE}"
  trainer.project_name=trace_rlvr
  trainer.experiment_name="${EXPERIMENT_NAME}"
  trainer.n_gpus_per_node="${NUM_GPUS}"
  trainer.max_steps="${MAX_STEPS}"
  trainer.total_epochs=1
  trainer.save_freq="${SAVE_FREQ}"
  trainer.val_freq="${VAL_FREQ}"
  trainer.find_last_checkpoint="${FIND_LAST_CHECKPOINT}"
)

if [[ -n "${CURRICULUM_EPS_FLOOR}" ]]; then
  ARGS+=(data.curriculum_eps_floor="${CURRICULUM_EPS_FLOOR}")
fi

"${ARGS[@]}"
