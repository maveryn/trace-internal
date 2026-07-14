# RLVR Ablation Results

This directory stores concrete RLVR ablation result snapshots with source-log
provenance and machine-readable metrics.

Available snapshots:

- `annotation_sectioned_100step_20260713/` - Qwen2.5-VL-3B 8x H200
  additive-vs-gated annotation reward comparison at global step 100 using the
  sectioned-reasoning annotation system prompt.
- `annotation_sectioned_qwen25vl7b_additive_500step_20260714/` -
  Qwen2.5-VL-7B 8x H200 additive annotation reward run through the saved
  `global_step_500` checkpoint, including resumed-launch provenance, completed
  validation through step 400, terminal train-window metrics, and the private
  step-500 Hugging Face artifact URL.
