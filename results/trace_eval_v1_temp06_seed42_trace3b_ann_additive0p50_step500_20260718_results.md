# TRACE Eval v1 Temp0.6 Single-Seed Results

Seeds: `42`

Model source: `maveryn/trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500@68ea66ce6ddcb1c683a58d0992d19f6e61963e4d`.
Evaluated runtime revision: `sha256set:7d7e8b6f4d0bc22a08b4e9877808b4716d5b6ebfe2b887a8dd8959658b698867`.

## Category Means

| Category | Benchmarks | TRACE-3B Answer+Annotation Additive 0.50 Step 500 |
|---|---|---|
| Charts & Tables | 4 | 46.59 +/- 0.00 |
| Visual Math | 4 | 36.34 +/- 0.00 |
| Science & General | 4 | 45.13 +/- 0.00 |
| Spatial Reasoning | 4 | 48.23 +/- 0.00 |
| Perception & Counting | 4 | 44.25 +/- 0.00 |
| Puzzles & Logic | 4 | 31.25 +/- 0.00 |

## Benchmark Means

| Category | Benchmark | Rows | TRACE-3B Answer+Annotation Additive 0.50 Step 500 |
|---|---|---|---|
| Charts & Tables | ChartQAPro | 1948 | 33.52 +/- 0.00 |
| Charts & Tables | CharXivReason | 1000 | 32.80 +/- 0.00 |
| Charts & Tables | TableVQABench | 1500 | 70.91 +/- 0.00 |
| Charts & Tables | EvoChart | 1250 | 49.12 +/- 0.00 |
| Visual Math | MathVision | 3040 | 21.58 +/- 0.00 |
| Visual Math | MathVista | 1000 | 64.10 +/- 0.00 |
| Visual Math | MathVerse | 788 | 36.80 +/- 0.00 |
| Visual Math | WeMath | 1740 | 22.86 +/- 0.00 |
| Science & General | PhyX mini MC | 1000 | 33.90 +/- 0.00 |
| Science & General | MMMU-ProVis | 1730 | 28.61 +/- 0.00 |
| Science & General | RealWorldQA | 765 | 63.14 +/- 0.00 |
| Science & General | MMStar | 1500 | 54.87 +/- 0.00 |
| Spatial Reasoning | EmbSpatial | 3640 | 62.50 +/- 0.00 |
| Spatial Reasoning | SpatialVizBench COT | 1180 | 30.42 +/- 0.00 |
| Spatial Reasoning | CV-Bench 3D | 1200 | 63.25 +/- 0.00 |
| Spatial Reasoning | ERQA | 400 | 36.75 +/- 0.00 |
| Perception & Counting | Blink | 1901 | 46.50 +/- 0.00 |
| Perception & Counting | CountBenchQA | 487 | 77.00 +/- 0.00 |
| Perception & Counting | CountQA | 1528 | 16.23 +/- 0.00 |
| Perception & Counting | TreeBench | 405 | 37.28 +/- 0.00 |
| Puzzles & Logic | PuzzleVQA | 2000 | 35.45 +/- 0.00 |
| Puzzles & Logic | VisualPuzzles | 1168 | 29.54 +/- 0.00 |
| Puzzles & Logic | LogicVista | 447 | 37.14 +/- 0.00 |
| Puzzles & Logic | MME-Reasoning | 1188 | 22.90 +/- 0.00 |
| Overall | Average |  | 41.97 +/- 0.00 |

Decoding: temperature 0.6, top-p 1, top-k -1, no penalties, maximum 4096 generated tokens.
Scoring: the pinned benchmark routes selected by canonical trace_eval_v1.
Selection manifest SHA-256: `b84262bcd2243d1d2879b2e02d9b49b17052659ea767df3d7303758f4d63de71`.
