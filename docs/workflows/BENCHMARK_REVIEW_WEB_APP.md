# Benchmark Review Web App

The benchmark-review web app is a separate browser surface for inspecting model
performance on external benchmark runs. It is intentionally not part of the
`trace/` package because it does not define TRACE generation, verification, or
task-review behavior.

## Source And State

Default source run:

```text
runs/external_benchmarks/qwen25vl7b/20260522T062435Z/
```

Default source model:

```text
Qwen/Qwen2.5-VL-7B-Instruct
```

Recovered local images for old VERO/lmms-eval artifacts can be regenerated with:

```bash
PYTHONPATH=. python scripts/recover_external_benchmark_images.py
```

That script reloads the sampled dataset docs, writes local images into each
benchmark's `images/` folder, and patches the affected sample JSONL rows with an
`image` path plus `image_recovery` metadata. It is safe to dry-run first:

```bash
PYTHONPATH=. python scripts/recover_external_benchmark_images.py --dry-run
```

Dataset-only CharXiv reasoning preview artifacts can be regenerated with:

```bash
PYTHONPATH=. python scripts/prepare_charxiv_reasoning_benchmark_preview.py --overwrite
```

This writes `charxiv_reasoning/` under the default source run with local images,
questions, and ground-truth answers from `princeton-nlp/CharXiv` validation
reasoning rows. It intentionally has no model responses or score fields, so the
app lists its samples under the `Unknown` filter.

Dataset-only Geometry3K preview artifacts can be regenerated with:

```bash
PYTHONPATH=. python scripts/prepare_geometry3k_benchmark_preview.py --overwrite
```

This writes `geometry3k/` under the default source run with local images,
questions, and ground-truth answers from `hiyouga/geometry3k`. It intentionally
has no model responses or score fields, so the app lists its samples under the
`Unknown` filter.

## App Location

Source code:

```text
apps/benchmark_review/
```

Launcher:

```text
scripts/run_benchmark_review_app.py
```

Do not put this app under `trace/`; it is review tooling. Do not put app source
under `review/`; that tree is runtime workspace and generated/manual state.

## Run

The launcher tries the requested port first and then scans the fallback range.
It prints the actual local and proxy URLs.

```bash
PYTHONPATH=. python scripts/run_benchmark_review_app.py \
  --host 127.0.0.1 \
  --port 7861 \
  --port-range 7861:7899
```

When using Jupyter Server Proxy, open the printed URL:

```text
http://<host>:8888/proxy/<port>/
```

For direct remote binding, configure a token:

```bash
export TRACE_BENCHMARK_REVIEW_APP_TOKEN='<shared-review-token>'
PYTHONPATH=. python scripts/run_benchmark_review_app.py --host 0.0.0.0
```

The launcher refuses to bind a non-localhost host without a token.

## Review Surface

The top-level view lists benchmarks instead of TRACE domains. Each benchmark
page supports these filters:

- `All`
- `Correct`
- `Incorrect`
- `Unknown`

Each sample row shows:

- image
- prompt
- model response
- ground-truth answer, extracted answer, score, and correctness status

Correct rows are marked green. Incorrect rows are marked blue. Unknown rows are
neutral.

The app uses benchmark-specific score fields when present, including
`individual_score`, `accuracy`, `exact_match`, `relaxed_overall`, `anls`,
`*_acc.is_correct`, `*_acc.score`, and `screenspot_PointInBox_ACC.correct`.

## Refresh Rules

- If files under the benchmark run root change, use **Reload Index** or call
  `POST /api/reload`.
- If app code, templates, CSS, JavaScript, or indexer logic changes, restart
  the app.
- Image recovery changes benchmark artifacts; reload the index before
  inspecting the affected benchmark in the browser.
