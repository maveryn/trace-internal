# TRACE Eval v1 Temp0.6 Single-Seed Results

Seeds: `42`

Model source: `maveryn/trace-qwen25vl7b-rlvr-ann-additive-0p50-sectioned-step500@f5ecbe0f8564548f201a6e4e2719225f1c8947e2`.
Evaluated runtime revision: `sha256set:3b2e60bffd6a70044ec71ae1b0a985410ddc54416c8d868a990dc5690f22dff7`.

## Category Means

| Category | Benchmarks | TRACE-7B Answer+Annotation Additive 0.50 Step 500 |
|---|---|---|
| Charts & Tables | 4 | 57.12 +/- 0.00 |
| Visual Math | 4 | 45.24 +/- 0.00 |
| Science & General | 4 | 55.21 +/- 0.00 |
| Spatial Reasoning | 4 | 57.81 +/- 0.00 |
| Perception & Counting | 4 | 49.58 +/- 0.00 |
| Puzzles & Logic | 4 | 34.78 +/- 0.00 |

## Benchmark Means

| Category | Benchmark | Rows | TRACE-7B Answer+Annotation Additive 0.50 Step 500 |
|---|---|---|---|
| Charts & Tables | ChartQAPro | 1948 | 45.60 +/- 0.00 |
| Charts & Tables | CharXivReason | 1000 | 44.20 +/- 0.00 |
| Charts & Tables | TableVQABench | 1500 | 76.43 +/- 0.00 |
| Charts & Tables | EvoChart | 1250 | 62.24 +/- 0.00 |
| Visual Math | MathVision | 3040 | 26.25 +/- 0.00 |
| Visual Math | MathVista | 1000 | 72.50 +/- 0.00 |
| Visual Math | MathVerse | 788 | 44.80 +/- 0.00 |
| Visual Math | WeMath | 1740 | 37.43 +/- 0.00 |
| Science & General | PhyX mini MC | 1000 | 49.20 +/- 0.00 |
| Science & General | MMMU-ProVis | 1730 | 36.99 +/- 0.00 |
| Science & General | RealWorldQA | 765 | 68.24 +/- 0.00 |
| Science & General | MMStar | 1500 | 66.40 +/- 0.00 |
| Spatial Reasoning | EmbSpatial | 3640 | 71.04 +/- 0.00 |
| Spatial Reasoning | SpatialVizBench COT | 1180 | 37.80 +/- 0.00 |
| Spatial Reasoning | CV-Bench 3D | 1200 | 81.92 +/- 0.00 |
| Spatial Reasoning | ERQA | 400 | 40.50 +/- 0.00 |
| Perception & Counting | Blink | 1901 | 56.13 +/- 0.00 |
| Perception & Counting | CountBenchQA | 487 | 83.16 +/- 0.00 |
| Perception & Counting | CountQA | 1528 | 21.99 +/- 0.00 |
| Perception & Counting | TreeBench | 405 | 37.04 +/- 0.00 |
| Puzzles & Logic | PuzzleVQA | 2000 | 38.55 +/- 0.00 |
| Puzzles & Logic | VisualPuzzles | 1168 | 25.77 +/- 0.00 |
| Puzzles & Logic | LogicVista | 447 | 47.43 +/- 0.00 |
| Puzzles & Logic | MME-Reasoning | 1188 | 27.36 +/- 0.00 |
| Overall | Average |  | 49.96 +/- 0.00 |

Decoding: temperature 0.6, top-p 1, top-k -1, no penalties, maximum 4096 generated tokens.
Scoring: the pinned benchmark routes selected by canonical trace_eval_v1.
Selection manifest SHA-256: `b84262bcd2243d1d2879b2e02d9b49b17052659ea767df3d7303758f4d63de71`.
