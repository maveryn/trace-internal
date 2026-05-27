#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR/rlvr:${PYTHONPATH:-}"

CKPT_ROOT="${CKPT_ROOT:-$ROOT_DIR/checkpoints/trace_rlvr}"
OUT_ROOT="${OUT_ROOT:-$ROOT_DIR/checkpoints/trace_rlvr_merged_hf}"
STEP="${STEP:-250}"

mkdir -p "$OUT_ROOT"

export_one() {
  local token="$1"
  local source="$CKPT_ROOT/trace_qwen3vl4b_alpha${token}_answer_250_seed20260504/global_step_${STEP}/actor"
  local target="$OUT_ROOT/trace_qwen3vl4b_alpha${token}_answer_step${STEP}"

  if [[ ! -f "$source/fsdp_config.json" ]]; then
    echo "[missing] $source" >&2
    return 1
  fi

  if compgen -G "$target/model*.safetensors" >/dev/null || [[ -f "$target/pytorch_model.bin" || -f "$target/model.safetensors.index.json" ]]; then
    echo "[skip] existing merged checkpoint: $target"
    return 0
  fi

  echo "[merge] alpha=${token} source=$source target=$target"
  python -m verl.model_merger merge \
    --backend fsdp \
    --local_dir "$source" \
    --target_dir "$target" \
    --trust-remote-code
}

export_one "0"
export_one "0_5"
export_one "1"

echo "[done] merged checkpoints under $OUT_ROOT"
