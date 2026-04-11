# RLVR Change Log (2026-02-02)

This document summarizes recent code changes and the rationale.

## Validation-only scoring changes
- Added `rlvr/verl/utils/val_reward.py`.
  - Purpose: apply heuristic answer extraction for validation only (no LLM usage).
  - Heuristics: MCQ letter extraction (supports multiple letters/sequences), numeric extraction/normalization, and existing binary-grid scoring.
  - This mirrors the non-LLM parts of VLMEval to improve validation alignment.

- Updated `rlvr/verl/trainer/ray_trainer.py`.
  - Validation now calls `compute_val_reward(...)` instead of the training reward function.
  - Training reward is unchanged; only validation scoring path is different.
  - Validation can now optionally dump full per-sample predictions/scores from the trainer path via `trainer.val_predictions_dump_dir`.
  - Validation metrics now log extracted-only accuracy under `accuracy_on_extracted` instead of `accuracy_reward`, both per dataset and in the overall validation summary.

- Updated `rlvr/verl/utils/val_reward.py`.
  - Validation now passes benchmark-native `parser_family` and `metadata` into `strict_score_response(...)` when those fields are present in the dataloader row.
  - This keeps benchmark screening aligned with the exact trainer validation path instead of a separate external scorer wrapper.

- Updated `rlvr/verl/workers/rollout/vllm_rollout_spmd.py`.
  - Validation rollout now keeps `finish_reason` / `stop_reason` in `non_tensor_batch`, so cap-rate analysis can come from the same RLVR path used during training.

- Updated `rlvr/verl/utils/dataset.py`.
  - Image normalization now preserves embedded image bytes when parquet rows also carry `path=None`, instead of incorrectly resolving those rows to a filesystem path ending in `None` during prompt-length filtering.

## vLLM compatibility fixes
- Updated `rlvr/verl/workers/rollout/vllm_rollout_spmd.py`.
  - Replaced deprecated `disable_mm_preprocessor_cache` with `mm_processor_cache_gb=0` for vLLM 0.13+ compatibility.

- Updated `rlvr/verl/workers/sharding_manager/fsdp_vllm.py`.
  - Added a fallback to `vllm.distributed.parallel_state.get_tp_group()` when `get_tensor_model_parallel_group()` is not available (vLLM 0.13 API change).

## Why these changes
- Validation scoring needed more robust heuristic extraction (MCQ letters and numbers) similar to VLMEval, without changing training reward behavior.
- vLLM APIs changed between versions; small updates were required to keep rollout/sharding compatible.
