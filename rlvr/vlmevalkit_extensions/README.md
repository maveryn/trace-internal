# Trace VLMEvalKit Extensions

This directory mirrors local VLMEvalKit dataset adapters and helper runner
scripts that are applied into `external/VLMEvalKit`, which is an ignored nested
checkout in this repo.

Install/update the local checkout with:

```bash
python scripts/apply_vlmevalkit_trace_extensions.py
```

Included adapters:

- `trace_local_vqa.py`: Trace-local CountQA and Game-QA-Lite adapters.
- `visiongraph.py`: `VisionGraph_Q3` and `VisionGraph_Q3_CoT`, exposing only
  the third VisionGraph graph-reasoning question as single-turn image VQA.

The plain `EvoChart` alias and `CountQA` append the exact generation suffix
`Put the final answer inside \\boxed{}.`; other dataset aliases are unchanged.
EvoChart scoring follows the authors' published metric. A numeric reference
requires exactly one numeric value in the extracted answer: clear rows use
zero-tolerance equality and unclear rows allow 5% relative error. Textual
references use case-insensitive string equality. No judge is used.

The installer also restores pinned VLMEvalKit's official Physics text-only
prompt behavior: rows with an empty `image` cell do not receive a synthetic
blank image. The later multi-ground-truth Physics handling remains unchanged.
The evaluation environment pins upstream's `antlr4-python3-runtime==4.11.1`
so the official symbolic-equivalence path remains available before judge
fallback.

`trace_final25_answer_parsing.py` adds only final-wrapper normalization before
the unchanged official scorers: TableVQABench unwraps exactly one nonempty
`<answer>` block, while PuzzleVQA and VisualPuzzles retain `Answer: X` and also
accept one unambiguous A-D choice from an answer block or final box. Conflicting
explicit choices remain unresolved.

Included runner scripts:

- `scripts/batched_vlmevalkit_qwen3vl.py`: local generation/scoring helpers
  used by Trace benchmark queues.
- `scripts/batched_chartmuseum_vllm.py`: ChartMuseum local generation and judge
  prompt utilities.
- `scripts/batched_chartqapro_vllm.py`: ChartQAPro final-answer extraction and
  deterministic local scoring helpers.

For VisionGraph images, either install `7z`/`7zz`/`unrar` so the adapter can
extract the official HF `.rar` archives, or set `VISIONGRAPH_ROOT` to a
pre-extracted VisionGraph checkout containing `Dataset/<task>/test/*.png`.
