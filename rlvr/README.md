# RLVR (TRACE + Integer/BBox)

This directory contains the RL training stack used for TRACE and related integer/bbox experiments (EasyR1/veRL-based), including training configs, reward functions, evaluation scripts, and checkpoint utilities.

RLVR-specific documentation lives under:
- `docs/README.md`

## Repo Summary

- `examples/config.yaml`: main trainer/data/model config.
- `examples/qwen2_5-7b-vl-*.sh`: launch scripts for integer/bbox training variants.
- `trace-scripts/trace_qwen2_5_3b_*`: active TRACE launchers for `Qwen/Qwen2.5-VL-3B-Instruct`.
- `trace-scripts/trace_qwen3_2b_*`: active TRACE launchers for `Qwen/Qwen3-VL-2B-Instruct`.
- `examples/reward_function/reward_trace.py`: integer/bbox + TRACE custom reward entry point.
- `verl/trainer/data_loader.py`: integer/bbox/TRACE dataset loading and prompt/answer column selection.
- `scripts/model_merger.py`: merge sharded actor checkpoints into Hugging Face format.

## Dataset Modes

Set `data.dataset_mode` to choose dataset-column behavior:

- `integer`: uses `problem_integer` + `answer_integer`
- `bbox`: uses `problem_bbox` + `answer_bbox`
- `trace`: uses TRACE `prompt` + `answer_gt`, preserves `evidence_gt` and `reward_contract`, and resolves exported TRACE image records from either `images[*].path` or embedded `images[*].bytes`
- `none`: generic/non-specialized behavior

### Exporting TRACE builds for RLVR

TRACE build roots are not used directly as RLVR training directories. From the repo root, export them first:

```bash
PYTHONPATH=. python scripts/export_trace_to_rlvr.py \
  --source builds/<trace_dataset> \
  --output rlvr/dataset/train/<trace_dataset>.parquet \
  --format parquet
```

Use `rlvr/trace-scripts/config_trace.yaml` as the starter config for exported TRACE data.

Recommended TRACE settings:

- `data.dataset_mode=trace`
- `data.format_prompt=null`
- `data.train_files=<exported jsonl/parquet path>`
- use a multimodal checkpoint such as `Qwen/Qwen2.5-VL-3B-Instruct` or `Qwen/Qwen2.5-VL-7B-Instruct`

The exporter defaults to TRACE `answer_and_evidence` prompts so evidence reward remains trainable, prefixes one `<image>` marker per exported image so the RLVR/vLLM multimodal path matches the local RLVR multimodal dataset convention, and can optionally embed image bytes directly into parquet rows for Hugging Face-friendly distribution.

TRACE parquet exports now also include:

- `prompt_active`
- `prompt_answer_only`
- `prompt_answer_and_evidence`

That lets one parquet drive multiple ablations by switching `data.prompt_key`.

For the local 128k training parquet built in this repo, the quickest start is:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/trace_qwen2_5_3b_evidence.sh
```

For faster smoke tests, build a smaller local train parquet from the full train
parquet with:

- `scripts/build_trace_train_subset.py`

The Qwen3-VL-2B launchers remain available with the same TRACE dataset and
validation pack:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/trace_qwen3_2b_evidence.sh
```

The active TRACE launchers validate from the 8 per-benchmark parquets under:

- `rlvr/dataset/validation/`

This matches the `symrl` validation flow: one validation dataloader per
benchmark, `val_batch_size=512`, and per-benchmark metrics logged directly from
that loop. `combined.parquet` remains an offline convenience artifact only.

Other active Qwen3-VL-2B variants:

- `trace-scripts/trace_qwen3_2b_answer.sh`
- `trace-scripts/trace_qwen3_2b_answer_curriculum.sh`
- `trace-scripts/trace_qwen3_2b_evidence_curriculum.sh`

### Qwen3.5-0.8B-Base

Initial TRACE support for `Qwen/Qwen3.5-0.8B-Base` is available through:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/archive/trace_qwen3_5_0p8b_base_answer_evidence.sh
```

The launcher defaults to a conservative setup for the first integration pass:

- `prompt_key=prompt_answer_and_evidence`
- `trace_reward_mode=answer_and_evidence`
- `padding_free=false`
- `use_torch_compile=false`
- 1 GPU / smaller batch sizes than the Qwen2.5-VL launchers

If your environment cannot load `model_type=qwen3_5`, install the overlay in:

- `requirements-qwen3_5_overlay.txt`

then install a nightly `vllm` wheel:

```bash
pip install --no-deps --extra-index-url https://wheels.vllm.ai/nightly vllm
```

The repo also ships [`sitecustomize.py`](/home/jovyan/work/trace/rlvr/sitecustomize.py) so RLVR launchers can work around the current `torch 2.8` + `vllm` nightly import breakage automatically when `rlvr/` is on `PYTHONPATH`.

That import shim is only enough for preflight and dataset/runtime checks. Full `vllm.LLM(...)` engine startup still needs a torch stack that matches the selected nightly wheel. The dedicated Qwen3.5 Docker runtime now pins the current vLLM-nightly-aligned triplet:

- `torch==2.10.0`
- `torchvision==0.25.0`
- `torchaudio==2.10.0`

For a dedicated containerized runtime that leaves the default RLVR image untouched, use:

```bash
cd /home/jovyan/work/trace/rlvr
chmod +x setup_qwen3_5.sh
bash setup_qwen3_5.sh
```

That path builds from:

- `Dockerfile.qwen3_5`
- `requirements-qwen3_5_runtime.txt`

and includes a smoke check inside the container:

```bash
python scripts/check_qwen3_5_runtime.py
```

The dedicated runtime keeps the repo-default RLVR setup stable while moving Qwen3.5 onto a newer Transformers stack. `flash-attn` is left opt-in there because its wheel must match the torch version selected for the vLLM nightly runtime.

TRACE exports also include:

- `complexity_score`
- `difficulty_bin`
- `bucket_id_str`

These are generated automatically from task-local complexity buckets so `data.curriculum_mode=self_paced_ema` can run without a separate bucketing pass.

## Custom Rewards

Implemented in `examples/reward_function/reward_trace.py`.

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
python3 scripts/model_merger.py --local_dir checkpoints/<experiment>/global_step_<step>/actor --hf_upload_path xashru/rlvr-v0
```
