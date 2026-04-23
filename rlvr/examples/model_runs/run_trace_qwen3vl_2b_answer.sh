#!/bin/bash
set -euo pipefail
set -x

DATE_TIME="$(date +%Y%m%d_%H%M%S)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export REPO_ROOT
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
cd "$REPO_ROOT"

NUM_GPUS="${NUM_GPUS:-${SLURM_GPUS_ON_NODE:-8}}"
if [[ -z "${CUDA_VISIBLE_DEVICES:-}" ]]; then
  LAST_GPU_INDEX=$((NUM_GPUS - 1))
  export CUDA_VISIBLE_DEVICES
  CUDA_VISIBLE_DEVICES="$(seq -s, 0 "$LAST_GPU_INDEX")"
else
  NUM_GPUS="$(awk -F, '{print NF}' <<<"$CUDA_VISIBLE_DEVICES")"
fi

MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-VL-2B-Instruct}"
TRAIN_FILES="${TRAIN_FILES:-$REPO_ROOT/dataset/train/trace_rlvr_train_128k_all_tasks_verojson.parquet}"
TRACE_OUTPUT_MODE="${TRACE_OUTPUT_MODE:-answer}"
case "$TRACE_OUTPUT_MODE" in
  answer|answer_only)
    DEFAULT_PROMPT_KEY="prompt_answer"
    DEFAULT_TRACE_REWARD_MODE="answer"
    DEFAULT_TRACE_SYSTEM_PROMPT="$REPO_ROOT/examples/prompts/trace_vero_json_system_prompt_answer.txt"
    ;;
  answer_and_evidence|evidence)
    DEFAULT_PROMPT_KEY="prompt_answer_and_evidence"
    DEFAULT_TRACE_REWARD_MODE="answer_and_evidence"
    DEFAULT_TRACE_SYSTEM_PROMPT="$REPO_ROOT/examples/prompts/trace_vero_json_system_prompt_answer_and_evidence.txt"
    ;;
  *)
    echo "Unsupported TRACE_OUTPUT_MODE: $TRACE_OUTPUT_MODE" >&2
    exit 1
    ;;
esac
PROMPT_KEY="${PROMPT_KEY:-$DEFAULT_PROMPT_KEY}"
TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-$DEFAULT_TRACE_REWARD_MODE}"
TRACE_SYSTEM_PROMPT="${TRACE_SYSTEM_PROMPT:-$DEFAULT_TRACE_SYSTEM_PROMPT}"
TRAINER_EXPERIMENT_SUFFIX="${TRAINER_EXPERIMENT_SUFFIX:-trace_qwen3_2b_answer}"
TRAINER_EXPERIMENT_NAME="${TRAINER_EXPERIMENT_NAME:-${TRAINER_EXPERIMENT_SUFFIX}_${DATE_TIME}}"

export MODEL_PATH
export TRAIN_FILES
export TRACE_OUTPUT_MODE
export PROMPT_KEY
export TRACE_REWARD_MODE
export TRACE_SYSTEM_PROMPT
export TRAINER_EXPERIMENT_NAME
export WANDB_MODE="${WANDB_MODE:-online}"

python3 -m verl.trainer.main_ppo \
  --config-path="$SCRIPT_DIR/config" \
  --config-name='trace_qwen3vl_trace' \
  trainer.n_gpus_per_node="$NUM_GPUS" \
  actor_rollout_ref.actor.fsdp_config.model_dtype=bfloat16 \
  actor_rollout_ref.ref.fsdp_config.model_dtype=bfloat16 \
  critic.model.fsdp_config.model_dtype=bfloat16 \
  "$@"
