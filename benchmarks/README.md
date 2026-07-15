# External Benchmark Categories

This document groups the 25 selected external benchmarks by their primary
evaluated capability. The short category names are intended for result tables,
plots, and evaluation summaries. Each benchmark appears in exactly one
category.

The executable route definitions live in
`scripts/trace_final25_contract.py`; the extraction/scoring audit is
`results/TRACE_FINAL25_SCORING_AUDIT.md`.

| Category | Benchmarks | Count |
| --- | --- | ---: |
| Charts, Tables & Structured Figures | ChartMuseum, ChartQAPro, CharXivReason, TableVQABench, EvoChart | 5 |
| Visual Mathematics | MathVision, MathVista, MathVerse, WeMath | 4 |
| Science & Academic Reasoning | PhyX mini MC, Physics, MMMU-ProVis, MMStar | 4 |
| Spatial, 3D, Embodied & UI Grounding | ScreenSpot, SpatialVizBench COT, CV-Bench 3D, ERQA | 4 |
| Visual Perception, Counting & Evidence Grounding | BLINK, CountBenchQA, CountQA, TreeBench | 4 |
| Puzzles & Abstract Logic | PuzzleVQA, VisualPuzzles, LogicVista, MME-Reasoning | 4 |
| **Total** |  | **25** |

## Placement Notes

- **CharXivReason** is categorized by its primary chart-reasoning objective,
  even though its charts come from scientific papers.
- **MMMU-ProVis** is multidisciplinary, but is grouped under Science for this
  compact reporting taxonomy.
- **MMStar** is grouped under Science & Academic Reasoning because this suite
  uses it as the broad academic visual-reasoning complement to MMMU-ProVis.
- **ScreenSpot** evaluates UI element localization, so it belongs under
  Spatial & Grounding.
- **TreeBench** combines subtle-target perception, traceable visual evidence,
  and relational reasoning, so it belongs under Perception & Counting rather
  than the puzzle category.

For an overall score, macro-average the 25 benchmark scores directly. Averaging
the six category means equally gives categories equal weight rather than giving
each benchmark equal weight.
