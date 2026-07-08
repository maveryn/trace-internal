#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RLVR_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TRACE_ROOT="$(cd "$RLVR_ROOT/.." && pwd)"
export REPO_ROOT="$RLVR_ROOT"
export ROOT_PATH="${ROOT_PATH:-$TRACE_ROOT}"
export PYTHONPATH="${RLVR_ROOT}:${TRACE_ROOT}:${PYTHONPATH:-}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"

HF_TOKEN_FILE="${HF_TOKEN_FILE:-$TRACE_ROOT/hf-token.txt}"
if [[ -z "${HF_TOKEN:-}" && -f "$HF_TOKEN_FILE" ]]; then
  HF_TOKEN="$(< "$HF_TOKEN_FILE")"
  export HF_TOKEN
fi

if [[ "${TRACE_RLVR_XTRACE:-0}" != "0" && "${TRACE_RLVR_XTRACE,,}" != "false" && "${TRACE_RLVR_XTRACE,,}" != "no" ]]; then
  set -x
fi

cd "$RLVR_ROOT"

if [[ -z "${CUDA_VISIBLE_DEVICES:-}" ]]; then
  if [[ -z "${NUM_GPUS:-}" ]]; then
    if command -v nvidia-smi >/dev/null 2>&1; then
      DETECTED_GPUS="$(nvidia-smi --list-gpus | wc -l)"
      if [[ "$DETECTED_GPUS" -gt 0 ]]; then
        NUM_GPUS="$DETECTED_GPUS"
      else
        NUM_GPUS="${SLURM_GPUS_ON_NODE:-1}"
      fi
    else
      NUM_GPUS="${SLURM_GPUS_ON_NODE:-1}"
    fi
  fi
  if [[ "$NUM_GPUS" -lt 1 ]]; then
    echo "NUM_GPUS must be >= 1, got $NUM_GPUS" >&2
    exit 1
  fi
  LAST_GPU_INDEX=$((NUM_GPUS - 1))
  export CUDA_VISIBLE_DEVICES
  CUDA_VISIBLE_DEVICES="$(seq -s, 0 "$LAST_GPU_INDEX")"
else
  NUM_GPUS="$(awk -F, '{print NF}' <<<"$CUDA_VISIBLE_DEVICES")"
fi

MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-3B-Instruct}"
if [[ -z "${MAX_PROMPT_LENGTH:-}" ]]; then
  MODEL_PATH_LOWER="${MODEL_PATH,,}"
  case "$MODEL_PATH_LOWER" in
    *qwen2.5-vl*|*qwen2_5-vl*|*qwen25vl*)
      MAX_PROMPT_LENGTH=2048
      ;;
    *qwen3-vl*|*qwen3vl*)
      MAX_PROMPT_LENGTH=1536
      ;;
    *)
      MAX_PROMPT_LENGTH=1536
      ;;
  esac
fi

TRAIN_FILES="${TRAIN_FILES:-maveryn/trace@train}"
VAL_FILES="${VAL_FILES:-maveryn/trace@validation}"
TRACE_OUTPUT_MODE="${TRACE_OUTPUT_MODE:-answer}"
case "$TRACE_OUTPUT_MODE" in
  answer|answer_only)
    DEFAULT_PROMPT_KEY="prompt_answer_only"
    DEFAULT_TRACE_REWARD_MODE="answer"
    DEFAULT_TRACE_SYSTEM_PROMPT="$RLVR_ROOT/examples/prompts/trace_vero_json_system_prompt_answer.txt"
    ;;
  answer_and_annotation|annotation)
    DEFAULT_PROMPT_KEY="prompt_answer_and_annotation"
    DEFAULT_TRACE_REWARD_MODE="answer_and_annotation"
    DEFAULT_TRACE_SYSTEM_PROMPT="$RLVR_ROOT/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation.txt"
    ;;
  *)
    echo "Unsupported TRACE_OUTPUT_MODE: $TRACE_OUTPUT_MODE" >&2
    exit 1
    ;;
esac

PROMPT_KEY="${PROMPT_KEY:-$DEFAULT_PROMPT_KEY}"
TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-$DEFAULT_TRACE_REWARD_MODE}"
TRACE_SYSTEM_PROMPT="${TRACE_SYSTEM_PROMPT:-$DEFAULT_TRACE_SYSTEM_PROMPT}"

if [[ -z "${TRAINER_EXPERIMENT_NAME:-}" ]]; then
  MODEL_SLUG="$(basename "$MODEL_PATH" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_' '_')"
  TRAINER_EXPERIMENT_SUFFIX="${TRAINER_EXPERIMENT_SUFFIX:-trace_${MODEL_SLUG}_${TRACE_OUTPUT_MODE}}"
  TRAINER_EXPERIMENT_NAME="$TRAINER_EXPERIMENT_SUFFIX"
  if [[ "${TRAINER_APPEND_TIMESTAMP:-0}" != "0" && "${TRAINER_APPEND_TIMESTAMP,,}" != "false" && "${TRAINER_APPEND_TIMESTAMP,,}" != "no" ]]; then
    TRAINER_EXPERIMENT_NAME="${TRAINER_EXPERIMENT_NAME}_$(date +%Y%m%d_%H%M%S)"
  fi
fi

TOTAL_TRAINING_STEPS="${TOTAL_TRAINING_STEPS:-900}"
SAVE_FREQ="${SAVE_FREQ:-100}"
TEST_FREQ="${TEST_FREQ:-100}"
TRAIN_BATCH_SIZE="${TRAIN_BATCH_SIZE:-256}"
VAL_BATCH_SIZE="${VAL_BATCH_SIZE:-512}"
ROLLOUT_N="${ROLLOUT_N:-8}"
MAX_ACTOR_CKPT_TO_KEEP="${MAX_ACTOR_CKPT_TO_KEEP:-1}"
MAX_CRITIC_CKPT_TO_KEEP="${MAX_CRITIC_CKPT_TO_KEEP:-1}"

export MODEL_PATH
export MAX_PROMPT_LENGTH
export MAX_RESPONSE_LENGTH="${MAX_RESPONSE_LENGTH:-2048}"
export VAL_MAX_RESPONSE_LENGTH="${VAL_MAX_RESPONSE_LENGTH:-1536}"
export TRACE_VAL_MAX_RESPONSE_LENGTH="${TRACE_VAL_MAX_RESPONSE_LENGTH:-2048}"
export TRAIN_FILES
export TRACE_OUTPUT_MODE
export PROMPT_KEY
export TRACE_REWARD_MODE
export TRACE_SYSTEM_PROMPT
export TRACE_ANNOTATION_REWARD_FORMULA="${TRACE_ANNOTATION_REWARD_FORMULA:-gated}"
export TRACE_ANSWER_SCORING="${TRACE_ANSWER_SCORING:-exact_json}"
export TRACE_ANSWER_WEIGHT="${TRACE_ANSWER_WEIGHT:-0.5}"
export TRACE_ANNOTATION_WEIGHT="${TRACE_ANNOTATION_WEIGHT:-0.5}"
export TRACE_FORMAT_WEIGHT="${TRACE_FORMAT_WEIGHT:-0.05}"
export VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.9}"
export VLLM_MAX_NUM_BATCHED_TOKENS="${VLLM_MAX_NUM_BATCHED_TOKENS:-32768}"
export VLLM_MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-1024}"
export VLLM_ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-FLASH_ATTN}"
export VLLM_USE_TRTLLM_ATTENTION="${VLLM_USE_TRTLLM_ATTENTION:-false}"
export FILTER_OVERLONG_PROMPTS="${FILTER_OVERLONG_PROMPTS:-true}"
export FILTER_OVERLONG_PROMPTS_WORKERS="${FILTER_OVERLONG_PROMPTS_WORKERS:-32}"
export TRACE_PROMPT_TRUNCATION="${TRACE_PROMPT_TRUNCATION:-error}"
export TRAINER_EXPERIMENT_NAME
export WANDB_MODE="${WANDB_MODE:-online}"

cmd=(
  python3 -m verl.trainer.main_ppo
  --config-path="$SCRIPT_DIR/config"
  --config-name=trace_qwen3vl_trace
  trainer.n_gpus_per_node="$NUM_GPUS"
  trainer.total_training_steps="$TOTAL_TRAINING_STEPS"
  trainer.save_freq="$SAVE_FREQ"
  trainer.test_freq="$TEST_FREQ"
  trainer.max_actor_ckpt_to_keep="$MAX_ACTOR_CKPT_TO_KEEP"
  trainer.max_critic_ckpt_to_keep="$MAX_CRITIC_CKPT_TO_KEEP"
  actor_rollout_ref.model.path="$MODEL_PATH"
  data.train_files="$TRAIN_FILES"
  data.trace_output_mode="$TRACE_OUTPUT_MODE"
  data.prompt_key="$PROMPT_KEY"
  data.system_prompt="$TRACE_SYSTEM_PROMPT"
  data.train_batch_size="$TRAIN_BATCH_SIZE"
  data.val_batch_size="$VAL_BATCH_SIZE"
  data.max_prompt_length="$MAX_PROMPT_LENGTH"
  data.max_response_length="$MAX_RESPONSE_LENGTH"
  data.validation_style="${VALIDATION_STYLE:-standard}"
  data.filter_overlong_prompts="$FILTER_OVERLONG_PROMPTS"
  data.filter_overlong_prompts_workers="$FILTER_OVERLONG_PROMPTS_WORKERS"
  data.truncation="$TRACE_PROMPT_TRUNCATION"
  actor_rollout_ref.rollout.n="$ROLLOUT_N"
  actor_rollout_ref.rollout.val_kwargs.max_tokens="$VAL_MAX_RESPONSE_LENGTH"
  data.trace_val_max_response_length="$TRACE_VAL_MAX_RESPONSE_LENGTH"
  custom_reward_function.reward_kwargs.trace_output_mode="$TRACE_OUTPUT_MODE"
  custom_reward_function.reward_kwargs.trace_reward_mode="$TRACE_REWARD_MODE"
  custom_reward_function.reward_kwargs.trace_answer_scoring="$TRACE_ANSWER_SCORING"
  custom_reward_function.reward_kwargs.trace_annotation_reward_formula="$TRACE_ANNOTATION_REWARD_FORMULA"
  custom_reward_function.reward_kwargs.trace_answer_weight="$TRACE_ANSWER_WEIGHT"
  custom_reward_function.reward_kwargs.trace_annotation_weight="$TRACE_ANNOTATION_WEIGHT"
  custom_reward_function.reward_kwargs.trace_format_weight="$TRACE_FORMAT_WEIGHT"
  actor_rollout_ref.actor.fsdp_config.model_dtype=bfloat16
  actor_rollout_ref.ref.fsdp_config.model_dtype=bfloat16
  critic.model.fsdp_config.model_dtype=bfloat16
)

cmd+=(actor_rollout_ref.rollout.gpu_memory_utilization="$VLLM_GPU_MEMORY_UTILIZATION")
cmd+=(actor_rollout_ref.rollout.max_num_batched_tokens="$VLLM_MAX_NUM_BATCHED_TOKENS")
cmd+=(actor_rollout_ref.rollout.max_num_seqs="$VLLM_MAX_NUM_SEQS")
if [[ -n "${VAL_FILES:-}" ]]; then
  cmd+=(data.val_files="$VAL_FILES")
fi
if [[ -n "${RESUME_FROM_PATH:-}" ]]; then
  cmd+=(trainer.resume_mode="${RESUME_MODE:-resume_path}")
  cmd+=(trainer.resume_from_path="$RESUME_FROM_PATH")
elif [[ -n "${RESUME_MODE:-}" ]]; then
  cmd+=(trainer.resume_mode="$RESUME_MODE")
fi

if [[ "${TRACE_RLVR_DRY_RUN:-0}" != "0" && "${TRACE_RLVR_DRY_RUN,,}" != "false" && "${TRACE_RLVR_DRY_RUN,,}" != "no" ]]; then
  printf '%q ' "${cmd[@]}" "$@"
  printf '\n'
  exit 0
fi

"${cmd[@]}" "$@"
