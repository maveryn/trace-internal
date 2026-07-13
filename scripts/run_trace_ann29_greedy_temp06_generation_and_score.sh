#!/usr/bin/env bash
set -euo pipefail

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
BASE_TMP_ROOT="${BASE_TMP_ROOT:-/dev/shm/trace_rlvr}"

GREEDY_TAG="${GREEDY_TAG:-trace_ann29_greedy4096_${RUN_STAMP}}"
TEMP06_TAG="${TEMP06_TAG:-trace_ann29_temp06_4096_${RUN_STAMP}}"

DECODING=greedy4096 \
RUN_TAG="${GREEDY_TAG}" \
RUN_ROOT="${BASE_TMP_ROOT}/${GREEDY_TAG}/runs" \
LATEST_RUN_LINK="${BASE_TMP_ROOT}/trace_ann29_greedy4096_latest" \
  bash /home/shadeform/trace/scripts/run_trace_ann29_generation.sh

DECODING=greedy4096 \
SCORE_TAG="${GREEDY_TAG}_score" \
RUN_ROOT="${BASE_TMP_ROOT}/${GREEDY_TAG}/runs" \
  bash /home/shadeform/trace/scripts/run_trace_ann29_score.sh

DECODING=temp06_4096 \
RUN_TAG="${TEMP06_TAG}" \
RUN_ROOT="${BASE_TMP_ROOT}/${TEMP06_TAG}/runs" \
LATEST_RUN_LINK="${BASE_TMP_ROOT}/trace_ann29_temp06_4096_latest" \
  bash /home/shadeform/trace/scripts/run_trace_ann29_generation.sh

DECODING=temp06_4096 \
SCORE_TAG="${TEMP06_TAG}_score" \
RUN_ROOT="${BASE_TMP_ROOT}/${TEMP06_TAG}/runs" \
  bash /home/shadeform/trace/scripts/run_trace_ann29_score.sh

echo "[ann29-suite:done] greedy_results=/home/shadeform/trace/results/trace_ann29_greedy4096_results.md"
echo "[ann29-suite:done] greedy_excel=/home/shadeform/trace/results/trace_ann29_greedy4096_results.xlsx"
echo "[ann29-suite:done] temp06_results=/home/shadeform/trace/results/trace_ann29_temp06_4096_results.md"
echo "[ann29-suite:done] temp06_excel=/home/shadeform/trace/results/trace_ann29_temp06_4096_results.xlsx"
