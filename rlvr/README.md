# RLVR (Prism + TRACE)

This directory contains the RL training stack used for Prism experiments (EasyR1/veRL-based), including training configs, reward functions, evaluation scripts, and checkpoint utilities.

## Repo Summary

- `examples/config.yaml`: main trainer/data/model config.
- `examples/qwen2_5-7b-vl-*.sh`: launch scripts for Prism training variants.
- `examples/reward_function/reward_tesserae.py`: Prism + TRACE custom reward entry point.
- `verl/trainer/data_loader.py`: Prism/TRACE dataset loading and prompt/answer column selection.
- `scripts/model_merger.py`: merge sharded actor checkpoints into Hugging Face format.
- `scripts/eval_prism_integer_vllm.py`: vLLM evaluation over Prism parquet/HF dataset.

## Dataset Modes

Set `data.prism_mode` to choose dataset-column behavior:

- `integer`: uses `problem_integer` + `answer_integer`
- `bbox`: uses `problem_bbox` + `answer_bbox`
- `trace`: uses TRACE `prompt` + `answer_gt`, preserves `evidence_gt` and `reward_contract`, and resolves exported TRACE image records from `images[*].path`
- `none`: non-Prism behavior

### Exporting TRACE builds for RLVR

TRACE build roots are not used directly as RLVR training directories. From the repo root, export them first:

```bash
PYTHONPATH=. python scripts/export_trace_to_rlvr.py \
  --source builds/<trace_dataset> \
  --output rlvr/mydata/<trace_dataset>.parquet \
  --format parquet
```

Use `rlvr/examples/config_trace.yaml` as the starter config for exported TRACE data.

Recommended TRACE settings:

- `data.prism_mode=trace`
- `data.format_prompt=null`
- `data.train_files=<exported jsonl/parquet path>`

The exporter defaults to TRACE `answer_and_evidence` prompts so evidence reward remains trainable.

TRACE exports also include:

- `complexity_score`
- `difficulty_bin`
- `bucket_id_str`

These are generated automatically from task-local complexity buckets so `data.curriculum_mode=self_paced_ema` can run without a separate bucketing pass.

## Custom Rewards

Implemented in `examples/reward_function/reward_tesserae.py`.

### TRACE mode

When dataset rows include TRACE fields:

- `answer_gt`
- `evidence_gt`
- `reward_contract`

the reward path dispatches on the public TRACE reward contract and currently supports:

- `bbox_set_iou_v1`
- `numeric_exact_v1`
- `symbolic_set_exact_v1`
- `sequence_exact_v1`
- `point_set_match_v1`

The current TRACE v1 aggregate is answer-gated:

- `overall = answer_reward * (0.5 + 0.5 * evidence_reward)`

So:

- wrong answer -> `overall = 0`, even if evidence matches
- right answer + wrong evidence -> `overall = 0.5`
- right answer + right evidence -> `overall = 1.0`

For validation, TRACE `hit` / `accuracy` tracks answer correctness, while `overall` remains the training reward.

### Integer mode

- Parses boxed/integer answer.
- Logs `accuracy`, `format`, `overall` (default uses accuracy-only unless `format_weight` is set).

### BBox mode

The model output is parsed as JSON with:

- `count`
- `bboxes: [[xmin, ymin, xmax, ymax], ...]`

Core components:

- `r_cnt`: count signal from predicted box-list length vs GT count.
  - hard: `1` if exact else `0`
  - soft: `exp(-|err|/2)`
- `r_set`: box-set overlap score (`thresholded` or `soft_iou_mass` matching).
- `cons_factor`: consistency factor from declared `count` vs `len(bboxes)`.
  - consistent -> `1`
  - inconsistent -> `bbox_consistency_factor`

Current base formula:

- `base = r_cnt * ((1 - bbox_gate_set_lambda) + bbox_gate_set_lambda * r_set)`
- `overall = max(0, cons_factor * base)`

Key knobs:

- `bbox_r_cnt_mode`: `hard | soft`
- `bbox_set_mode`: `thresholded | soft_iou_mass`
- `bbox_gate_set_lambda`: `[0,1]`, default `0.2`
- `bbox_iou_threshold`: IoU threshold for thresholded matching
- `bbox_consistency_factor`: multiplicative fallback when `count != len(bboxes)`

Notes:

- `r_ans` is logged for analysis, not used directly in `overall`.
- `reward/zero_reward` is sample-level (`overall <= 0`).
- `rlvr_stats/zero_solve_rate` is UID-group-level (max reward per UID), default threshold is now `0.0` (true zero-solve).

## Common Training Commands

Hard count mode:

```bash
BBOX_GATE_SET_LAMBDA=0.2 bash examples/qwen2_5-7b-vl-bbox-rcnt-hard.sh
```

Soft count mode:

```bash
BBOX_GATE_SET_LAMBDA=0.2 bash examples/qwen2_5-7b-vl-bbox-rcnt-soft.sh
```

## Merge Checkpoints to Hugging Face Format

Example:

```bash
python3 scripts/model_merger.py --local_dir checkpoints/<experiment>/global_step_<step>/actor
```

This writes merged weights to:

- `checkpoints/<experiment>/global_step_<step>/actor/huggingface/`

Optional upload:

```bash
python3 scripts/model_merger.py --local_dir checkpoints/<experiment>/global_step_<step>/actor --hf_upload_path xashru/prism-v0
```
