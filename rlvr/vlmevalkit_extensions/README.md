# TRACE VLMEvalKit Extensions

This directory mirrors local VLMEvalKit dataset adapters and helper runner
scripts that are applied into `external/VLMEvalKit`, which is an ignored nested
checkout in this repo.

Install/update the local checkout with:

```bash
python scripts/apply_vlmevalkit_trace_extensions.py
```

Included adapters:

- `trace_local_vqa.py`: TRACE-local CountQA and Game-QA-Lite adapters.
- `evochart.py`: TRACE-local EvoChart-QA adapter for `gsarch/EvoChart-QA`,
  including Vero-style Qwen2.5/Qwen3 prompt aliases and deterministic relaxed
  chart-answer scoring.
- `visiongraph.py`: `VisionGraph_Q3` and `VisionGraph_Q3_CoT`, exposing only
  the third VisionGraph graph-reasoning question as single-turn image VQA.

Included runner scripts:

- `scripts/batched_vlmevalkit_qwen3vl.py`: local generation/scoring helpers
  used by TRACE benchmark queues.
- `scripts/batched_chartmuseum_vllm.py`: ChartMuseum local generation and judge
  prompt utilities.
- `scripts/batched_chartqapro_vllm.py`: ChartQAPro final-answer extraction and
  deterministic local scoring helpers.

For VisionGraph images, either install `7z`/`7zz`/`unrar` so the adapter can
extract the official HF `.rar` archives, or set `VISIONGRAPH_ROOT` to a
pre-extracted VisionGraph checkout containing `Dataset/<task>/test/*.png`.
