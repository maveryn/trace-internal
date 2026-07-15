# External Benchmark Evaluation

This workflow runs fixed external benchmark subsets for TRACE checkpoint
comparison and coverage analysis.

## Scope

- For RLVR checkpoint comparison, use the fixed `external_eval_v1` subset:
  `1000` rows per benchmark with seed `42`.
- The subset manifest root is:

  ```text
  benchmark/subsets/external_eval_v1/
  ```

- The private HF mirror is:

  ```text
  maveryn/trace-external-eval-subsets
  ```

- Subsets are manifest-only: source indices and hashes are stored, not benchmark
  images/media.
- Image cap: requests are resized to at most 1,000,000 pixels and max side
  1280, then encoded as JPEG payloads so the 4096-token vLLM endpoint is
  usable on high-resolution benchmark images.
- Judge-required benchmarks are generation first, then scored with the local
  judge path after responses are collected.

## Benchmarks

The sampled VERO runner covers:

`chartqapro`, `infovqa`, `chartmuseum`, `evochart`, `mmmu_pro_vision`,
`mathvista_testmini`, `mathvision`, `blink`, `erqa`, `game_qa_lite`,
`embspatial`, `countqa`, `vstarbench`, `screenspotpro`, `aerialvg`,
`simplevqaen`.

ChartMuseum, MathVista TestMini, MathVision, and SimpleVQAEn are marked
judge-deferred for final scoring because the corresponding VERO judge-style
paths use LLM judging or LLM-based answer extraction. SimpleVQAEn uses a
smaller generation cap on the local 4096-token endpoint. MMMU-ProVis,
MathVista TestMini, and MathVision use the local VERO qwen3 prompt aliases
because qwen25 aliases are not present in the checkout; their generation caps
are reduced to fit the endpoint. The provisional MathVista/MathVision scores
from qwen-style deterministic extraction are useful for smoke checks, but not
the final VERO-style judge scores.

ScreenSpotPro currently uses the local FiftyOne export converted under
`runs/external_benchmarks/local_datasets/screenspotpro`; set
`SCREENSPOTPRO_ROOT` to that directory when rerunning it. The local VERO
checkout's ScreenSpotPro YAML is configured to bootstrap from a dummy JSON split
and let the task utils read `SCREENSPOTPRO_ROOT`. AerialVG is gated on Hugging
Face, so the token in use must be authorized for `IPEC-COMMUNITY/AerialVG`
before the runner can download annotations/images.

## TRACE RLVR Subset v1

The current checkpoint-comparison subset is:

| benchmark | selected rows |
| --- | ---: |
| `chartqapro` | 1000 |
| `charxivreason` | 1000 |
| `mathvista` | 1000 |
| `mmmu_pro_vision` | 1000 |
| `countqa` | 1000 |
| `game_qa_lite` | 1000 |
| `blink` | 1000 |
| `screenspotpro` pooled aggregate | 1000 |

`screenspotpro` is selected proportionally across its six VLMEval subsets and
also writes per-subset manifests so the existing queue jobs can run unchanged.

Create or refresh the local manifests:

```bash
PYTHONPATH=. python scripts/prepare_external_eval_subset_v1.py --overwrite
```

Upload the manifest-only subset to the private HF repo:

```bash
PYTHONPATH=. python scripts/upload_external_eval_subset_v1_to_hf.py
```

Dry-run either command before a real update when changing the subset policy.

## Run

Check benchmark aliases:

```bash
python scripts/run_vero_sampled_benchmark.py --list-benchmarks
```

Build deterministic manifests without model calls:

```bash
python scripts/run_vero_sampled_benchmark.py --manifest-only
```

Run selected benchmarks:

```bash
python scripts/run_vero_sampled_benchmark.py --benchmarks chartqapro,countqa
```

Run the full sampled pass:

```bash
python scripts/run_vero_sampled_benchmark.py --benchmarks all
```

For current RLVR checkpoint comparison with the queue runner, use the fixed
subset root and the v1 benchmark selectors:

```bash
PYTHONPATH=. python scripts/run_external_benchmark_generation_queue.py \
  --model <hf-or-local-model-path> \
  --model-slug <model-slug> \
  --run-set full \
  --only chartqapro charxivreason mathvista mmmu_pro_vision countqa game_qa_lite blink screenspotpro \
  --subset-root benchmark/subsets/external_eval_v1 \
  --queue-name <model-slug>_external_eval_v1
```

Then score the same generated outputs:

```bash
PYTHONPATH=. python scripts/run_external_benchmark_score_queue.py \
  --model <hf-or-local-model-path> \
  --model-slug <model-slug> \
  --run-set full \
  --only chartqapro charxivreason mathvista mmmu_pro_vision countqa game_qa_lite blink screenspotpro \
  --queue-name <model-slug>_external_eval_v1
```

Run final scoring for judge-deferred benchmarks after responses are cached:

```bash
python scripts/score_vero_deferred_from_samples.py \
  --benchmarks chartmuseum mathvista_testmini mathvision simplevqaen \
  --max-samples 500
```

This scores directly from the saved generation sample files and avoids
lmms-eval cache-alignment/task-alias issues during judge-only reruns. The scorer
uses the local `Qwen/Qwen3-32B` text judge through VERO's judge helpers, so the
GPU must be free for the judge model before launching it. Override `RUN_ID` or
`MAX_SAMPLES` in the environment when needed.

## Local VLMEvalKit MIRAGE support

The local checkout under `external/VLMEvalKit` supports the public dataset name
`MIRAGE` for the DongSky/MIRAGE multimodal reasoning-chain hallucination
benchmark. On first construction it downloads the released `mirage.tsv` and
`mirage_images.zip` from Hugging Face, verifies both checksums, and extracts the
images under `${LMUData:-~/LMUData}/images/MIRAGE/`.
The durable adapter source is `rlvr/vlmevalkit_extensions/mirage.py`; reapply
all local adapters after replacing the nested checkout with
`python scripts/apply_vlmevalkit_trace_extensions.py`.

Run it through the normal VLMEvalKit entry point:

```bash
cd external/VLMEvalKit
OPENAI_API_KEY=EMPTY \
LOCAL_LLM=qwen3-32b-judge \
OPENAI_API_BASE=http://127.0.0.1:<judge-port>/v1/chat/completions \
python run.py \
  --data MIRAGE \
  --model <vlmevalkit-model-name> \
  --judge qwen3-32b-judge \
  --work-dir ../../results/benchmark-runs/<run-tag>/runs
```

The judge endpoint must serve `Qwen/Qwen3-32B` under the API model name
`qwen3-32b-judge`, matching `results/TRACE_FINAL20_EVALUATION_SETUP.md` and the
defaults in `scripts/run_external_benchmark_score_queue.py`. When starting a
Qwen3 judge pool, use the `qwen3` reasoning parser and
`rlvr/examples/prompts/chat_template_no_think.jinja`, as in the video wrapper,
so capped judge responses contain the extracted answer rather than unfinished
thinking text.

The adapter defaults to this local Qwen3-32B judge. It uses the released
`prompt` column and treats each released JPG as the single composite visual
input, removing `<imageN>` placeholders from the text. Evaluation retains the
original `prediction`, `parsed_answer`,
raw `judge_output`, `judge_log`, `judge_model`, `judge_api_model`, and `hit` for
every row, plus the resumable extraction pickle, and emits overall plus seven
category scores.
The command above keeps the prediction workbook, extraction cache, judged
workbook, and score CSV below `results/benchmark-runs/<run-tag>/runs`, following
the durable results root used by previous runs. Multiple-choice answers are
matched by option letter, free-form answers use exact extracted-answer
matching, and `approx` answers accept the benchmark's 5% numeric tolerance. Use
`--judge exact_matching` for a judge-free pass; rows without an explicit final
answer then score as incorrect instead of invoking an answer-extraction model.

## Video4 pooled-endpoint runs

Use `scripts/run_trace_video4_temp06_seed42_single_model.sh` for the four
frame-based VLMEvalKit video aliases. The wrapper keeps media and the active
run under tmpfs, but response durability does not depend on tmpfs:

- The canonical live root remains `${RUN_ROOT}` and keeps the existing
  `api_row_results/<rank>.<index>.<hash>.json` layout.
- Every finalized row JSON is atomically and byte-identically mirrored under
  `${PERSIST_RUN_ROOT}`. The default persistent root is
  `results/benchmark-runs/<run-tag>/runs/`.
- A normal resume restores missing live row files from the persistent mirror
  before selecting pending rows. Successful row keys are reused; error rows
  are retried and replaced in both locations if they succeed.
- `NO_RESUME=1` clears row results for the selected model from both roots.
- Final prediction tables and suite summaries are synced to the persistent
  root on wrapper exit, including failure exits. Score/judge artifacts are
  likewise restored from and synced to `${PERSIST_SCORE_ROOT}`, which defaults
  to `results/benchmark-runs/<run-tag>/score/`. Model response fields and the
  benchmark/model directory hierarchy are unchanged.
- Prediction workbooks use the public VLMEvalKit dataset alias in their file
  name, including frame-count suffixes such as `_8frame`; this is the filename
  contract consumed by the official evaluator.
- Score queues and Markdown/XLSX summaries are model-scoped, so two model
  passes sharing a run tag cannot suppress or overwrite one another. A scoring
  error stops the wrapper instead of being reported as a successful suite.
- Official video scoring defaults to one queue worker per benchmark (up to the
  endpoint count). Each worker points stock VLMEvalKit judge calls at a
  different endpoint; set `SCORE_WORKERS=1` for serial troubleshooting.
- The Qwen3 judge pool defaults to the repo's non-thinking chat template plus
  vLLM's `qwen3` reasoning parser. The template prevents a capped response from
  ending inside `<think>`, while the parser keeps any reasoning markup out of
  the concise answer expected by VLMEvalKit's integer/label parsers. Set
  `JUDGE_CHAT_TEMPLATE=` and `JUDGE_REASONING_PARSER=` when serving a
  non-reasoning judge model.
- VideoMMMU's primary score is taken from its final `acc` row. The upstream
  result table also contains raw total/hit rows, which must not be averaged
  into the percentage.
- QBench-Video's primary score is the row-count-weighted mean of its reported
  subtask accuracies, including the already standardized open-ended score.
  Video-TT's primary score comes from its nested `overall.score` field.
- Resumes append to the model generation/score logs. Each vLLM restart writes
  under `logs/benchmark/<run-tag>/attempts/<attempt-id>/`; parallel score-worker
  logs use the same attempt directory, so retrying a run never truncates or
  mixes the detailed logs from an earlier attempt.

The API queue treats HTTP 4xx responses other than 429 as permanent row
failures and records the response body without repeating the same request.
Transport errors, timeouts, HTTP 429, and HTTP 5xx responses can fail over to a
different endpoint. An endpoint is quarantined after
`GEN_ENDPOINT_FAILURE_THRESHOLD` consecutive health-affecting failures; the
default is `2`. Scoring does not start when any row still has an error.

The video wrapper also bounds CPU oversubscription. Each vLLM API/engine
process defaults to `8` OpenMP/MKL/OpenBLAS/NumExpr threads, and on a regular
multi-GPU host `VLLM_CPU_AFFINITY_GROUPS=auto` partitions logical CPUs evenly
by physical GPU id. Set `VLLM_CPU_AFFINITY_GROUPS=none` to disable affinity, or
provide an explicit semicolon-delimited CPU list matching `GPU_GROUPS`.

To resume an interrupted comparison, reuse all three roots/tags rather than
starting a new run identity:

```bash
RUN_TAG=<existing-run-tag> \
RUN_ROOT=<existing-tmpfs-run-root> \
PERSIST_RUN_ROOT=results/benchmark-runs/<existing-run-tag>/runs \
MODEL_PATH=<model-path> \
MODEL_SLUG=<model-slug> \
GPU_GROUPS="0 1 2 3" \
bash scripts/run_trace_video4_temp06_seed42_single_model.sh
```

Outputs are written under:

```text
runs/external_benchmarks/qwen25vl7b/<run_id>/<benchmark>/
```

Each benchmark folder contains `sample_manifest.jsonl`,
`sample_summary.json`, VERO `*_results.json`, VERO `*_samples_*.jsonl`,
and `run_summary.json`.

## Analyze

After generation, build TRACE coverage summaries:

```bash
python scripts/analyze_vero_benchmark_failures.py \
  --run-root runs/external_benchmarks/qwen25vl7b/<run_id>
```

Outputs are written under:

```text
review/external_benchmark_failure_analysis/qwen25vl7b/<run_id>/
```

For each benchmark, the analyzer writes:

- `normalized_items.jsonl`: per-sample prompt, target, response, score, inferred
  failure intent, and TRACE mapping.
- `failure_patterns.jsonl`: at most 20 grouped patterns.
- `<benchmark>.md`: short human-readable summary.

The root `README.md` contains a cross-benchmark table.

## TRACE Final25 scoring contract

The frozen Final25 suite and category ordering live in
`scripts/benchmark_queue_lib.py` as `TRACE_FINAL25_BENCHMARK_CATEGORIES`.
The machine-readable extraction/scoring matrix is
`scripts/trace_final25_contract.py`. The three scoring routes are disjoint and
must cover all 25 benchmarks:

- `DIRECT_SCORE_KEYS`: official deterministic scorers or benchmark-specific
  Qwen3-32B judge wrappers in `run_external_benchmark_score_queue.py`.
- `LLM_EXTRACT_SCORE_KEYS`: Qwen3-32B answer extraction followed by an
  explicit deterministic scorer in
  `run_llm_extracted_benchmark_score_queue.py`.
- `DEDICATED_SCORE_KEYS`: MME-Reasoning's mixed official evaluator in
  `run_mme_reasoning_eval.py`.

`trace_final25` is a first-class run set for both generation queues. Generate
all 25 prediction tables once through the endpoint pool:

```bash
python scripts/run_external_benchmark_generation_api_queue.py \
  --model <model-path> \
  --model-slug <model-slug> \
  --api-model <served-model-name> \
  --api-base http://127.0.0.1:<port>/v1 \
  --run-set trace_final25 \
  --run-root <run-root> \
  --temperature 0.6 --top-p 1 --top-k -1 \
  --presence-penalty 0 --repetition-penalty 1 \
  --max-tokens 4096 --seed 42
```

Score those tables through the three explicit routes. The direct queue
automatically selects only its 9 contracts when `trace_final25` is used:

```bash
python scripts/run_external_benchmark_score_queue.py \
  --model <model-path> --model-slug <model-slug> \
  --run-set trace_final25 \
  --run-root <run-root> --benchmark-root <score-root> \
  --queue-name <model-slug>_final25_direct --stop-on-error \
  --judge-api-base http://127.0.0.1:<qwen3-judge-port>/v1

python scripts/run_llm_extracted_benchmark_score_queue.py \
  --queue-name <model-slug>_final25_extract \
  --final25 --model-entry <model-slug>=<model-path> \
  --run-root <run-root> --benchmark-root <score-root> \
  --prepare --api-run --finalize \
  --api-base http://127.0.0.1:<qwen3-judge-port>/v1

python scripts/run_mme_reasoning_eval.py score \
  --model <model-path> --model-slug <model-slug> \
  --run-root <run-root> --benchmark-root <score-root> \
  --judge-api-base http://127.0.0.1:<qwen3-judge-port>/v1
```

The direct scorer rejects LLM-extraction and dedicated contracts if they are
explicitly passed with `--only`; it cannot silently score them through a less
appropriate VLMEvalKit fallback. The multi-model direct queue applies the same
restriction.

Do not send a benchmark from `LLM_EXTRACT_SCORE_KEYS` through the generic
VLMEvalKit score queue. That queue rejects the operation so verbose reasoning
cannot be mis-scored by a bare first-letter or exact-string parser. Judge
generation is deterministic (`temperature=0`) even when evaluated model
generation uses the Final25 setting (`temperature=0.6`, `top_p=1`,
`top_k=-1`, no penalties, `max_tokens=4096`, seed 42 unless running the
documented multi-seed comparison).

Dataset construction must go through `build_vlmeval_dataset(spec)`. This pins
`ERQA` to the 400-row EASI `ERQABench` class despite VLMEvalKit registering two
classes under the same alias, and it repairs the upstream TreeBench row whose
option B delimiter is embedded in column A. The builder fails if a TreeBench
ground-truth option is still absent after the narrow repair.

The active deterministic repairs are part of the scorer, not post-processing:

- ScreenSpot accepts named and positional `pyautogui.click`/`moveTo` calls,
  `<answer>` and boxed wrappers, and coordinate pairs. Parse failure raises;
  it is never converted to the point `(0, 0)`.
- TableVQABench unwraps `<answer>`, `\\boxed{}`, JSON `answer`, and explicit
  final-answer markers before calling the official FinTabNetQA, VTabFact,
  VWTQ, and VWTQ-Syn scorers. Its reported TRACE score remains the macro mean
  over all official split `average_scores` values.
- PhyX parses the explicit inline `OPTION: A: ...` block before treating
  line-leading prose such as `A. H. Pfund` as a choice.
- Every Final25 MCQ extraction row must include parsed choice text. The
  extractor never invents a valid option by adding the ground-truth letter;
  fixed A-D datasets must expose all four options, and every ground truth must
  map to a parsed choice before any judge request is sent.
- MathVerse accepts explicit `Judgement: 0/1` decisions and validates every
  extraction and binary judge result.

All direct semantic judges and MME-Reasoning judge stages fail the scoring job
when output is empty or does not satisfy the expected decision contract.
MME-Reasoning choice extractions are normalized from either `A` or bracketed
multi-select forms such as `[A, C]` to the official scorer's `A,C` contract.
Judge-format and infrastructure failures must never be counted as incorrect
model answers. Every final run must preserve the row-level prediction table,
raw judge output, parsed answer/decision, and per-row score.

Validate the contracts before a final run:

```bash
python -m unittest \
  tests.test_external_benchmark_generation_api_queue \
  tests.test_external_benchmark_score_queue \
  tests.test_trace_final25_scoring_contract -v
python scripts/audit_trace_final25_scoring_artifacts.py \
  --output results/trace_final25_historical_llm_artifact_audit.json
```

The artifact audit is diagnostic for old runs. Historical queues may report
issues that the current code now rejects; a clean Final25 run must have zero
malformed option extractions, missing binary decisions, and ground truths
excluded from valid options or parsed choice text, with no required choice text
missing.
