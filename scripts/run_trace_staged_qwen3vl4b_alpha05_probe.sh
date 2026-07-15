#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3,4,5,6,7}"
export PYTHONPATH="${REPO_ROOT}/rlvr${PYTHONPATH:+:${PYTHONPATH}}"

DATASET="${DATASET:-rlvr/dataset/train/trace_rlvr_train_200000_query_id_alpha0_5_answer_seed20260504.parquet}"
OUTPUT_DIR="${OUTPUT_DIR:-rlvr/outputs/curriculum_probe/qwen3vl4b_200k_query_id_alpha0_5_answer_staged4to16_seed20260504}"
MODEL="${MODEL:-Qwen/Qwen3-VL-4B-Instruct}"

# Per-GPU rollout budget for each vLLM generate() wave. With STAGE_ROLLOUTS=4,
# BATCH_SIZE=4096 sends 1024 prompts per worker per wave.
BATCH_SIZE="${BATCH_SIZE:-4096}"
REPLICA_WORKERS="${REPLICA_WORKERS:-8}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
STAGE_ROLLOUTS="${STAGE_ROLLOUTS:-4}"
MAX_ROLLOUTS="${MAX_ROLLOUTS:-16}"
EASY_RATE="${EASY_RATE:-0.875}"

MAX_PROMPT_LENGTH="${MAX_PROMPT_LENGTH:-1536}"
MAX_TOKENS="${MAX_TOKENS:-2048}"
MAX_PIXELS="${MAX_PIXELS:-1048576}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-65536}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-4096}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.95}"
TEMPERATURE="${TEMPERATURE:-1.0}"
SEED="${SEED:-18}"
TRACE_ANSWER_SCORING="${TRACE_ANSWER_SCORING:-exact_json}"
RESUME="${RESUME:-0}"
if [[ "${RESUME}" != "0" && "${RESUME,,}" != "false" && "${RESUME,,}" != "no" ]]; then
  OVERWRITE="${OVERWRITE:-0}"
else
  OVERWRITE="${OVERWRITE:-1}"
fi
FILTER_OVERLONG_PROMPTS="${FILTER_OVERLONG_PROMPTS:-0}"
CPU_THREADS_PER_WORKER="${CPU_THREADS_PER_WORKER:-4}"
DISABLE_TRTLLM_ATTENTION="${DISABLE_TRTLLM_ATTENTION:-1}"
ATTENTION_BACKEND="${ATTENTION_BACKEND:-FLASH_ATTN}"
PREFETCH_WORKERS="${PREFETCH_WORKERS:-1}"
SCORE_WORKERS="${SCORE_WORKERS:-1}"
SCORE_BACKLOG="${SCORE_BACKLOG:-2}"

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${CPU_THREADS_PER_WORKER}}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-${CPU_THREADS_PER_WORKER}}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-${CPU_THREADS_PER_WORKER}}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-${CPU_THREADS_PER_WORKER}}"
export RAYON_NUM_THREADS="${RAYON_NUM_THREADS:-${CPU_THREADS_PER_WORKER}}"
export VLLM_ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-${ATTENTION_BACKEND}}"

cmd=(
  python rlvr/scripts/trace_staged_curriculum_probe.py
  --parquet "${DATASET}"
  --output-dir "${OUTPUT_DIR}"
  --model "${MODEL}"
  --replica-workers "${REPLICA_WORKERS}"
  --tensor-parallel-size "${TENSOR_PARALLEL_SIZE}"
  --batch-size "${BATCH_SIZE}"
  --stage-rollouts "${STAGE_ROLLOUTS}"
  --max-rollouts "${MAX_ROLLOUTS}"
  --easy-rate "${EASY_RATE}"
  --max-prompt-length "${MAX_PROMPT_LENGTH}"
  --max-tokens "${MAX_TOKENS}"
  --max-pixels "${MAX_PIXELS}"
  --max-model-len "${MAX_MODEL_LEN}"
  --max-num-batched-tokens "${MAX_NUM_BATCHED_TOKENS}"
  --max-num-seqs "${MAX_NUM_SEQS}"
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}"
  --temperature "${TEMPERATURE}"
  --seed "${SEED}"
  --trace-answer-scoring "${TRACE_ANSWER_SCORING}"
  --prefetch-workers "${PREFETCH_WORKERS}"
  --score-workers "${SCORE_WORKERS}"
  --score-backlog "${SCORE_BACKLOG}"
)

if [[ -n "${ATTENTION_BACKEND}" ]]; then
  cmd+=(--attention-backend "${ATTENTION_BACKEND}")
fi

if [[ "${DISABLE_TRTLLM_ATTENTION}" != "0" && "${DISABLE_TRTLLM_ATTENTION,,}" != "false" && "${DISABLE_TRTLLM_ATTENTION,,}" != "no" ]]; then
  cmd+=(--disable-trtllm-attention)
fi

if [[ "${RESUME}" != "0" && "${RESUME,,}" != "false" && "${RESUME,,}" != "no" ]]; then
  cmd+=(--resume)
fi

if [[ "${OVERWRITE}" != "0" && "${OVERWRITE,,}" != "false" && "${OVERWRITE,,}" != "no" ]]; then
  cmd+=(--overwrite)
fi

if [[ "${FILTER_OVERLONG_PROMPTS}" != "0" && "${FILTER_OVERLONG_PROMPTS,,}" != "false" && "${FILTER_OVERLONG_PROMPTS,,}" != "no" ]]; then
  cmd+=(--filter-overlong-prompts)
fi

echo "Trace staged Qwen3-VL-4B curriculum probe"
echo "  dataset: ${DATASET}"
echo "  output: ${OUTPUT_DIR}"
echo "  model: ${MODEL}"
echo "  gpus: ${CUDA_VISIBLE_DEVICES}"
echo "  replica_workers: ${REPLICA_WORKERS}"
echo "  tensor_parallel_size: ${TENSOR_PARALLEL_SIZE}"
echo "  stage_rollouts: ${STAGE_ROLLOUTS}"
echo "  max_rollouts: ${MAX_ROLLOUTS}"
echo "  easy_rate: ${EASY_RATE}"
echo "  batch_size_per_worker: ${BATCH_SIZE}"
echo "  max_num_batched_tokens: ${MAX_NUM_BATCHED_TOKENS}"
echo "  max_num_seqs: ${MAX_NUM_SEQS}"
echo "  gpu_memory_utilization: ${GPU_MEMORY_UTILIZATION}"
echo "  cpu_threads_per_worker: ${CPU_THREADS_PER_WORKER}"
echo "  prefetch_workers_per_worker: ${PREFETCH_WORKERS}"
echo "  score_workers_per_worker: ${SCORE_WORKERS}"
echo "  score_backlog_per_worker: ${SCORE_BACKLOG}"
echo "  resume: ${RESUME}"
echo "  overwrite: ${OVERWRITE}"
echo "  disable_trtllm_attention: ${DISABLE_TRTLLM_ATTENTION}"
echo "  attention_backend: ${ATTENTION_BACKEND:-auto}"
echo "  max_prompt_length: ${MAX_PROMPT_LENGTH}"
echo "  max_tokens: ${MAX_TOKENS}"

"${cmd[@]}"
