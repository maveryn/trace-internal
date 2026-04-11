#!/bin/bash

# Shared default external validation pack for RLVR training scripts.
# Assumes REPO_ROOT and SCRIPT_DIR are already defined by the caller.

VALIDATION_ROOT="${REPO_ROOT}/rlvr/dataset/validation"

DEFAULT_VAL_FILES_JSON="$(printf '[\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"]' \
  "${VALIDATION_ROOT}/mathverse_mini.parquet" \
  "${VALIDATION_ROOT}/mathvista_mini.parquet" \
  "${VALIDATION_ROOT}/mmstar.parquet" \
  "${VALIDATION_ROOT}/charxiv_dq.parquet" \
  "${VALIDATION_ROOT}/charxiv_rq.parquet" \
  "${VALIDATION_ROOT}/embspatialbench.parquet" \
  "${VALIDATION_ROOT}/blink.parquet" \
  "${VALIDATION_ROOT}/countqa.parquet")"
