# TRACE Evaluation v1

`trace_eval_v1` is the active external model-comparison suite. It contains 24
full-split benchmarks in six balanced reporting categories. The suite identity
does not encode its benchmark count, so future reports and archive locations
remain stable when a new version is introduced.

[`suite.v1.json`](suite.v1.json) is the canonical machine-readable contract. It
records exact benchmark order, official aliases, row counts, reporting
categories, answer contracts, score contracts, route ownership, decoding
settings, and the pinned VLMEvalKit revision.

| Category | Benchmarks |
| --- | --- |
| Charts & Tables | ChartQAPro, CharXivReason, TableVQABench, EvoChart |
| Visual Math | MathVision, MathVista, MathVerse, WeMath |
| Science & General | PhyX mini MC, MMMU-ProVis, RealWorldQA, MMStar |
| Spatial Reasoning | EmbSpatial, SpatialVizBench COT, CV-Bench 3D, ERQA |
| Perception & Counting | BLINK, CountBenchQA, CountQA, TreeBench |
| Puzzles & Logic | PuzzleVQA, VisualPuzzles, LogicVista, MME-Reasoning |

Each category contains four benchmarks. The overall result is the unweighted
macro-average of all 24 primary benchmark scores, which is also the unweighted
average of the six category means. The suite contains 32,805 rows per model and
decoding seed.

## Behavior Boundary

This suite is the complete public selection and reporting contract. Benchmark
behavior is the pinned upstream VLMEvalKit implementation plus the scoped TRACE
adapters installed by `scripts/apply_vlmevalkit_trace_extensions.py`; no
unlisted prompt or evaluator substitution is permitted. Every benchmark's
official alias, answer contract, score contract, and execution route are stated
directly in the manifest.

The route partition is:

- seven benchmark-specific direct scorers;
- sixteen pinned VLMEvalKit `dataset.evaluate` routes;
- the dedicated MME-Reasoning scorer.

Generation and dataset preparation select only these 24 benchmarks through the
`trace_eval_v1` run set and dataset-manifest view.

### Scoped fixes and compatibility

Stay on the pinned upstream prompt, extraction, and scoring behavior unless a
concrete evaluator defect is demonstrated from preserved raw outputs. A scoped
fix must leave generation unchanged, preserve the raw response and judge
cache, record its exact affected identities, and be reproducible without
silently converting an infrastructure or parser failure into an incorrect
answer.

The completed baseline campaign required one such parser repair. PCGRPO seed
44, LogicVista row index 135 had five cached judge attempts, each containing
the otherwise valid label `C.`. `_logicvista_label_tokens` therefore removes
exactly one terminal period before applying the existing option-set
normalization. It continues to reject extra prose, internal punctuation, and
multiple periods. The row was rescored from the unchanged model response and
existing cache with zero new judge requests; its score aggregate carries the
old/new evaluator fingerprints, cache hashes, affected identity, and
`parser_repair` record.

This operational compatibility surface remains internal. Baseline-specific
processor aliases, runtime views, parser incidents, and recovery fixtures
belong in internal provenance and documentation, not in public model-specific
tests or public APIs. A public release may retain a small generic smoke check
for the released TRACE model, but comparison-model compatibility must not
become part of the public contract.

## Running

Set up the pinned VLMEvalKit checkout and CPU-side evaluation dependencies
before preparing data or launching a campaign:

```bash
bash scripts/setup_trace_eval_env.sh
python scripts/prepare_trace_eval_manifest.py
```

The additional packages are pinned in
[`../requirements-eval.txt`](../requirements-eval.txt). In particular,
`pyarrow` is required for durable Parquet slices and `huggingface_hub` is
required for private archive export.

Stage pinned public snapshots and the judge with the existing compatibility
helper, or register a local trained checkpoint. Both commands write the
per-file hash marker required by the launcher's deep model verification:

```bash
python scripts/prepare_trace_final25_models.py download-public \
  --model-root <model-root> \
  --only <public-model-slug> --only qwen3-32b-judge
python scripts/prepare_trace_final25_models.py register-local \
  --slug <slug> --path <local-model-path> \
  --source <model-repository-id>@<model-repository-revision>
```

Use the immutable revision printed by `register-local`, or the pinned commit
recorded by `download-public`, in the model descriptor below. The helper keeps
its historical filename for compatibility; it does not select an evaluation
suite.

Use the neutral launcher with one or more explicit model descriptors:

```bash
bash scripts/run_trace_eval.sh \
  --model <slug> <local-model-path> <immutable-revision> \
    <model-repository-id>@<model-repository-revision> <display-label> \
  --seeds 42 43 44
```

### RL baseline queue

`scripts/run_trace_eval_rl_baselines.sh` is the resumable three-model launcher
used for the Game-RL, Sphinx, and PCGRPO paper baselines. It generates all
three models sequentially, loads the judge once for shared extraction/scoring,
and runs the background publisher against the same campaign root. Inspect the
resolved configuration without acquiring a lock or starting a GPU process:

```bash
TRACE_RL_BASELINES_PRINT_CONFIG=1 \
  bash scripts/run_trace_eval_rl_baselines.sh
```

Paths are derived from the checkout and remain overridable through
`PYTHON_BIN`, `TMP_ROOT`, `MODEL_ROOT`, `LMUData`, `VLMEVALKIT_ROOT`,
`EVAL_DEPS_ROOT`, `TOKEN_FILE`, and the per-model `*_PATH` variables. Model and
judge revisions are pinned in the launcher but may also be overridden for a
new versioned campaign.

The pinned Game-RL checkpoint at upstream revision
`205b5934ce70504cfd6ae26b16f705d0b98b9306` declares
`Qwen2_5_VLImageProcessor`, which is not exported by the pinned evaluation
runtime. The completed campaign used a registered compatibility view that
changed only `preprocessor_config.json#/image_processor_type` to
`Qwen2VLImageProcessor`; every other file linked to the pinned upstream
snapshot. That view had content-set revision
`sha256set:a9c97c8bd921fcaeaf5160c1ed644b34f292ae05302a00980c4ded899a837f8f`.
This baseline-specific compatibility detail is documented here for internal
reproduction; it is not represented by a public test fixture or compatibility
contract.
Set `GAME_PATH` and `GAME_REV` to an equivalently registered view before
launching on a new host.

### Completed baseline results

The campaign
`trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717` completed all
three baselines on the canonical 24-benchmark suite at seeds 42, 43, and 44.
It generated 295,245 responses, completed 216 model/seed/benchmark scoring
identities, and produced 648 locally verified
generation/extraction/score slices. The sanitized private artifact bundle is
pinned at
`maveryn/trace-eval-runs@4ca25af7a4d7daa644e6f35e070dbed1af078321`;
the repository documentation head is
`b61d7702d0c95435869597b1050c8140d5b0d1f2`.

| Category | Game-RL | Sphinx | PCGRPO |
| --- | ---: | ---: | ---: |
| Charts & Tables | 54.81 +/- 0.41 | 54.50 +/- 0.87 | 52.91 +/- 0.99 |
| Visual Math | 44.37 +/- 0.32 | 44.70 +/- 0.26 | 44.99 +/- 0.40 |
| Science & General | 51.52 +/- 1.53 | 52.25 +/- 0.88 | 52.28 +/- 0.92 |
| Spatial Reasoning | 54.31 +/- 0.99 | 56.18 +/- 0.97 | 56.03 +/- 0.55 |
| Perception & Counting | 48.54 +/- 0.24 | 50.03 +/- 0.17 | 48.70 +/- 0.22 |
| Puzzles & Logic | 34.72 +/- 0.74 | 38.39 +/- 0.05 | 37.91 +/- 0.79 |
| Overall | 48.05 +/- 0.45 | 49.34 +/- 0.15 | 48.80 +/- 0.28 |

Values are benchmark-macro means in percent, reported as mean and sample
standard deviation over the three decoding seeds. The full per-benchmark table
and machine-readable score records remain the result source; this table is a
summary.

SpatialVizBench COT used the pinned evaluator's official retry and `INVALID`
fallback unchanged. Fallback row counts were:

| Model | Seed 42 | Seed 43 | Seed 44 | Total |
| --- | ---: | ---: | ---: | ---: |
| Game-RL | 1 | 1 | 1 | 3 |
| Sphinx | 1 | 2 | 0 | 3 |
| PCGRPO | 0 | 1 | 0 | 1 |

No post-hoc answer inference or repair was applied to these rows. The
LogicVista terminal-period repair described above is the only parser repair
needed by this campaign.

The model source must be an immutable 40- or 64-hex repository commit, including
for a locally trained model. Upload and pin that model repository before the
evaluation campaign; mutable branches, training-run labels, and local paths are
rejected. Supply the same repository id and revision to `build-plan`.

The launcher defaults to eight single-GPU endpoints without CPU pinning.
`GPU_GROUPS`, `CPU_AFFINITY_GROUPS`, and `EVAL_CPUSET` are optional host-specific
tuning overrides; do not reuse CPU ids from another machine's topology.

The launcher uses the existing eight-endpoint generation and Qwen3 judge pools,
then invokes the pinned routes with only the recorded scoped adapters. It binds
generation and scoring to a deterministic hash of the complete dirty/untracked
VLMEvalKit worktree and the repo-local extension sources. Raw runtime responses,
prompts, extractions, and scores remain in the configured local campaign spool;
the launcher refuses to send those legacy raw slices to a remote repository.

After local coverage succeeds, seal the exact content-addressed source slices
into a private export plan. `--source-root` may name the archive spool or its
`staged/` directory. Pass every decoding seed and every source model exactly
once. Each model argument records the source archive slug and revision followed
by the neutral model identity and the same immutable repository provenance passed
to the launcher; quote display names containing spaces.

```bash
python scripts/trace_eval_public_export.py build-plan \
  --source-root <local-archive-spool> \
  --source-run-id <local-campaign-run-id> \
  --public-run-id <neutral-paper-run-id> \
  --seed 42 --seed 43 --seed 44 \
  --model <source-slug> <source-revision> \
    <neutral-model-id> <neutral-model-revision> "<display-name>" \
    <model-repository-id> <model-repository-revision> \
  --judge <source-judge-slug> <judge-repository-id> <judge-repository-revision> \
  --output <private-export-plan.json>
```

The command only loads the canonical `trace_eval_v1` suite. It requires exactly
one generation, extraction, and score slice for every requested
model/seed/benchmark identity, rejects extra slices in the named source run,
hashes the selected manifest and Parquet bytes, and binds those hashes to the
explicit model and judge revisions. Revisions must be immutable commits or
content digests. The plan is written atomically with mode `0600`; an existing
different plan is never overwritten.

Build and validate the allowlisted neutral export from that sealed local source
and private plan:

```bash
python scripts/trace_eval_public_export.py export \
  --source-root <sealed-local-source-root> \
  --plan <private-export-plan.json> \
  --output-root <neutral-export-root>
python scripts/trace_eval_public_export.py verify \
  --root <neutral-export-root>
```

Append that sanitized run to the private paper repository with the guarded
run-upload command. The run id is the single value in `run_ids` in the export's
`metadata/manifest.json`. `--public-export-plan` is a global argument and must
appear before the subcommand:

```bash
python scripts/migrate_trace_eval_archive.py \
  --state-root <durable-state> \
  --public-export-plan <private-export-plan.json> \
  upload-paper-run \
  --public-export-root <neutral-export-root> \
  --allow-paper-run-upload \
  --confirm-paper-run "UPLOAD maveryn/trace-eval-runs/<run-id>"
```

The command verifies the complete remote run after its manifest-last upload.
The sanitized destination is `maveryn/trace-eval-runs`. Benchmark prompts,
ground truth, options, source rows, and media paths are excluded from it.

The completed IID-validation run was sealed at data revision
`cf0d14aed86db2661d397ce8b68b36171873478d` and documented at repository head
`b3b37f633b4bcfea294185051e05a930191984b3`. Its 60-file immutable run prefix
contains 24 Parquet parts, 24 matching part manifests, and 12 compact metadata
files; the export manifest SHA-256 is
`73fe4d1d5e8008452720206fbbf404960b0490a397823fd3f4c77ddc94634a48`.

### Internal rich-run publication

Non-paper campaigns that intentionally retain prompts, ground truth, source
rows, judge exchanges, and evaluator artifacts belong in the private
`maveryn/trace-internal-eval-runs` repository. New uploads must still exclude
credentials and host-local paths. Legacy ready spools must therefore be
deterministically re-emitted before the normal archive builder is allowed to
upload them:

```bash
python scripts/reemit_trace_eval_internal_archive.py reemit \
  --source-root <campaign-root>/hf_archive \
  --output-root <durable-path-free-spool> \
  --map-root <machine-runtime-root>=runtime
python scripts/final25_hf_archive.py \
  --spool-root <durable-path-free-spool> build
python scripts/reemit_trace_eval_internal_archive.py verify \
  --root <durable-path-free-spool>
python scripts/final25_hf_archive.py \
  --spool-root <durable-path-free-spool> \
  --repo-id maveryn/trace-internal-eval-runs \
  --token-file <token-file> flush
```

The re-emitter preserves the exact run/model/seed/benchmark/stage identity,
record ids, row order, request hashes, and provenance. Explicit machine roots
become stable `trace-local-ref://<label>/...` references; unmapped absolute
paths and credential-shaped keys or values fail closed. Verification scans both
the JSON source spool and the staged Parquet/manifests that are actually sent.
The token-free `build`/scrub-verify pair must succeed before `flush` is run.
Remote verification must then use `final25_hf_archive.py verify`, which compares
the uploaded objects against those locally safety-checked hashes.

The completed seed-42 answer-and-annotation campaigns use source run ids
`trace_eval_v1_temp06_seed42_trace3b_ann_additive0p50_step500_20260718` and
`trace_eval_v1_temp06_seed42_trace7b_ann_additive0p50_step500_20260718`.
Each has 72 slices (24 benchmarks times generation/extraction/score), and each
remote run prefix contains 72 Parquet parts plus 72 manifests. The immutable
artifact append is
`maveryn/trace-internal-eval-runs@1ed79d7c08208a7e9081dedde86ed030c10b15d1`;
the repository head after documenting both runs is
`fa8ce278bfd1a99bb31b1b16431a36e3fd3942fa`.

### Artifact repository ownership

Choose the destination from the evaluation role, not from whether a model was
trained to emit answers or annotations:

- `maveryn/trace-eval-runs` stores allowlisted, neutral evaluation runs that
  are canonical comparison artifacts. This includes the paper-facing
  `trace_eval_v1` comparisons and the separately identified TRACE IID
  validation comparison. Every run uses the response, extraction, and score
  contracts above and excludes prompts, ground truth, media, and machine-local
  paths.
- `maveryn/trace-internal-eval-runs` stores sealed internal or non-paper run
  archives. The single-seed 24-benchmark campaigns for the 3B and 7B
  answer-and-annotation ablation checkpoints belong here; they do not become
  canonical paper runs merely because they use `trace_eval_v1` benchmarks.

Do not upload a raw campaign tree to either repository or duplicate one run
between them. Preserve raw receipts, logs, judge caches, and machine paths only
in the local forensic workspace; upload the verified contract-shaped export
selected for the run's destination.

### Background publication

For new campaigns, run the publication workflow as a separate low-priority
CPU/network process alongside `run_trace_eval.sh`. The worker watches the local
atomic archive descriptors, incrementally builds their Parquet slices, and does
not initialize an HF client or make a network request while generation or
scoring is incomplete. It repeats the canonical generation and score-receipt
verification before sealing a sanitized export.

Use the same campaign root, run id, decoding seeds, model slug, absolute local
model path, and immutable revision passed to the evaluation launcher. The local
model path string is part of the generation contract and must match exactly.
The remaining model fields define the neutral identity and immutable HF source
recorded in the sanitized export.

```bash
PUBLISH_ROOT=<durable-private-state>/<neutral-paper-run-id>
install -d -m 700 "${PUBLISH_ROOT}"

nohup nice -n 10 python scripts/run_trace_eval_publish_worker.py \
  --campaign-root <campaign-root> \
  --dataset-manifest /dev/shm/trace_rlvr/LMUData/trace_eval_v1_dataset_manifest.json \
  --work-root "${PUBLISH_ROOT}" \
  --source-run-id <campaign-run-tag> \
  --public-run-id <neutral-paper-run-id> \
  --seed 42 --seed 43 --seed 44 \
  --model <source-slug> <exact-absolute-local-model-path> <immutable-revision> \
    <neutral-model-id> <neutral-model-revision> "<display-name>" \
    <model-repository-id> <model-repository-revision> \
  --judge qwen3-32b-judge Qwen/Qwen3-32B \
    9216db5781bf21249d130ec9da846c4624c16137 \
  --token-file <mode-600-hf-token-file> \
  --allow-paper-run-upload \
  --confirm-paper-run "UPLOAD maveryn/trace-eval-runs/<neutral-paper-run-id>" \
  >"${PUBLISH_ROOT}/worker.log" 2>&1 </dev/null &
```

Each `--model` accepts eight fields, and the option may be repeated for a
multi-model campaign. `--archive-spool-root` defaults to
`<campaign-root>/hf_archive`, while `--score-root` defaults to
`<campaign-root>/scoring`. The worker holds a per-campaign lock, serializes local
uploads to the same HF repository, writes `status.json` atomically with mode
`0600`, and exits after full remote readback verification. It never uploads the
raw archive; only the allowlisted tree under `sanitized-export/` is eligible.

Monitor it without touching the evaluation process:

```bash
tail -f "${PUBLISH_ROOT}/worker.log"
jq '{phase, ready_slices, expected_slices, updated_at, error}' \
  "${PUBLISH_ROOT}/status.json"
```

After a host or HF failure, rerun the identical command with the same work
root. The private plan and sanitized export are content-bound and reusable, and
the manifest-last HF append resumes safely. A completed status receipt makes an
identical restart exit without another upload. Publication does not use a GPU,
so another generation campaign can start while export or upload is still
running.

### Post-training handoff

Use `run_trace_eval_after_training.py` when a locally trained checkpoint should
enter evaluation as soon as its training wrapper exits. The supervisor is an
orchestration layer only: it invokes `run_trace_eval.sh` and the background
publisher unchanged, and does not replace benchmark prompts, generation,
answer extraction, or scoring.

The supervisor waits on the exact training PID and script identity, verifies
the retained final checkpoint and merged model, and then establishes two
separate immutable identities:

- a local `sha256set:` revision covering every model file;
- the final 40-character commit of the private canonical HF model repository.

It prefers a server-side move from the training run's temporary repository. If
that upload failed after a valid local merge, it can recover by uploading the
merged folder directly without rerunning training. Existing canonical content
is accepted only when its private snapshot matches the local model; unrelated
content is never overwritten. The local handoff receipt, lock, process
receipts, and status are mode `0600` under a mode-`0700` state directory.

The pinned wrapper for the active Qwen2.5-VL 3B run is:

```bash
bash scripts/run_trace_qwen25vl3b_post_training_eval_job.sh
```

It evaluates the trained TRACE model and the pinned Qwen2.5-VL-3B-Instruct base
on `trace_eval_v1` with seeds `42`, `43`, and `44`. The neutral launcher first
generates every TRACE seed, then every base-model seed, and only then loads one
shared Qwen3-32B judge pool for extraction and scoring across both models.
`GPU_GROUPS="0 1 2 3 4 5 6 7"` gives generation eight independent one-GPU
vLLM endpoints and retains the established 32 requests per endpoint. The judge
phase likewise uses eight endpoints. The publisher runs separately under
`nice -n 10` and waits for all 432 local slices without using a GPU.

Render the complete static contract without reading the token, contacting HF,
waiting for training, or creating state:

```bash
TRACE_3B_HANDOFF_PRINT_CONFIG=1 \
  bash scripts/run_trace_qwen25vl3b_post_training_eval_job.sh
```

Run a read-only host preflight with the training, GPU, and port state included:

```bash
TRACE_3B_HANDOFF_DRY_RUN=1 \
  bash scripts/run_trace_qwen25vl3b_post_training_eval_job.sh
```

For a detached handoff, keep the supervisor log in its durable private state
directory:

```bash
HANDOFF_ROOT=logs/handoff/qwen2.5-vl-3b-comparison-temp06-seeds42-44-v1
install -d -m 700 "${HANDOFF_ROOT}"
nohup bash scripts/run_trace_qwen25vl3b_post_training_eval_job.sh \
  >"${HANDOFF_ROOT}/supervisor.log" 2>&1 </dev/null &
```

Monitor training, handoff, evaluation, and publication independently:

```bash
tail -f "${HANDOFF_ROOT}/supervisor.log"
jq '{phase, updated_at, error}' "${HANDOFF_ROOT}/status.json"
tail -f logs/benchmark/trace_eval_v1_temp06_seed42_43_44_qwen25vl3b_base_trace_step500_20260716/campaign.log
jq '{phase, ready_slices, expected_slices, error}' \
  logs/publish/qwen2.5-vl-3b-comparison-temp06-seeds42-44-v1/status.json
```

Restart the identical wrapper after a process or network failure on the same
host. It validates and reuses the immutable model handoff, attaches to matching
live child PIDs, uses row-level generation resume and scorer resume, and reuses
a completed publisher receipt. Transient HF failures retry with bounded
exponential backoff until the service recovers; permanent authorization or
contract failures stop immediately. It never kills an unknown GPU process;
evaluation waits until all eight target GPUs and both endpoint port ranges are
free. A machine reboot clears the checkpoint and campaign data under
`/dev/shm`; rehydrate those artifacts before restarting after a reboot.

Monitor or verify an existing campaign with:

```bash
python scripts/status_trace_eval.py \
  --campaign-root <campaign-root> \
  --dataset-manifest /dev/shm/trace_rlvr/LMUData/trace_eval_v1_dataset_manifest.json \
  --model-slug <slug> --seeds 42 43 44

python scripts/verify_trace_eval.py \
  --campaign-root <campaign-root> --phase score \
  --model-entry <slug>=<local-model-path>=<immutable-revision> \
  --seeds 42 43 44
```
