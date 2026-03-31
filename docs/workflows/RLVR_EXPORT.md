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
  --format parquet
```

Examples:

```bash
PYTHONPATH=. python scripts/export_trace_to_rlvr.py \
  --source builds/my_trace_dataset \
  --output rlvr/mydata/my_trace_train.parquet \
  --format parquet
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
10. `prompt_mode`
11. `images`
12. `answer_gt`
13. `evidence_gt`
14. `reward_contract`
15. `trace_ref`

Notes:
1. `uid` is set to `instance_id` so repeated generations stay grouped by prompt in RLVR logging/statistics.
2. `images` is exported as a list of lightweight `{"path": ...}` objects so RLVR can normalize relative paths against the exported file location.
3. `answer_gt`, `evidence_gt`, and `reward_contract` stay in TRACE ABI form so RLVR can dispatch the public reward contract directly.
4. `complexity_score` is copied from TRACE `task_complexity.complexity_score` for logging/debugging only.
5. `difficulty_bin` and `bucket_id_str` are generated automatically from task-local curriculum buckets so RLVR self-paced sampling can work without extra preprocessing.

## 4) Prompt variant policy
Default export uses:
- `--prompt-variant answer_and_evidence`

Use this for RLVR training because the model needs to see the evidence-output contract to earn evidence reward.

Other options:
- `active`
- `answer_only`

If the requested prompt variant is missing, the exporter falls back to the active TRACE `prompt`.

## 5) Image path policy
Default export uses:
- `--image-path-mode relative`

This rewrites image paths relative to the exported file location, which keeps the export portable across directories inside the same checkout.

Other options:
- `absolute` — writes absolute image paths
- `dataset_relative` — preserves TRACE dataset-root-relative paths

## 6) RLVR usage
Pair the export with:
- `rlvr/examples/config_trace.yaml`

Key RLVR settings for TRACE:
1. `data.prism_mode=trace`
2. `data.format_prompt=null` (TRACE prompts already carry the JSON output contract)
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
