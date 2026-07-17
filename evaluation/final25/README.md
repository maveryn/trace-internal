# Final25/Final31 Evaluation (Historical)

This directory is the immutable configuration and provenance surface for older
external benchmark campaigns. New campaigns use
[`../trace_eval/README.md`](../trace_eval/README.md). It intentionally contains no model responses, extracted
answers, judge outputs, scores, workbooks, or aggregate result tables. Runtime
artifacts belong in the configured campaign root and the private evaluation
archive.

This remains the immutable source contract for its historical campaigns; the
commands and policies below document those runs and are not active defaults.

## Suite Definition

[`suite.v1.json`](suite.v1.json) defines three explicit suite views:

- `frozen`: the historical 25-benchmark comparison suite, including CountQA.
- `provisional_mmvp`: the same suite with MMVP replacing CountQA.
- `all31`: the diagnostic All26 union (both CountQA and MMVP) plus
  ScreenSpotPro, ScreenSpot v2, EmbSpatial, RealWorldQA, and VisuLogic.

MMVP remains provisional until the full 300-row benchmark is run once on the
Qwen2.5-VL-7B base model and the trained checkpoint with the same decoding
policy. Promote the replacement only after reviewing VLMEvalKit's paired
`Overall` accuracy and per-question `Average` accuracy. Until then, published
or consolidated results must use the frozen view.

The six reporting categories are:

1. Charts & Tables
2. Visual Math
3. Science & General
4. Spatial & Grounding
5. Perception & Counting
6. Puzzles & Logic

The overall score is the unweighted macro-average of the selected benchmark
scores: 25 scores for either comparison view and 31 scores for `all31`.
Do not average the six category means, because that would give categories equal
weight instead of benchmarks.

In `all31`, RealWorldQA is reported under Science & General;
ScreenSpotPro, ScreenSpot v2, and EmbSpatial under Spatial & Grounding; and
VisuLogic under Puzzles & Logic. ScreenSpotPro's six official subsets and
ScreenSpot v2's three official subsets are each pooled sample-wise into one
logical benchmark score.

## Reproducibility Pin

Use the official
[`open-compass/VLMEvalKit`](https://github.com/open-compass/VLMEvalKit)
repository at commit:

```text
a8b12bf1c3737a33fc1de967c202f9c592b22e86
```

The expected checkout is `external/VLMEvalKit`. Apply the repository's Trace
extensions after checking out that exact upstream revision:

```bash
python scripts/apply_vlmevalkit_trace_extensions.py
```

Record both the upstream commit and the Trace commit in every campaign's
provenance. A moving upstream branch is not a reproducible dependency.

Prepare and hash the exact local prompt media before starting a model server:

```bash
python scripts/prepare_trace_final25_datasets.py --view all31
python scripts/prepare_trace_final25_datasets.py --view all31 --verify-only
```

The Final31 command writes `trace_final31_dataset_manifest.json` and records
separate snapshot hashes for the frozen, provisional, All26, and All31 views.
It verifies 40,527 rows per model/seed, including exact ScreenSpotPro and
ScreenSpot v2 child-subset row counts.
Generation sends these verified files via `file://` and lets the pinned Qwen
processor apply the suite-wide checkpoint-native bounds of 3,136 to
12,845,056 pixels with normal 28-pixel grid alignment.

ScreenSpot, ScreenSpotPro, and ScreenSpot v2 use the shared user-only JSON point
prompt recorded as `trace_screenspot_json_point_v1`; no system message is
injected. Their official subset data and point-in-target geometry remain pinned
to VLMEvalKit. EmbSpatial, RealWorldQA, and VisuLogic retain their pinned
VLMEvalKit prompts and deterministic evaluation routes.

## Environment Setup

Keep evaluation-only packages outside the active RLVR training environment:

```bash
scripts/setup_trace_final25_eval_env.sh
scripts/setup_trace_final25_eval_env.sh --verify-only
```

The setup script installs the pinned packages from `requirements-eval.txt` into
`.tmp/eval_deps`, verifies the official VLMEvalKit commit, reapplies the Trace
extensions, and imports the complete CPU-side evaluation stack. The campaign
launcher prepends this target to `PYTHONPATH`; it does not modify the training
venv.

Stage the public comparison models and Qwen3-32B judge at their immutable HF
commits after training releases the GPUs:

```bash
python scripts/prepare_trace_final25_models.py download-public \
  --model-root /dev/shm/trace_rlvr/final25_models \
  --token-file hf-token.txt
```

Merged TRACE checkpoints are local artifacts, so register each one after the
FSDP-to-HF merge. Registration hashes the config, index, and every weight shard
and writes a provenance marker beside the model:

```bash
python scripts/prepare_trace_final25_models.py register-local \
  --slug trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 \
  --path /dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 \
  --source <training-run-id>:global_step_500
```

The launcher refuses to start generation or scoring when a config, weight
shard, provenance marker, or immutable revision is missing or mismatched. Its
campaign hash includes the per-model revisions, suite revision, judge contract,
and the content hash of the executed Trace/VLMEvalKit evaluation code.

## Extraction Boundary

The current deterministic parser is deliberately conservative and remains a
score-neutral shadow audit:

- Explicit wrappers such as `<answer>...</answer>`, `\boxed{...}`, JSON answer
  objects, and final-answer markers may resolve a candidate.
- An unwrapped raw response remains unresolved in the shadow output.
- Conflicting explicit candidates remain unresolved and retain their candidate
  evidence for audit.
- Production benchmark-specific extraction and official scoring behavior stay
  in the existing runners. The shadow record does not replace or override it.
- Judge-required rows must fail after bounded retries when the judge output is
  malformed; they must not be silently converted to zero.

This boundary hardens provenance without introducing a new scoring framework or
changing official VLMEvalKit metrics.

## Synthetic Validation

`tests/test_final25_synthetic_pipeline.py` exercises one synthetic response for
each frozen benchmark plus MMVP. It covers deterministic wrapper extraction,
exact option/number/short-answer comparisons, strict binary judge-output
parsing, ScreenSpot point containment, MME-Reasoning structured validation, and
MMVP's official paired metric. It does not load images, start a model server, or
call an LLM judge.

Run it with the pinned VLMEvalKit checkout available:

```bash
PYTHONPATH=".tmp/eval_deps:.:scripts:external/VLMEvalKit:external/VLMEvalKit/scripts" \
  pytest -q tests/test_final25_synthetic_pipeline.py
```

## Final31 Campaign

`scripts/run_trace_final31_temp06_3seed_3models.sh` is the resumable launcher
for Qwen2.5-VL-7B Base, TRACE, and VERO on seeds 42, 43, and 44. It serves one
model at a time as eight tensor-parallel-1 replicas, generates the 28 standard
benchmarks with a 4,096-token cap and the three ScreenSpot benchmarks with a
16,384-token cap, then replaces the generation pool with eight Qwen3-32B judge
replicas. CPU finalization is bounded and overlaps subsequent generation.

After dataset and model preparation, run and monitor it with:

```bash
bash scripts/run_trace_final31_temp06_3seed_3models.sh
tail -f logs/benchmark/trace_final31_temp06_seed42_44_3models_v1/status.log
python scripts/status_trace_final31_campaign.py \
  --campaign-root /dev/shm/trace_rlvr/trace_final31_temp06_seed42_44_3models_v1 \
  --dataset-manifest /dev/shm/trace_rlvr/LMUData/trace_final31_dataset_manifest.json
```

The launcher checks immutable dataset/model revisions before serving, validates
every generation summary against the active All31 manifest snapshot before
staging it for scoring, and resumes only exact generation and score contracts.
The final workbook contains per-seed values, benchmark and category mean/std,
and TRACE-minus-Base and TRACE-minus-VERO deltas.

## Isolated Final26/Final31 Rescoring

`scripts/run_trace_final26_official_score_campaign.py` rescoring takes exactly
three repeatable `--campaign MODEL MODEL_SLUG CAMPAIGN_ROOT` descriptors. It
copies the saved prediction workbooks into a new `--score-root`; generation
outputs are never used as evaluator working directories. Run `--preflight`
first. A nonempty score root is rejected unless `--resume` finds an exact
manifest match for every source XLSX hash and the judge contract.

The All26 routes are 15 pinned `dataset.evaluate` jobs (the former 14 generic
extraction jobs plus MMVP), the 10 existing direct-score jobs, and the dedicated
MME-Reasoning scorer. `--suite all31` adds five pinned `dataset.evaluate` jobs;
these additions use deterministic official scoring and never fall back to an
LLM. Official evaluator processes lease at most one of the eight local Qwen3
judge endpoints each. Archive variables reach scoring subprocesses only when
`--emit-archive` is explicit.

## Private Run Archive

The campaign launcher continuously spools one immutable slice after each
model/seed/benchmark generation, extraction, and score stage. A CPU-pinned
background process converts those slices to Zstd Parquet and commits them to
the private `maveryn/trace-final25-eval-runs` dataset repository. Benchmark
images, videos, local media paths, and credentials are rejected or removed.

Each row retains the dataset alias/revision/split, source index and ordinal,
source-row hash, request hash, model/revision, seed, raw response, extraction
evidence, score, and code/config provenance needed for later reanalysis. The
Final31 launcher checks all 837 stage identities:
`3 models x 3 seeds x 31 benchmarks x 3 stages`. After stopping the background
daemon it performs one explicit flush so the last completed slices are not left
queued. Remote archive failure is a warning unless
`REQUIRE_REMOTE_ARCHIVE=1`; local evaluation artifacts remain authoritative.

The uploader reads `hf-token.txt` by path and requires mode `600`; the token is
never placed in an archive record or command-line value. Archive management is
implemented by `scripts/final25_hf_archive.py`, including `flush`, `verify`,
and filtered `reconstruct` commands.

Generation uses bounded preparation, request, and persistence queues. Once a
seed's row responses are durable, CPU finalization and archive emission run in
the background while the endpoint pool continues with the next seed/model.
Judge requests use bounded multi-prompt batches, endpoint cooldown/half-open
recovery, strict route-specific output validation, and content-addressed cache
contracts. Direct scoring, extraction, MME-Reasoning, and archive uploads use
separate CPU pools so GPU serving is not blocked on workbook or upload work.
