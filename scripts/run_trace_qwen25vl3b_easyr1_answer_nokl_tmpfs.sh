#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
BACKEND_DIR="${REPO_ROOT}/rlvr/easyr1_backend"
cd "$BACKEND_DIR"

if [[ -f /home/shadeform/venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source /home/shadeform/venv/bin/activate
fi

export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-true}"
export HF_HOME="${HF_HOME:-/dev/shm/trace_rlvr/cache/huggingface}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-/dev/shm/trace_rlvr/cache/huggingface/datasets}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/dev/shm/trace_rlvr/cache/huggingface/transformers}"
export RAY_TMPDIR="${RAY_TMPDIR:-/dev/shm/trace_rlvr/ray}"
export WANDB_DIR="${WANDB_DIR:-/dev/shm/trace_rlvr/wandb}"
export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH:-}"
mkdir -p "$HF_HOME" "$HF_DATASETS_CACHE" "$TRANSFORMERS_CACHE" "$RAY_TMPDIR" "$WANDB_DIR"

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-VL-3B-Instruct}"
TRAIN_FILES="${TRAIN_FILES:-maveryn/trace@train}"
VAL_FILES="${VAL_FILES:-/dev/shm/trace_rlvr/datasets/trace_rlvr_validation_500_5_per_task_seed42.parquet}"
SYSTEM_PROMPT_FILE="${SYSTEM_PROMPT_FILE:-../examples/prompts/trace_vero_json_system_prompt_answer.txt}"
REWARD_FUNCTION="${REWARD_FUNCTION:-examples/reward_function/trace_rlvr.py:compute_score}"

MAX_STEPS="${MAX_STEPS:-600}"
SAVE_FREQ="${SAVE_FREQ:-100}"
VAL_FREQ="${VAL_FREQ:-100}"
SAVE_LIMIT="${SAVE_LIMIT:-8}"
VAL_BEFORE_TRAIN="${VAL_BEFORE_TRAIN:-false}"
FIND_LAST_CHECKPOINT="${FIND_LAST_CHECKPOINT:-true}"
LOAD_CHECKPOINT_PATH="${LOAD_CHECKPOINT_PATH:-null}"

ROLLOUT_BATCH_SIZE="${ROLLOUT_BATCH_SIZE:-128}"
ACTOR_GLOBAL_BATCH_SIZE="${ACTOR_GLOBAL_BATCH_SIZE:-128}"
ROLLOUT_N="${ROLLOUT_N:-8}"
VAL_BATCH_SIZE="${VAL_BATCH_SIZE:-1024}"
MAX_PROMPT_LENGTH="${MAX_PROMPT_LENGTH:-2048}"
MAX_RESPONSE_LENGTH="${MAX_RESPONSE_LENGTH:-2048}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.6}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-8192}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-2}"
N_GPUS="${N_GPUS:-8}"

PROJECT_NAME="${PROJECT_NAME:-trace_easyr1}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-trace_qwen25vl3b_easyr1_answer_nokl_bsz${ROLLOUT_BATCH_SIZE}_rollout${ROLLOUT_N}_val500_${RUN_STAMP}}"
SAVE_CHECKPOINT_PATH="${SAVE_CHECKPOINT_PATH:-/dev/shm/trace_rlvr/easyr1_checkpoints/${EXPERIMENT_NAME}}"

echo "[trace-easyr1] experiment=${EXPERIMENT_NAME}"
echo "[trace-easyr1] checkpoint_path=${SAVE_CHECKPOINT_PATH}"
echo "[trace-easyr1] max_steps=${MAX_STEPS} save_freq=${SAVE_FREQ} val_freq=${VAL_FREQ}"
echo "[trace-easyr1] model=${MODEL_PATH}"

python3 -m verl.trainer.main \
  config=examples/config.yaml \
  data.train_files="$TRAIN_FILES" \
  data.val_files="$VAL_FILES" \
  data.prompt_key=prompt_answer_only \
  data.answer_key=answer_gt \
  data.format_prompt=null \
  data.system_prompt=null \
  data.system_prompt_file="$SYSTEM_PROMPT_FILE" \
  data.rollout_batch_size="$ROLLOUT_BATCH_SIZE" \
  data.val_batch_size="$VAL_BATCH_SIZE" \
  data.max_prompt_length="$MAX_PROMPT_LENGTH" \
  data.max_response_length="$MAX_RESPONSE_LENGTH" \
  data.filter_overlong_prompts=false \
  algorithm.adv_estimator=grpo \
  algorithm.disable_kl=true \
  algorithm.use_kl_loss=false \
  algorithm.kl_coef=0 \
  worker.actor.model.model_path="$MODEL_PATH" \
  worker.actor.model.tokenizer_path="$MODEL_PATH" \
  worker.actor.model.trust_remote_code=false \
  worker.actor.model.freeze_vision_tower=false \
  worker.actor.global_batch_size="$ACTOR_GLOBAL_BATCH_SIZE" \
  worker.actor.micro_batch_size_per_device_for_experience=2 \
  worker.actor.micro_batch_size_per_device_for_update=1 \
  worker.actor.optim.lr=1e-6 \
  worker.actor.optim.lr_warmup_ratio=0 \
  worker.actor.optim.lr_scheduler_type=constant \
  worker.actor.offload.offload_params=true \
  worker.actor.offload.offload_optimizer=true \
  worker.actor.clip_ratio_low=0.2 \
  worker.actor.clip_ratio_high=0.3 \
  worker.actor.clip_ratio_dual=3.0 \
  worker.actor.loss_avg_mode=token \
  worker.actor.ppo_epochs=1 \
  worker.rollout.n="$ROLLOUT_N" \
  worker.rollout.temperature=1.0 \
  worker.rollout.top_p=1.0 \
  worker.rollout.gpu_memory_utilization="$GPU_MEMORY_UTILIZATION" \
  worker.rollout.max_num_batched_tokens="$MAX_NUM_BATCHED_TOKENS" \
  worker.rollout.tensor_parallel_size="$TENSOR_PARALLEL_SIZE" \
  worker.rollout.val_override_config.temperature=0.6 \
  worker.rollout.val_override_config.top_p=0.95 \
  worker.rollout.val_override_config.n=1 \
  worker.reward.reward_function="$REWARD_FUNCTION" \
  worker.reward.reward_function_kwargs.trace_output_mode=answer \
  worker.reward.reward_function_kwargs.trace_reward_mode=answer \
  worker.reward.reward_function_kwargs.trace_answer_scoring=exact_json \
  worker.reward.reward_function_kwargs.trace_annotation_reward_formula=gated \
  worker.reward.reward_function_kwargs.trace_answer_weight=0.5 \
  worker.reward.reward_function_kwargs.trace_annotation_weight=0.5 \
  worker.reward.reward_function_kwargs.trace_format_weight=0.05 \
  trainer.project_name="$PROJECT_NAME" \
  trainer.experiment_name="$EXPERIMENT_NAME" \
  trainer.logger='["console","wandb"]' \
  trainer.n_gpus_per_node="$N_GPUS" \
  trainer.max_steps="$MAX_STEPS" \
  trainer.save_freq="$SAVE_FREQ" \
  trainer.val_freq="$VAL_FREQ" \
  trainer.save_limit="$SAVE_LIMIT" \
  trainer.val_before_train="$VAL_BEFORE_TRAIN" \
  trainer.save_checkpoint_path="$SAVE_CHECKPOINT_PATH" \
  trainer.load_checkpoint_path="$LOAD_CHECKPOINT_PATH" \
  trainer.find_last_checkpoint="$FIND_LAST_CHECKPOINT"
