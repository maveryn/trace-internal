#!/bin/bash

set -euo pipefail
set -x

export PYTHONUNBUFFERED=1
export WANDB_MODE="${WANDB_MODE:-online}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RLVR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/validation_pack_qwen3_vl_2b_selected512.sh"

export PYTHONPATH="${RLVR_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${RLVR_ROOT}"

MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-3B-Instruct}"
TRAIN_FILE="${TRAIN_FILE:-mydata/trace_train_128k_multivariant_hf.parquet}"
PROMPT_KEY="${PROMPT_KEY:-prompt}"
HF_TRAIN_REPO="${HF_TRAIN_REPO:-xashru/trace-rlvr-train-128k}"
HF_TRAIN_SPLIT="${HF_TRAIN_SPLIT:-train}"
NUM_GPUS="${NUM_GPUS:-4}"
MAX_STEPS="${MAX_STEPS:-10}"
ROLLOUT_TP="${ROLLOUT_TP:-1}"
ROLLOUT_N="${ROLLOUT_N:-8}"
FREEZE_VISION_TOWER="${FREEZE_VISION_TOWER:-false}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.8}"
IMAGE_CHECK_LIMIT="${IMAGE_CHECK_LIMIT:-256}"
TRACE_PREFLIGHT_ONLY="${TRACE_PREFLIGHT_ONLY:-0}"
SAVE_FREQ="${SAVE_FREQ:-10}"
VAL_FREQ="${VAL_FREQ:-10}"
FIND_LAST_CHECKPOINT="${FIND_LAST_CHECKPOINT:-true}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen2_5_vl_3b_trace_128k_4gpu_10steps}"
VAL_FILES_JSON="${VAL_FILES_JSON:-${DEFAULT_VAL_FILES_JSON}}"
TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer_and_evidence}"
CURRICULUM_MODE="${CURRICULUM_MODE:-none}"
CURRICULUM_ALPHA0="${CURRICULUM_ALPHA0:-0.995}"
CURRICULUM_EPS_FLOOR="${CURRICULUM_EPS_FLOOR:-}"
CURRICULUM_BETA="${CURRICULUM_BETA:-2.0}"
CURRICULUM_LOG_INTERVAL="${CURRICULUM_LOG_INTERVAL:-10}"
ROLLOUT_BATCH_SIZE="${ROLLOUT_BATCH_SIZE:-128}"
ACTOR_GLOBAL_BATCH_SIZE="${ACTOR_GLOBAL_BATCH_SIZE:-128}"
ACTOR_MICRO_BATCH_SIZE_UPDATE="${ACTOR_MICRO_BATCH_SIZE_UPDATE:-16}"
ACTOR_MICRO_BATCH_SIZE_EXPERIENCE="${ACTOR_MICRO_BATCH_SIZE_EXPERIENCE:-32}"
TRAIN_DATALOADER_NUM_WORKERS="${TRAIN_DATALOADER_NUM_WORKERS:-8}"
VAL_DATALOADER_NUM_WORKERS="${VAL_DATALOADER_NUM_WORKERS:-8}"
FILTER_OVERLONG_PROMPTS="${FILTER_OVERLONG_PROMPTS:-true}"
FILTER_OVERLONG_PROMPTS_WORKERS="${FILTER_OVERLONG_PROMPTS_WORKERS:-16}"
MAX_RESPONSE_LENGTH="${MAX_RESPONSE_LENGTH:-}"
VAL_MAX_TOKENS="${VAL_MAX_TOKENS:-}"
PADDING_FREE="${PADDING_FREE:-true}"
USE_TORCH_COMPILE="${USE_TORCH_COMPILE:-true}"

TRAIN_SOURCE="${TRAIN_FILE}"
if [[ "${TRAIN_FILE}" == *.parquet || "${TRAIN_FILE}" == /* || "${TRAIN_FILE}" == ./* || "${TRAIN_FILE}" == ../* ]]; then
  if [[ -f "${TRAIN_FILE}" ]]; then
    TRAIN_SOURCE="${TRAIN_FILE}"
  else
    if [[ -z "${HF_TRAIN_REPO}" ]]; then
      echo "TRACE parquet not found locally and HF_TRAIN_REPO is empty: ${TRAIN_FILE}" >&2
      exit 1
    fi
    TRAIN_SOURCE="${HF_TRAIN_REPO}@${HF_TRAIN_SPLIT}"
    echo "TRACE local parquet missing; falling back to Hugging Face dataset ${TRAIN_SOURCE}" >&2
  fi
fi

# Fail fast if the exported parquet is malformed or points at missing image paths.
python3 - "${TRAIN_SOURCE}" "${PROMPT_KEY}" "${IMAGE_CHECK_LIMIT}" "${VAL_FILES_JSON}" "${CURRICULUM_MODE}" <<'PY'
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
from datasets import load_dataset


def _resolve_source(raw_source: str) -> tuple[str, str, str]:
    if raw_source.endswith(".parquet") or raw_source.startswith(("/", "./", "../")):
        return "local_parquet", str(Path(raw_source).resolve()), "train"
    if "@" in raw_source:
        data_path, data_split = raw_source.split("@", 1)
        return "remote_hf", data_path, data_split or "train"
    return "remote_hf", raw_source, "train"


def _validate_images(images, row_idx: int, *, source_path: Path | None) -> None:
    if not images:
        raise SystemExit(f"No images at sampled row {row_idx}")

    for image_idx, image_record in enumerate(images):
        if hasattr(image_record, "size"):
            continue

        if isinstance(image_record, str):
            resolved = (
                (source_path.parent / image_record).resolve()
                if source_path is not None and not Path(image_record).is_absolute()
                else Path(image_record)
            )
            if not resolved.exists():
                raise SystemExit(
                    f"Missing image file at sampled row {row_idx}, image {image_idx}: {resolved}"
                )
            continue

        if not isinstance(image_record, dict):
            raise SystemExit(
                f"Unsupported image record at sampled row {row_idx}, image {image_idx}: {type(image_record)!r}"
            )

        image_bytes = image_record.get("bytes")
        if image_bytes is not None:
            if not image_bytes:
                raise SystemExit(f"Empty image bytes at sampled row {row_idx}, image {image_idx}")
            continue

        image_path = image_record.get("path")
        if not image_path:
            raise SystemExit(f"Missing image bytes/path at sampled row {row_idx}, image {image_idx}")
        resolved = (
            (source_path.parent / image_path).resolve()
            if source_path is not None and not Path(image_path).is_absolute()
            else Path(image_path)
        )
        if not resolved.exists():
            raise SystemExit(
                f"Missing image file at sampled row {row_idx}, image {image_idx}: {resolved}"
            )

raw_source = str(sys.argv[1])
prompt_key = str(sys.argv[2])
image_check_limit = int(sys.argv[3])
val_files = json.loads(sys.argv[4])
curriculum_mode = str(sys.argv[5])
source_kind, source_path_or_repo, data_split = _resolve_source(raw_source)
source_path = Path(source_path_or_repo).resolve() if source_kind == "local_parquet" else None

if not isinstance(val_files, list):
    raise SystemExit(f"VAL_FILES_JSON must decode to a list, got: {type(val_files)!r}")

required_columns = [prompt_key, "images", "answer_gt", "evidence_gt", "reward_contract"]
if curriculum_mode != "none":
    required_columns.append("bucket_id_str")
if source_kind == "local_parquet":
    if not source_path.exists():
        raise SystemExit(f"TRACE parquet not found: {source_path}")
    parquet_file = pq.ParquetFile(source_path)
    total_rows = parquet_file.metadata.num_rows
    available_columns = set(parquet_file.schema_arrow.names)
    missing_columns = [name for name in required_columns if name not in available_columns]
    if missing_columns:
        raise SystemExit(
            "TRACE parquet is missing required columns: "
            + ", ".join(missing_columns)
            + f". Available columns: {sorted(available_columns)}"
        )

    sample_rows = min(total_rows, max(1, image_check_limit))
    sampled_rows = []
    for batch in parquet_file.iter_batches(batch_size=sample_rows, columns=list(required_columns)):
        sampled_rows.extend(batch.to_pylist())
        if len(sampled_rows) >= sample_rows:
            break
else:
    try:
        remote_dataset = load_dataset(source_path_or_repo, split=data_split)
        total_rows = len(remote_dataset)
        sample_rows = min(total_rows, max(1, image_check_limit))
        sampled_dataset = load_dataset(source_path_or_repo, split=f"{data_split}[:{sample_rows}]")
    except Exception as exc:
        raise SystemExit(
            "Failed to load TRACE training dataset from Hugging Face fallback "
            f"{source_path_or_repo}@{data_split}. "
            "If this repo is private, export HF_TOKEN or HUGGINGFACE_TOKEN first. "
            f"Original error: {exc}"
        ) from exc
    available_columns = set(sampled_dataset.column_names)
    missing_columns = [name for name in required_columns if name not in available_columns]
    if missing_columns:
        raise SystemExit(
            "TRACE HF dataset is missing required columns: "
            + ", ".join(missing_columns)
            + f". Available columns: {sorted(available_columns)}"
        )
    sampled_rows = [sampled_dataset[index] for index in range(min(sample_rows, len(sampled_dataset)))]

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

    _validate_images(row["images"] or [], row_idx, source_path=source_path)

for val_idx, raw_path in enumerate(val_files):
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise SystemExit(f"Invalid validation file entry at index {val_idx}: {raw_path!r}")
    resolved = Path(raw_path).expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"Validation parquet not found at index {val_idx}: {resolved}")

print(
    "TRACE preflight passed:",
    f"rows={total_rows}",
    f"sampled_rows={sample_rows}",
    f"prompt_key={prompt_key}",
    f"source={raw_source}",
    f"resolved={source_path_or_repo}",
    f"kind={source_kind}",
    f"val_files={len(val_files)}",
)
PY

if [[ "${TRACE_PREFLIGHT_ONLY}" == "1" ]]; then
  exit 0
fi

ARGS=(
  python3 -m verl.trainer.main
  config=trace-scripts/config_trace.yaml
  data.train_files="${TRAIN_SOURCE}"
  data.prompt_key="${PROMPT_KEY}"
  data.val_files="${VAL_FILES_JSON}"
  data.curriculum_mode="${CURRICULUM_MODE}"
  data.curriculum_alpha0="${CURRICULUM_ALPHA0}"
  data.curriculum_beta="${CURRICULUM_BETA}"
  data.curriculum_log_interval="${CURRICULUM_LOG_INTERVAL}"
  data.rollout_batch_size="${ROLLOUT_BATCH_SIZE}"
  data.train_dataloader_num_workers="${TRAIN_DATALOADER_NUM_WORKERS}"
  data.val_dataloader_num_workers="${VAL_DATALOADER_NUM_WORKERS}"
  data.filter_overlong_prompts="${FILTER_OVERLONG_PROMPTS}"
  data.filter_overlong_prompts_workers="${FILTER_OVERLONG_PROMPTS_WORKERS}"
  worker.actor.global_batch_size="${ACTOR_GLOBAL_BATCH_SIZE}"
  worker.actor.micro_batch_size_per_device_for_update="${ACTOR_MICRO_BATCH_SIZE_UPDATE}"
  worker.actor.micro_batch_size_per_device_for_experience="${ACTOR_MICRO_BATCH_SIZE_EXPERIENCE}"
  worker.actor.padding_free="${PADDING_FREE}"
  worker.actor.use_torch_compile="${USE_TORCH_COMPILE}"
  worker.actor.model.model_path="${MODEL_PATH}"
  worker.actor.model.freeze_vision_tower="${FREEZE_VISION_TOWER}"
  worker.rollout.n="${ROLLOUT_N}"
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

if [[ -n "${VAL_MAX_TOKENS}" ]]; then
  ARGS+=(worker.rollout.val_override_config.max_tokens=${VAL_MAX_TOKENS})
fi

if [[ -n "${MAX_RESPONSE_LENGTH}" ]]; then
  ARGS+=(data.max_response_length="${MAX_RESPONSE_LENGTH}")
fi

if [[ -n "${CURRICULUM_EPS_FLOOR}" ]]; then
  ARGS+=(data.curriculum_eps_floor="${CURRICULUM_EPS_FLOOR}")
fi

"${ARGS[@]}"
