#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-.:rlvr}"
export TRANSFORMERS_NO_TF="${TRANSFORMERS_NO_TF:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export VLLM_LOGGING_LEVEL="${VLLM_LOGGING_LEVEL:-WARN}"
export PYTORCH_ALLOC_CONF="${PYTORCH_ALLOC_CONF:-expandable_segments:True}"

PARQUET="${PARQUET:-rlvr/dataset/prompt_pilot/trace_answer_prompt_pilot_20k_seed20260703.parquet}"
OUTPUT_DIR="${OUTPUT_DIR:-rlvr/outputs/prompt_pilot/qwen25vl3b_trace20k_seed20260703/short_json_tail}"
MODEL="${MODEL:-Qwen/Qwen2.5-VL-3B-Instruct}"
SYSTEM_PROMPT="${SYSTEM_PROMPT:-rlvr/examples/prompts/trace_prompt_pilot/answer_short_json_tail.txt}"
TRACE_OUTPUT_MODE="${TRACE_OUTPUT_MODE:-answer}"
PROMPT_KEY="${PROMPT_KEY:-prompt_answer}"
TRACE_REWARD_MODE="${TRACE_REWARD_MODE:-answer}"
TRACE_ANSWER_SCORING="${TRACE_ANSWER_SCORING:-legacy_strict}"
ROLLOUTS_PER_PROMPT="${ROLLOUTS_PER_PROMPT:-1}"
TEMPERATURE="${TEMPERATURE:-0.0}"

START_INDEX="${START_INDEX:-0}"
COUNT="${COUNT:-20000}"

python rlvr/scripts/trace_curriculum_probe.py \
  --parquet "${PARQUET}" \
  --output-dir "${OUTPUT_DIR}" \
  --model "${MODEL}" \
  --system-prompt "${SYSTEM_PROMPT}" \
  --trace-output-mode "${TRACE_OUTPUT_MODE}" \
  --prompt-key "${PROMPT_KEY}" \
  --trace-reward-mode "${TRACE_REWARD_MODE}" \
  --trace-answer-scoring "${TRACE_ANSWER_SCORING}" \
  --start-index "${START_INDEX}" \
  --count "${COUNT}" \
  --rollouts-per-prompt "${ROLLOUTS_PER_PROMPT}" \
  --temperature "${TEMPERATURE}" \
  --max-tokens 4096 \
  --max-prompt-length "${MAX_PROMPT_LENGTH:-2048}" \
  --max-model-len 8192 \
  --batch-size "${BATCH_SIZE:-1024}" \
  --max-num-batched-tokens "${MAX_NUM_BATCHED_TOKENS:-65536}" \
  --max-num-seqs "${MAX_NUM_SEQS:-256}" \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.92}" \
  --max-pixels 1280000 \
  --prefetch-workers "${PREFETCH_WORKERS:-4}" \
  --no-enforce-eager \
  --write-per-rollout \
  --per-rollout-response-mode truncated \
  --per-rollout-response-max-chars "${PER_ROLLOUT_RESPONSE_MAX_CHARS:-4000}"
