# External Benchmark Evaluation

This workflow runs sampled VERO-supported benchmarks through the shared
Qwen2.5-VL-7B endpoint, then summarizes incorrect answers into TRACE coverage
patterns.

## Scope

- Model: `Qwen/Qwen2.5-VL-7B-Instruct`.
- Endpoint: `http://127.0.0.1:8002/v1`.
- Lock: `logs/vllm/locks/qwen25vl7b_8002.lock`.
- Sample cap: if a benchmark has more than 1000 rows, sample 1000 rows with
  seed `20260522`; otherwise use all rows. Resume passes may intentionally use a
  smaller cap; check each benchmark's `run_summary.json` for the exact selected
  count.
- Image cap: requests are resized to at most 1,000,000 pixels and max side
  1280, then encoded as JPEG payloads so the 4096-token vLLM endpoint is
  usable on high-resolution benchmark images.
- Judge-required benchmarks are generation-only for final scoring in this pass.
  Run Qwen3-32B judging later after all responses are collected.

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
plans/external_benchmark_failure_analysis/qwen25vl7b/<run_id>/
```

For each benchmark, the analyzer writes:

- `normalized_items.jsonl`: per-sample prompt, target, response, score, inferred
  failure intent, and TRACE mapping.
- `failure_patterns.jsonl`: at most 20 grouped patterns.
- `<benchmark>.md`: short human-readable summary.

The root `README.md` contains a cross-benchmark table.
