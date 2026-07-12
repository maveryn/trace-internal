# TRACE VLMEvalKit Extensions

This directory mirrors local VLMEvalKit dataset adapters that are applied into
`external/VLMEvalKit`, which is an ignored nested checkout in this repo.

Install/update the local checkout with:

```bash
python scripts/apply_vlmevalkit_trace_extensions.py
```

Included adapters:

- `trace_local_vqa.py`: TRACE-local CountQA and Game-QA-Lite adapters.
- `visiongraph.py`: `VisionGraph_Q3` and `VisionGraph_Q3_CoT`, exposing only
  the third VisionGraph graph-reasoning question as single-turn image VQA.

For VisionGraph images, either install `7z`/`7zz`/`unrar` so the adapter can
extract the official HF `.rar` archives, or set `VISIONGRAPH_ROOT` to a
pre-extracted VisionGraph checkout containing `Dataset/<task>/test/*.png`.
