# TRACE Training Scripts

This directory holds TRACE-specific RLVR launchers.

## Qwen2.5-VL 3B on the 128k TRACE parquet

Use `qwen2_5-3b-vl-trace-4gpu.sh` to train against the exported TRACE parquet with these defaults:

- `TRAIN_FILE=mydata/trace_rlvr_train_128k_all_tasks.parquet`
- `MODEL_PATH=Qwen/Qwen2.5-VL-3B-Instruct`
- `NUM_GPUS=4`
- `MAX_STEPS=10`
- `GPU_MEMORY_UTILIZATION=0.8`
- `WANDB_MODE=offline`

The script runs a preflight check before launching training. It verifies:

- the parquet exists
- required TRACE columns are present
- sampled `answer_gt`, `evidence_gt`, and `reward_contract` values are valid JSON
- sampled image paths resolve on disk relative to the parquet location

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
