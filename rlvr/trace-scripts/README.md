# TRACE Training Scripts

This directory holds TRACE-specific RLVR launchers.

The shared TRACE training config lives here too:

- `trace-scripts/config_trace.yaml`

## Qwen2.5-VL 3B on the 128k TRACE parquet

Use `qwen2_5-3b-vl-trace-4gpu.sh` to train against the exported TRACE parquet with these defaults:

- `TRAIN_FILE=mydata/trace_train_128k_multivariant_hf.parquet`
- `HF_TRAIN_REPO=xashru/trace-rlvr-train-128k`
- `HF_TRAIN_SPLIT=train`
- `MODEL_PATH=Qwen/Qwen2.5-VL-3B-Instruct`
- `NUM_GPUS=4`
- `MAX_STEPS=10`
- `GPU_MEMORY_UTILIZATION=0.8`
- `WANDB_MODE=online`

The script runs a preflight check before launching training. It verifies:

- the local parquet exists, or the HF fallback repo can be loaded
- required TRACE columns are present
- sampled `answer_gt`, `evidence_gt`, and `reward_contract` values are valid JSON
- sampled images are usable, either from embedded bytes / HF `Image` payloads or from local paths on disk

If `TRAIN_FILE` points to a local parquet path and that file is missing, the launcher automatically falls back to:

- `${HF_TRAIN_REPO}@${HF_TRAIN_SPLIT}`

For a private HF dataset repo, export `HF_TOKEN` or `HUGGINGFACE_TOKEN` before launching.

If you want local-only logging for a run, override with `WANDB_MODE=offline`.

Example:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/qwen2_5-3b-vl-trace-4gpu.sh
```

Preflight only:

```bash
cd /home/jovyan/work/trace/rlvr
TRACE_PREFLIGHT_ONLY=1 bash trace-scripts/qwen2_5-3b-vl-trace-4gpu.sh
```
