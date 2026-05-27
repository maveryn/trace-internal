#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  scripts/prepare_trace_variant_alpha025_rlvr_train.sh [cpu_count]

Builds the 200k TRACE answer-mode RLVR parquet with variant-aware task sampling
at alpha=0.25.

Default cpu_count is 120 so this can run alongside staged GPU probes. Pass 180
to match the previous full-speed dataset builds.

Output:
  rlvr/dataset/train/trace_rlvr_train_200000_variant_alpha0_25_answer_seed20260504.parquet
EOF
  exit 0
fi

# Keep this below the full-machine 180-worker setting by default so the staged
# GPU probe keeps enough CPU for vLLM preprocessing/scoring. Pass a first arg to
# override, e.g. `scripts/prepare_trace_variant_alpha025_rlvr_train.sh 180`.
CPU_COUNT="${1:-120}"

exec scripts/prepare_trace_variant_aware_rlvr_train.sh 0.25 "${CPU_COUNT}"
