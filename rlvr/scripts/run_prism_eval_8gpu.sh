#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

OUT_ROOT="${OUT_ROOT:-rlvr/mydata/prism_eval_train_8gpu}"
MODEL="${MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}"
BATCH_SIZE="${BATCH_SIZE:-128}"
DATASET="${DATASET:-xashru/prism@train}"
PROBLEM_KEY="${PROBLEM_KEY:-problem_integer}"
ANSWER_KEY="${ANSWER_KEY:-answer_integer}"
TOTAL_ROWS="${TOTAL_ROWS:-150000}"
SHARDS=8

if (( TOTAL_ROWS % SHARDS != 0 )); then
  echo "[error] TOTAL_ROWS (${TOTAL_ROWS}) must be divisible by ${SHARDS}" >&2
  exit 1
fi

SHARD_SIZE=$((TOTAL_ROWS / SHARDS))
mkdir -p "$OUT_ROOT"
declare -a pids=()

run_shard() {
  local gpu="$1"
  local start="$2"
  local end="$3"
  local out_dir="${OUT_ROOT}/shard_${gpu}"

  mkdir -p "$out_dir"
  echo "[start] gpu=${gpu} split=${DATASET}[${start}:${end}]"

  CUDA_VISIBLE_DEVICES="${gpu}" \
    python rlvr/scripts/eval_prism_integer_vllm.py \
      --dataset "${DATASET}[${start}:${end}]" \
      --model "${MODEL}" \
      --problem-key "${PROBLEM_KEY}" \
      --answer-key "${ANSWER_KEY}" \
      --batch-size "${BATCH_SIZE}" \
      --tensor-parallel-size 1 \
      --out-dir "${out_dir}" \
      > "${out_dir}/run.log" 2>&1 &

  pids+=("$!")
}

for gpu in 0 1 2 3 4 5 6 7; do
  start=$((gpu * SHARD_SIZE))
  end=$(((gpu + 1) * SHARD_SIZE))
  run_shard "$gpu" "$start" "$end"
done

fail=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    fail=1
  fi
done

if (( fail != 0 )); then
  echo "[error] one or more shards failed; inspect ${OUT_ROOT}/shard_*/run.log" >&2
  exit 1
fi

cat "${OUT_ROOT}"/shard_*/predictions.jsonl > "${OUT_ROOT}/predictions_all.jsonl"
echo "[done] merged predictions: ${OUT_ROOT}/predictions_all.jsonl"
