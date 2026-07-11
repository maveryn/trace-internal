#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
cd "$REPO_ROOT"

if [[ -f /home/shadeform/venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source /home/shadeform/venv/bin/activate
fi

export PYTHONUNBUFFERED=1
export HF_HOME="${HF_HOME:-/dev/shm/trace_rlvr/cache/huggingface}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-/dev/shm/trace_rlvr/cache/huggingface/datasets}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/dev/shm/trace_rlvr/cache/huggingface/transformers}"
export VLLM_WORKER_MULTIPROC_METHOD="${VLLM_WORKER_MULTIPROC_METHOD:-spawn}"
export VLLM_ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-FLASH_ATTN}"
export VLLM_DISABLE_COMPILE_CACHE="${VLLM_DISABLE_COMPILE_CACHE:-1}"

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG_ROOT="${LOG_ROOT:-logs/benchmark/trace_candidate37_200_${RUN_STAMP}}"
RUN_ROOT="${RUN_ROOT:-runs}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-benchmark}"
QUEUE_ROOT="${QUEUE_ROOT:-benchmark/queues}"
mkdir -p "$LOG_ROOT" "$RUN_ROOT" "$BENCHMARK_ROOT" "$QUEUE_ROOT"

exec > >(tee -a "$LOG_ROOT/run.log") 2>&1

GPU_LIST="${GPU_LIST:-0 1 2 3 4 5 6 7}"
GEN_BATCH_SIZE="${GEN_BATCH_SIZE:-200}"
GEN_GPU_MEMORY_UTILIZATION="${GEN_GPU_MEMORY_UTILIZATION:-0.75}"
GEN_MAX_MODEL_LEN="${GEN_MAX_MODEL_LEN:-20480}"
GEN_MAX_NUM_SEQS="${GEN_MAX_NUM_SEQS:-256}"
GEN_MAX_NUM_BATCHED_TOKENS="${GEN_MAX_NUM_BATCHED_TOKENS:-32768}"
GEN_MAX_TOKENS_OVERRIDE="${GEN_MAX_TOKENS_OVERRIDE:-4096}"
GEN_MAX_IMAGES="${GEN_MAX_IMAGES:-24}"
GEN_MAX_VIDEOS="${GEN_MAX_VIDEOS:-0}"
GEN_PREFETCH_WORKERS="${GEN_PREFETCH_WORKERS:-4}"
GEN_PREFETCH_BATCHES="${GEN_PREFETCH_BATCHES:-2}"

JUDGE_MODEL="${JUDGE_MODEL:-Qwen/Qwen3-32B}"
JUDGE_BATCH_SIZE="${JUDGE_BATCH_SIZE:-128}"
JUDGE_GPU_MEMORY_UTILIZATION="${JUDGE_GPU_MEMORY_UTILIZATION:-0.90}"
JUDGE_MAX_MODEL_LEN="${JUDGE_MAX_MODEL_LEN:-8192}"
JUDGE_MAX_NUM_SEQS="${JUDGE_MAX_NUM_SEQS:-128}"
JUDGE_MAX_NUM_BATCHED_TOKENS="${JUDGE_MAX_NUM_BATCHED_TOKENS:-8192}"
JUDGE_MAX_TOKENS="${JUDGE_MAX_TOKENS:-256}"

CHECKPOINT_RUN_ROOT="${CHECKPOINT_RUN_ROOT:-/dev/shm/trace_rlvr/easyr1_checkpoints/trace_qwen25vl3b_easyr1_answer_nokl_noref_step200_bsz128_rollout8_val500_20260710T073846Z}"
MERGED_ROOT="${MERGED_ROOT:-/dev/shm/trace_rlvr/merged_hf}"
BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-VL-3B-Instruct}"

echo "[trace-candidate37] stamp=$RUN_STAMP"
echo "[trace-candidate37] log_root=$LOG_ROOT"
echo "[trace-candidate37] run_root=$RUN_ROOT benchmark_root=$BENCHMARK_ROOT queue_root=$QUEUE_ROOT"

if [[ "${PREPARE_SUBSET:-1}" == "1" ]]; then
  if [[ ! -f benchmark/subsets/trace_candidate37_200/manifest.json || "${FORCE_SUBSET:-0}" == "1" ]]; then
    echo "[trace-candidate37] preparing fixed 200-row subset"
    python scripts/prepare_external_eval_subset_v1.py --preset trace_candidate37_200 --overwrite
  else
    echo "[trace-candidate37] subset manifest already exists"
  fi
fi

ensure_merged_step() {
  local step="$1"
  local src="${CHECKPOINT_RUN_ROOT}/global_step_${step}/actor"
  local dst="${MERGED_ROOT}/trace-qwen25vl3b-easyr1-answer-nokl-step${step}"
  if [[ -f "${dst}/config.json" ]]; then
    echo "[trace-candidate37] merged checkpoint exists: $dst"
    return 0
  fi
  if [[ ! -d "$src" ]]; then
    echo "[trace-candidate37] missing actor checkpoint: $src" >&2
    return 1
  fi
  echo "[trace-candidate37] merging step ${step}: $src -> $dst"
  mkdir -p "$MERGED_ROOT"
  PYTHONPATH="${REPO_ROOT}/rlvr:${PYTHONPATH:-}" \
    python -m verl.model_merger merge \
      --backend fsdp \
      --local_dir "$src" \
      --target_dir "$dst"
}

ensure_merged_step 400
ensure_merged_step 500
ensure_merged_step 600
ensure_merged_step 700

check_queue() {
  local queue_path="$1"
  python - "$queue_path" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print(f"[queue-check] missing {path}", file=sys.stderr)
    raise SystemExit(1)
state = json.loads(path.read_text())
jobs = state.get("jobs", {})
failed = {k: v for k, v in jobs.items() if v.get("status") == "failed"}
pending = {k: v for k, v in jobs.items() if v.get("status") not in {"done", "failed"}}
done = sum(1 for v in jobs.values() if v.get("status") == "done")
print(f"[queue-check] {path} done={done} failed={len(failed)} pending={len(pending)}")
if failed or pending:
    for name, info in {**failed, **pending}.items():
        print(f"[queue-check] {name}: {info}", file=sys.stderr)
    raise SystemExit(1)
PY
}

run_generation() {
  local slug="$1"
  local model="$2"
  local queue_name="${slug}_trace_candidate37_200_${RUN_STAMP}"
  local -a pids=()
  echo "[generation:start] slug=$slug model=$model queue=$queue_name"
  for gpu in $GPU_LIST; do
    CUDA_VISIBLE_DEVICES="$gpu" python scripts/run_external_benchmark_generation_queue.py \
      --trace-candidate37-200 \
      --model "$model" \
      --model-slug "$slug" \
      --gpu "$gpu" \
      --worker-id "gen-${slug}-${gpu}-${RUN_STAMP}" \
      --queue-name "$queue_name" \
      --queue-root "$QUEUE_ROOT" \
      --run-root "$RUN_ROOT" \
      --batch-size "$GEN_BATCH_SIZE" \
      --gpu-memory-utilization "$GEN_GPU_MEMORY_UTILIZATION" \
      --max-model-len "$GEN_MAX_MODEL_LEN" \
      --max-num-seqs "$GEN_MAX_NUM_SEQS" \
      --max-num-batched-tokens "$GEN_MAX_NUM_BATCHED_TOKENS" \
      --max-tokens-override "$GEN_MAX_TOKENS_OVERRIDE" \
      --max-images "$GEN_MAX_IMAGES" \
      --max-videos "$GEN_MAX_VIDEOS" \
      --prefetch-workers "$GEN_PREFETCH_WORKERS" \
      --prefetch-batches "$GEN_PREFETCH_BATCHES" \
      > "$LOG_ROOT/generation_${slug}_gpu${gpu}.log" 2>&1 &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do
    wait "$pid"
  done
  check_queue "$QUEUE_ROOT/generation_${queue_name}.json"
  echo "[generation:done] slug=$slug"
}

run_scoring() {
  local slug="$1"
  local model="$2"
  local queue_name="${slug}_trace_candidate37_200_${RUN_STAMP}"
  local -a pids=()
  echo "[score:start] slug=$slug model=$model queue=$queue_name"
  for gpu in $GPU_LIST; do
    CUDA_VISIBLE_DEVICES="$gpu" python scripts/run_external_benchmark_score_queue.py \
      --trace-candidate37-200 \
      --model "$model" \
      --model-slug "$slug" \
      --gpu "$gpu" \
      --worker-id "score-${slug}-${gpu}-${RUN_STAMP}" \
      --queue-name "$queue_name" \
      --queue-root "$QUEUE_ROOT" \
      --run-root "$RUN_ROOT" \
      --benchmark-root "$BENCHMARK_ROOT" \
      --judge-model "$JUDGE_MODEL" \
      --judge-batch-size "$JUDGE_BATCH_SIZE" \
      --judge-gpu-memory-utilization "$JUDGE_GPU_MEMORY_UTILIZATION" \
      --judge-max-model-len "$JUDGE_MAX_MODEL_LEN" \
      --judge-max-num-seqs "$JUDGE_MAX_NUM_SEQS" \
      --judge-max-num-batched-tokens "$JUDGE_MAX_NUM_BATCHED_TOKENS" \
      --judge-max-tokens "$JUDGE_MAX_TOKENS" \
      > "$LOG_ROOT/score_${slug}_gpu${gpu}.log" 2>&1 &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do
    wait "$pid"
  done
  check_queue "$QUEUE_ROOT/score_${queue_name}.json"
  echo "[score:done] slug=$slug"
}

MODELS=(
  "qwen25vl3b-base::${BASE_MODEL}"
  "trace-qwen25vl3b-easyr1-answer-nokl-step400::${MERGED_ROOT}/trace-qwen25vl3b-easyr1-answer-nokl-step400"
  "trace-qwen25vl3b-easyr1-answer-nokl-step500::${MERGED_ROOT}/trace-qwen25vl3b-easyr1-answer-nokl-step500"
  "trace-qwen25vl3b-easyr1-answer-nokl-step600::${MERGED_ROOT}/trace-qwen25vl3b-easyr1-answer-nokl-step600"
  "trace-qwen25vl3b-easyr1-answer-nokl-step700::${MERGED_ROOT}/trace-qwen25vl3b-easyr1-answer-nokl-step700"
)

for entry in "${MODELS[@]}"; do
  slug="${entry%%::*}"
  model="${entry#*::}"
  run_generation "$slug" "$model"
  run_scoring "$slug" "$model"
done

python scripts/summarize_trace_candidate37_200_results.py \
  --benchmark-root "$BENCHMARK_ROOT" \
  --run-root "$RUN_ROOT"

echo "[trace-candidate37] complete"
