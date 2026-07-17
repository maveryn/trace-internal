# Final24 External Evaluation (Historical)

Final24 is a frozen historical reporting selection. New campaigns use the
independent [`../trace_eval/suite.v1.json`](../trace_eval/suite.v1.json)
contract. This historical selection was additive over the pinned contracts in
[`../final25/suite.v1.json`](../final25/suite.v1.json); it changes no prompts,
generation settings, parsers, judges, or scorers.

[`suite.v1.json`](suite.v1.json) pins the parent manifest hash, exact benchmark
order, exclusions, and six reporting categories:

| Category | Benchmarks |
| --- | --- |
| Charts & Tables | ChartQAPro, CharXivReason, TableVQABench, EvoChart |
| Visual Math | MathVision, MathVista, MathVerse, WeMath |
| Science & General | PhyX Mini MC, MMMU-ProVis, RealWorldQA, MMStar |
| Spatial Reasoning | EmbSpatial, SpatialVizBench CoT, CV-Bench 3D, ERQA |
| Perception & Counting | BLINK, CountBenchQA, CountQA, TreeBench |
| Puzzles & Logic | PuzzleVQA, VisualPuzzles, LogicVista, MME-Reasoning |

Each category contains four benchmarks. Therefore, the overall score is both
the unweighted macro-average of the 24 benchmark scores and the unweighted
average of the six category means. The selection contains 32,805 rows per
model and seed and inherits seven direct, sixteen official VLMEvalKit, and one
MME-specific scoring route.

Completed All31 response, extraction, score, and private archive slices remain
the provenance source. Final24 reporting must filter those existing scores;
it must not regenerate responses or rescore unchanged artifacts.

Runtime results do not belong in this directory. Use a versioned output name
such as `trace_final24_v1_temp06_seed42_44_3models_results.*`; older files whose
names contain `trace_final24` refer to a different historical selection.
