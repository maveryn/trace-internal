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
