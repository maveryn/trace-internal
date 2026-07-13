#!/usr/bin/env bash
set -euo pipefail

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
BASE_TMP_ROOT="${BASE_TMP_ROOT:-/dev/shm/trace_rlvr}"

CANDIDATE_TAG="${CANDIDATE_TAG:-trace_candidate24_full_temp06_4096_${RUN_STAMP}}"
CANDIDATE_RUN_ROOT="${CANDIDATE_RUN_ROOT:-${BASE_TMP_ROOT}/${CANDIDATE_TAG}/runs}"
CANDIDATE_SCORE_TAG="${CANDIDATE_SCORE_TAG:-${CANDIDATE_TAG}_score}"

EXTRA_TAG="${EXTRA_TAG:-trace_extra7_full_temp06_4096_${RUN_STAMP}}"
EXTRA_RUN_ROOT="${EXTRA_RUN_ROOT:-${BASE_TMP_ROOT}/${EXTRA_TAG}/runs}"
EXTRA_SCORE_TAG="${EXTRA_SCORE_TAG:-${EXTRA_TAG}_score}"

echo "[temp06-suite] stamp=${RUN_STAMP}"
echo "[temp06-suite] candidate_run_root=${CANDIDATE_RUN_ROOT}"
echo "[temp06-suite] extra_run_root=${EXTRA_RUN_ROOT}"

RUN_TAG="${CANDIDATE_TAG}" \
RUN_ROOT="${CANDIDATE_RUN_ROOT}" \
  bash /home/shadeform/trace/scripts/run_trace_candidate24_full_temp06_4096_generation_4models.sh

SCORE_TAG="${CANDIDATE_SCORE_TAG}" \
RUN_ROOT="${CANDIDATE_RUN_ROOT}" \
  bash /home/shadeform/trace/scripts/run_trace_candidate24_full_temp06_4096_score_4models.sh

RUN_TAG="${EXTRA_TAG}" \
RUN_ROOT="${EXTRA_RUN_ROOT}" \
LATEST_RUN_LINK="${BASE_TMP_ROOT}/trace_extra7_full_temp06_4096_latest" \
  bash /home/shadeform/trace/scripts/run_trace_extra7_full_temp06_4096_generation_4models.sh

SCORE_TAG="${EXTRA_SCORE_TAG}" \
RUN_ROOT="${EXTRA_RUN_ROOT}" \
  bash /home/shadeform/trace/scripts/run_trace_extra7_full_temp06_4096_score_4models.sh

echo "[temp06-suite:done] candidate_results=/home/shadeform/trace/results/trace_candidate24_full_temp06_4096_results.md"
echo "[temp06-suite:done] candidate_excel=/home/shadeform/trace/results/trace_candidate24_full_temp06_4096_results.xlsx"
echo "[temp06-suite:done] extra_results=/home/shadeform/trace/results/trace_extra7_full_temp06_4096_results.md"
echo "[temp06-suite:done] extra_excel=/home/shadeform/trace/results/trace_extra7_full_temp06_4096_results.xlsx"
