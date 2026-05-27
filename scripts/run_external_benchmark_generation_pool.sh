#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGET="${1:-all}" # base | ablations | all
LOG_ROOT="${LOG_ROOT:-$ROOT_DIR/benchmark/logs/generation/$(date -u +%Y%m%dT%H%M%SZ)}"
BATCH_SIZE="${BATCH_SIZE:-2048}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-512}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-262144}"
MAX_TOKENS_OVERRIDE="${MAX_TOKENS_OVERRIDE:-4096}"
PREFETCH_WORKERS="${PREFETCH_WORKERS:-4}"
PREFETCH_BATCHES="${PREFETCH_BATCHES:-2}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
START_DELAY="${START_DELAY:-5}"
STALE_AFTER_SEC="${STALE_AFTER_SEC:-900}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-2}"

mkdir -p "$LOG_ROOT"
PIDS=()
NAMES=()

launch_worker() {
  local gpu="$1"
  local model="$2"
  local slug="$3"
  local run_set="$4"
  local worker_id="$5"
  local log="$LOG_ROOT/${worker_id}.log"

  if [[ "$model" == "$ROOT_DIR"/* && ! -f "$model/config.json" ]]; then
    echo "[missing model export] $model" >&2
    echo "Run: bash scripts/export_trace_ablation_hf_checkpoints.sh" >&2
    exit 1
  fi

  echo "[launch] gpu=$gpu model=$slug run_set=$run_set log=$log"
  CUDA_VISIBLE_DEVICES="$gpu" python -u scripts/run_external_benchmark_generation_queue.py \
    --gpu "$gpu" \
    --model "$model" \
    --model-slug "$slug" \
    --run-set "$run_set" \
    --worker-id "$worker_id" \
    --batch-size "$BATCH_SIZE" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --max-num-seqs "$MAX_NUM_SEQS" \
    --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS" \
    --max-tokens-override "$MAX_TOKENS_OVERRIDE" \
    --prefetch-workers "$PREFETCH_WORKERS" \
    --prefetch-batches "$PREFETCH_BATCHES" \
    --max-model-len "$MAX_MODEL_LEN" \
    --stale-after-sec "$STALE_AFTER_SEC" \
    --max-attempts "$MAX_ATTEMPTS" \
    >"$log" 2>&1 &
  local pid=$!
  PIDS+=("$pid")
  NAMES+=("$worker_id")
  echo "[pid] worker=$worker_id pid=$pid"
  if [[ "${START_DELAY}" != "0" ]]; then
    sleep "$START_DELAY"
  fi
}

if [[ "$TARGET" == "base" || "$TARGET" == "all" ]]; then
  launch_worker 6 "Qwen/Qwen3-VL-4B-Instruct" "qwen3-vl-4b-instruct" "remaining_base" "base_gpu6"
  launch_worker 7 "Qwen/Qwen3-VL-4B-Instruct" "qwen3-vl-4b-instruct" "remaining_base" "base_gpu7"
fi

if [[ "$TARGET" == "ablations" || "$TARGET" == "all" ]]; then
  launch_worker 0 "$ROOT_DIR/checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha0_answer_step250" "trace-qwen3vl4b-alpha0-answer-step250" "full" "alpha0_gpu0"
  launch_worker 1 "$ROOT_DIR/checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha0_answer_step250" "trace-qwen3vl4b-alpha0-answer-step250" "full" "alpha0_gpu1"
  launch_worker 2 "$ROOT_DIR/checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha0_5_answer_step250" "trace-qwen3vl4b-alpha0-5-answer-step250" "full" "alpha05_gpu2"
  launch_worker 3 "$ROOT_DIR/checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha0_5_answer_step250" "trace-qwen3vl4b-alpha0-5-answer-step250" "full" "alpha05_gpu3"
  launch_worker 4 "$ROOT_DIR/checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha1_answer_step250" "trace-qwen3vl4b-alpha1-answer-step250" "full" "alpha1_gpu4"
  launch_worker 5 "$ROOT_DIR/checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha1_answer_step250" "trace-qwen3vl4b-alpha1-answer-step250" "full" "alpha1_gpu5"
fi

if [[ "$TARGET" != "base" && "$TARGET" != "ablations" && "$TARGET" != "all" ]]; then
  echo "Usage: $0 [base|ablations|all]" >&2
  exit 2
fi

status=0
for i in "${!PIDS[@]}"; do
  pid="${PIDS[$i]}"
  name="${NAMES[$i]}"
  if wait "$pid"; then
    echo "[done] worker=$name pid=$pid rc=0"
  else
    rc=$?
    echo "[failed] worker=$name pid=$pid rc=$rc"
    status=$rc
  fi
done
echo "[done] generation pool complete. logs=$LOG_ROOT"
exit "$status"
