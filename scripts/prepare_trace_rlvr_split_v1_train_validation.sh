#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

export SEED="${SEED:-42}"
export TRAIN_PER_TASK="${TRAIN_PER_TASK:-256}"
export VALIDATION_PER_TASK="${VALIDATION_PER_TASK:-25}"
export IMAGE_CAP="${IMAGE_CAP:-1280000}"
export OUTPUT_ROOT="${OUTPUT_ROOT:-out/rlvr_task_split_v1_seed${SEED}}"
export CODE_HASH="${CODE_HASH:-local}"
export DRY_RUN="${DRY_RUN:-0}"

export TRAIN_NAME="${TRAIN_NAME:-trace_rlvr_train_230400_task_split_v1_seed${SEED}}"
export VALIDATION_NAME="${VALIDATION_NAME:-trace_rlvr_validation_2500_task_split_v1_seed${SEED}}"

export TRAIN_PARQUET="${TRAIN_PARQUET:-rlvr/dataset/train/${TRAIN_NAME}.parquet}"
export VALIDATION_PARQUET="${VALIDATION_PARQUET:-rlvr/dataset/validation/${VALIDATION_NAME}.parquet}"

exec python scripts/prepare_trace_rlvr_split_v1_train_validation.py
