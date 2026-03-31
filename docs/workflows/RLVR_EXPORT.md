# TRACE RLVR Export

Workflow for exporting a built TRACE dataset into an RLVR-ready JSONL or parquet file.

## 1) Why this exists
TRACE build outputs are optimized for dataset integrity and replay:
- `train_instances.jsonl`
- `traces/`
- `images/`
- `validation_report.json`
- `build_report.json`

The local `rlvr/` stack trains more smoothly from one flat row file, so TRACE provides a dedicated export step instead of overloading the builder.

## 2) Export command
Run:

```bash
PYTHONPATH=. python scripts/export_trace_to_rlvr.py \
  --source <trace_dataset_root> \
  --output <rlvr_output_path_or_dir> \
  --format parquet \
  --parquet-cpu-count 0
```

Examples:

```bash
PYTHONPATH=. python scripts/export_trace_to_rlvr.py \
  --source builds/my_trace_dataset \
  --output rlvr/mydata/my_trace_train.parquet \
  --format parquet \
  --parquet-cpu-count 0
```

```bash
PYTHONPATH=. python scripts/export_trace_to_rlvr.py \
  --source builds/my_trace_dataset \
  --output rlvr/mydata/my_trace_jsonl \
  --format jsonl
```

If `--output` is a directory (or has no suffix), the exporter writes:
- `train.jsonl` for JSONL
- `train.parquet` for parquet

For parquet export:
- `--parquet-cpu-count 0` uses all visible CPUs for Arrow compute + IO threads.
- Set an explicit positive integer when you want a smaller export footprint.
- `--image-storage-mode embedded_bytes` writes self-contained parquet rows suitable for Hugging Face distribution.

## 2b) End-to-end training-dataset helper
For the standard equal-split all-task RLVR train build, use:

```bash
PYTHONPATH=. python scripts/prepare_trace_rlvr_train.py \
  --output-root ./out \
  --dataset-name trace_rlvr_train_128k_all_tasks \
  --num-instances 128000 \
  --workers 0 \
  --parquet-cpu-count 0
```

This helper:
1. enumerates all active registered tasks,
2. requires an exact equal split across tasks,
3. builds the TRACE dataset with `workers=0` meaning all visible CPUs,
4. exports RLVR parquet in one step.

## 3) Exported row contract
Each exported RLVR row currently includes:
1. `uid`
2. `instance_id`
3. `domain`
4. `task_group`
5. `task`
6. `complexity_score`
7. `difficulty_bin`
8. `bucket_id_str`
9. `prompt`
10. `prompt_active`
11. `prompt_answer_only`
12. `prompt_answer_and_evidence`
13. `prompt_mode`
14. `images`
15. `answer_gt`
16. `evidence_gt`
17. `reward_contract`
18. `trace_ref`

Notes:
1. `uid` is set to `instance_id` so repeated generations stay grouped by prompt in RLVR logging/statistics.
2. `prompt_active`, `prompt_answer_only`, and `prompt_answer_and_evidence` are all exported so one parquet can drive multiple ablations by switching `data.prompt_key`.
3. When a row has images, the exporter rewrites each prompt column into the Tesserae multimodal convention by stripping any existing `<image>` markers and prefixing exactly one `<image>` token per exported image. This keeps TRACE prompts compatible with the RLVR/vLLM multimodal path without changing TRACE build artifacts.
4. `images` can be exported either as relative/absolute path dicts (`{"path": ...}`) or, for parquet, as embedded byte dicts (`{"bytes": ..., "format": ...}`) for self-contained Hugging Face upload.
5. `answer_gt`, `evidence_gt`, and `reward_contract` stay in TRACE ABI form so RLVR can dispatch the public reward contract directly.
6. `complexity_score` is copied from TRACE `task_complexity.complexity_score` for logging/debugging only.
7. `difficulty_bin` and `bucket_id_str` are generated automatically from task-local curriculum buckets so RLVR self-paced sampling can work without extra preprocessing.
8. JSONL exports write `answer_gt`, `evidence_gt`, `reward_contract`, and `trace_ref` as structured TRACE objects. Parquet exports serialize those four columns as JSON strings because mixed-task TRACE datasets contain heterogeneous nested value types; the RLVR TRACE loader parses them back automatically.

## 4) Prompt variant policy
Default export uses:
- `--prompt-variant answer_and_evidence`

Use this for RLVR training because the model needs to see the evidence-output contract to earn evidence reward.

Other options:
- `active`
- `answer_only`

If the requested prompt variant is missing, the exporter falls back to the active TRACE `prompt`.

For single-parquet ablations, keep all prompt columns in the same file and switch:

1. `data.prompt_key=prompt_answer_only`
2. or `data.prompt_key=prompt_answer_and_evidence`

## 5) Image path policy
Default export uses:
- `--image-path-mode relative`

This rewrites image paths relative to the exported file location, which keeps the export portable across directories inside the same checkout.

Other options:
- `absolute` — writes absolute image paths
- `dataset_relative` — preserves TRACE dataset-root-relative paths

For Hugging Face parquet distribution, prefer:

1. `--format parquet`
2. `--image-storage-mode embedded_bytes`

That mirrors the prior Prism/Tesserae parquet workflow, where images were embedded directly into parquet rows instead of relying on checkout-local filesystem paths.

## 6) RLVR usage
Pair the export with:
- `rlvr/trace-scripts/config_trace.yaml`

Key RLVR settings for TRACE:
1. `data.prism_mode=trace`
2. `data.format_prompt=null` (TRACE prompts already carry the JSON output contract, and export injects the RLVR `<image>` placeholders when needed)
3. `data.train_files=<exported jsonl/parquet path>`

### Self-paced curriculum

TRACE exports bucket metadata automatically. When you want self-paced EMA curriculum, set:

1. `data.curriculum_mode=self_paced_ema`
2. keep `data.curriculum_backend=prebuilt`
3. leave `data.curriculum_bucket_order_path=null`
4. leave `data.curriculum_mu_init_path=null`

Bucket policy is intentionally low-tuning:

1. split rows **within each task** only
2. target **3 quantile buckets** per task (`q0`, `q1`, `q2`)
3. fall back to `2` or `1` buckets when a task has too few rows or too few distinct complexity scores
4. initialize all bucket competence estimates at `0.5`

This keeps curriculum model-relative without pretending TRACE complexity is comparable across tasks.

## 7) When to rerun export
Rerun the export whenever:
1. the source TRACE dataset changes,
2. prompt-mode choice changes,
3. image-path rewriting requirements change,
4. RLVR row requirements change,
5. curriculum-bucket policy changes.
