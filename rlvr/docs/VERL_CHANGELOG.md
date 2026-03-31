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

## vLLM compatibility fixes
- Updated `rlvr/verl/workers/rollout/vllm_rollout_spmd.py`.
  - Replaced deprecated `disable_mm_preprocessor_cache` with `mm_processor_cache_gb=0` for vLLM 0.13+ compatibility.

- Updated `rlvr/verl/workers/sharding_manager/fsdp_vllm.py`.
  - Added a fallback to `vllm.distributed.parallel_state.get_tp_group()` when `get_tensor_model_parallel_group()` is not available (vLLM 0.13 API change).

## Why these changes
- Validation scoring needed more robust heuristic extraction (MCQ letters and numbers) similar to VLMEval, without changing training reward behavior.
- vLLM APIs changed between versions; small updates were required to keep rollout/sharding compatible.
