# External Benchmark Categories

This document groups the 24 selected external benchmarks by their primary
evaluated capability. The short category names are intended for result tables,
plots, and evaluation summaries. Each benchmark appears in exactly one
category.

The canonical selection is `evaluation/final24/suite.v1.json`. Executable route
definitions live in `scripts/trace_final25_contract.py`; Final24 inherits those
benchmark-specific contracts unchanged from the pinned All31 source campaign.

Final scoring has three routes. Seven benchmarks use benchmark-specific
pinned/direct evaluators, 16 use the pinned VLMEvalKit dataset object's
`evaluate` method on the saved prediction workbook, and MME-Reasoning uses its
dedicated official task scorer. The older generic TRACE Qwen answer-extraction
queue is not a final scoring route.

| Category | Benchmarks | Count |
| --- | --- | ---: |
| Charts & Tables | ChartQAPro, CharXivReason, TableVQABench, EvoChart | 4 |
| Visual Math | MathVision, MathVista, MathVerse, WeMath | 4 |
| Science & General | PhyX mini MC, MMMU-ProVis, RealWorldQA, MMStar | 4 |
| Spatial Reasoning | EmbSpatial, SpatialVizBench COT, CV-Bench 3D, ERQA | 4 |
| Perception & Counting | BLINK, CountBenchQA, CountQA, TreeBench | 4 |
| Puzzles & Logic | PuzzleVQA, VisualPuzzles, LogicVista, MME-Reasoning | 4 |
| **Total** |  | **24** |

## Placement Notes

- **CharXivReason** is categorized by its primary chart-reasoning objective,
  even though its charts come from scientific papers.
- **MMMU-ProVis** is multidisciplinary, but is grouped under Science & General
  Reasoning for this compact reporting taxonomy.
- **MMStar** is a general multimodal benchmark. It remains with the science
  benchmarks as their broad visual-reasoning complement, which is reflected in
  the Science & General label.
- **RealWorldQA** supplies the broad real-world component of Science & General.
- **EmbSpatial**, **SpatialVizBench COT**, **CV-Bench 3D**, and **ERQA** primarily
  evaluate spatial reasoning rather than coordinate or UI grounding.
- **TreeBench** combines subtle-target perception, traceable visual evidence,
  and relational reasoning, so it belongs under Perception & Counting rather
  than the puzzle category.

## Historical Context

- **VStarBench** remains an additive candidate benchmark. Its full 191-row
  `VStarBench` alias uses the normal generation route; scoring applies the same
  deterministic explicit-option normalization as RealWorldQA before the pinned
  VLMEvalKit `dataset.evaluate` exact-matching route.
- **MMVP** remains in the historical All31 diagnostic view but is not a
  Final24 member; Final24 retains CountQA.
- **EvoChart** uses a local deterministic evaluator extension because the
  pinned VLMEvalKit commit has no EvoChart evaluator.
- **LogicVista** follows the pinned evaluator with one narrow exception for
  numeric source labels, which are mapped to their corresponding option
  letters before exact-set comparison.
- **ChartQAPro COT** keeps only its mandated final `The answer is X` sentence
  for official evaluation. **WeMath** uses official `Score (Strict)` percent,
  and **ERQA** uses the pinned EASI `ERQABench.evaluate` implementation to
  avoid VLMEvalKit's broken duplicate registry class.

For an overall score, macro-average the 24 benchmark scores directly. Because
every Final24 category contains four benchmarks, averaging the six category
means produces the same overall value.
