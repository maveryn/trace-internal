#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

usage() {
  cat <<'USAGE' >&2
Usage:
  scripts/run_trace_rlvr_experiment.sh alpha_ablation <0|0.5|1>
  scripts/run_trace_rlvr_experiment.sh evidence_ablation <gated|additive>
  scripts/run_trace_rlvr_experiment.sh final <qwen3vl4b|qwen3vl8b|qwen25vl7b>

Environment overrides:
  TRAIN_FILES, MODEL_PATH, TRACE_OUTPUT_MODE, TRACE_EVIDENCE_REWARD_FORMULA,
  TOTAL_TRAINING_STEPS, TRAINER_EXPERIMENT_NAME, RESUME_FROM_PATH,
  CUDA_VISIBLE_DEVICES, NUM_GPUS, SAVE_FREQ, TEST_FREQ, VAL_FILES.
Additional arguments after the mode are forwarded to the underlying Hydra run.
USAGE
}

alpha_token() {
  case "$1" in
    0|0.0) echo "0" ;;
    0.5|0_5) echo "0_5" ;;
    1|1.0) echo "1" ;;
    *)
      echo "Unsupported alpha: $1" >&2
      exit 1
      ;;
  esac
}

model_path_for_alias() {
  case "$1" in
    qwen3vl4b) echo "Qwen/Qwen3-VL-4B-Instruct" ;;
    qwen3vl8b) echo "Qwen/Qwen3-VL-8B-Instruct" ;;
    qwen25vl7b|qwen2_5vl7b) echo "Qwen/Qwen2.5-VL-7B-Instruct" ;;
    *)
      echo "Unsupported model alias: $1" >&2
      exit 1
      ;;
  esac
}

validation_files_for_alpha() {
  local token="$1"
  local validation_root="$REPO_ROOT/rlvr/dataset/validation"
  local trace_seed
  case "$token" in
    0) trace_seed="20260506" ;;
    0_5) trace_seed="20260507" ;;
    1) trace_seed="20260508" ;;
    *)
      echo "Unsupported alpha token for validation: $token" >&2
      exit 1
      ;;
  esac
  echo "[$validation_root/mathvista_mini.parquet,$validation_root/mmstar.parquet,$validation_root/charxiv_rq.parquet,$validation_root/embspatialbench.parquet,$validation_root/mmmu_pro_vision.parquet,$validation_root/countqa.parquet,$validation_root/trace_rlvr_validation_1024_variant_alpha${token}_answer_seed${trace_seed}.parquet]"
}

mode="${1:-}"
arg="${2:-}"
if [[ -z "$mode" || -z "$arg" ]]; then
  usage
  exit 1
fi
shift 2

case "$mode" in
  alpha_ablation)
    token="$(alpha_token "$arg")"
    export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-VL-4B-Instruct}"
    export TRACE_OUTPUT_MODE="${TRACE_OUTPUT_MODE:-answer}"
    export TRACE_EVIDENCE_REWARD_FORMULA="${TRACE_EVIDENCE_REWARD_FORMULA:-gated}"
    export TOTAL_TRAINING_STEPS="${TOTAL_TRAINING_STEPS:-250}"
    export TRAIN_FILES="${TRAIN_FILES:-$REPO_ROOT/rlvr/dataset/train/trace_rlvr_train_102400_variant_alpha${token}_answer_retained_seed20260504.parquet}"
    export VAL_FILES="${VAL_FILES:-$(validation_files_for_alpha "$token")}"
    export TRAINER_EXPERIMENT_NAME="${TRAINER_EXPERIMENT_NAME:-trace_qwen3vl4b_alpha${token}_answer_250_seed20260504}"
    ;;
  evidence_ablation)
    case "$arg" in
      gated|additive) ;;
      *)
        echo "Unsupported evidence reward formula: $arg" >&2
        exit 1
        ;;
    esac
    token="$(alpha_token "${TRACE_ALPHA:-0_5}")"
    export MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-VL-4B-Instruct}"
    export TRACE_OUTPUT_MODE="${TRACE_OUTPUT_MODE:-answer_and_evidence}"
    export TRACE_EVIDENCE_REWARD_FORMULA="$arg"
    export TRACE_ANSWER_WEIGHT="${TRACE_ANSWER_WEIGHT:-0.5}"
    export TRACE_EVIDENCE_WEIGHT="${TRACE_EVIDENCE_WEIGHT:-0.5}"
    export TOTAL_TRAINING_STEPS="${TOTAL_TRAINING_STEPS:-250}"
    export TRAIN_FILES="${TRAIN_FILES:-$REPO_ROOT/rlvr/dataset/train/trace_rlvr_train_102400_variant_alpha${token}_answer_retained_seed20260504.parquet}"
    export VAL_FILES="${VAL_FILES:-$(validation_files_for_alpha "$token")}"
    export TRAINER_EXPERIMENT_NAME="${TRAINER_EXPERIMENT_NAME:-trace_qwen3vl4b_alpha${token}_evidence_${arg}_250_seed20260504}"
    ;;
  final)
    export MODEL_PATH="${MODEL_PATH:-$(model_path_for_alias "$arg")}"
    token="$(alpha_token "${TRACE_ALPHA:-0_5}")"
    export TRACE_OUTPUT_MODE="${TRACE_OUTPUT_MODE:-answer}"
    export TRACE_EVIDENCE_REWARD_FORMULA="${TRACE_EVIDENCE_REWARD_FORMULA:-gated}"
    export TOTAL_TRAINING_STEPS="${TOTAL_TRAINING_STEPS:-800}"
    export TRAIN_FILES="${TRAIN_FILES:-$REPO_ROOT/rlvr/dataset/train/trace_rlvr_train_102400_variant_alpha${token}_answer_retained_seed20260504.parquet}"
    export VAL_FILES="${VAL_FILES:-$(validation_files_for_alpha "$token")}"
    export TRAINER_EXPERIMENT_NAME="${TRAINER_EXPERIMENT_NAME:-trace_${arg}_alpha${token}_${TRACE_OUTPUT_MODE}_800_seed20260504}"
    ;;
  *)
    usage
    exit 1
    ;;
esac

if [[ ! -f "$TRAIN_FILES" ]]; then
  echo "Training parquet does not exist: $TRAIN_FILES" >&2
  exit 1
fi

exec "$REPO_ROOT/rlvr/examples/model_runs/run_trace_vl_rlvr.sh" "$@"
