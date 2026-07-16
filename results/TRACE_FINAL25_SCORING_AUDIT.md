# TRACE Final25 Scoring Audit

Date: 2026-07-16

## Conclusion

Final scoring stays with the pinned VLMEvalKit implementation wherever it is
available. The frozen Final25 suite has 10 benchmark-specific pinned/direct
routes, 14 routes that call the pinned dataset object's
`evaluate(prediction_xlsx, ...)` method, and one dedicated MME-Reasoning
route. The provisional all26 view adds MMVP to `dataset.evaluate`, producing
10 direct, 15 pinned `dataset.evaluate`, and one dedicated contract.

The retired generic TRACE Qwen answer-extraction queue is not a final scoring
route. Historical per-row model responses and prediction workbooks remain
reusable; historical generic extraction and judge artifacts do not determine
new scores.

The pinned VLMEvalKit revision is
`a8b12bf1c3737a33fc1de967c202f9c592b22e86`.

## Route Matrix

### Pinned `dataset.evaluate`

These saved prediction workbooks are passed directly to the corresponding
pinned dataset object's `evaluate` method. TRACE owns only job scheduling,
workbook staging, provenance, and canonical result serialization.

| Category | Benchmarks |
|---|---|
| Charts & Tables | ChartQAPro |
| Visual Math | WeMath |
| Science & General Reasoning | PhyX mini MC, MMMU-ProVis, MMStar |
| Spatial & Grounding | SpatialVizBench COT, CV-Bench 3D, ERQA |
| Perception & Counting | BLINK, CountBenchQA, CountQA, TreeBench, MMVP (provisional) |
| Puzzles & Logic | PuzzleVQA, VisualPuzzles |

This route does not substitute TRACE prompts, parsers, extraction schemas,
judge prompts, judge-output parsing, scoring, or aggregation for the pinned
benchmark implementation.

ChartQAPro COT keeps only its mandated final `The answer is X` sentence before
official evaluation. WeMath selects the official `Score (Strict)` percent
field. ERQA calls the EASI `ERQABench.evaluate` implementation rather than the
broken duplicate-registry `ERQADataset.evaluate`; its rows and prompts were
verified to match.

### Benchmark-Specific Pinned/Direct

| Benchmark | Contract |
|---|---|
| ChartMuseum | Pinned answer extraction, `COMPARE_ANSWER_PROMPT`, yes-substring decision, and category aggregation. |
| CharXivReason | Pinned benchmark grading prompt, answer extraction, rubric score, and aggregation. |
| TableVQABench | Pinned leading `Answer: ` cleanup and official four-split scorers. |
| EvoChart | Local deterministic extension; the pinned upstream revision has no EvoChart evaluator. |
| MathVision | Pinned prefetch/extraction, normalization, and aggregation. |
| MathVista | Pinned prefetch/extraction, normalization, and aggregation. |
| MathVerse | Pinned extraction and correctness prompts/parsers; malformed judge output retries and then fails. |
| Physics | Pinned boxed-answer extraction, typed answer handling, `is_equiv`, and fractional multi-box aggregation. |
| ScreenSpot | Pinned named x/y parser and point-in-box geometry unchanged. |
| LogicVista | Pinned extraction and exact option-set scoring, with the numeric-label exception below. |

### Dedicated

MME-Reasoning uses `run_mme_reasoning_eval.py` with its official task-specific
choice, open-answer, and structured-puzzle functions. Choice output is
normalized only to the official `A` or `A,C` representation. Extraction and
open-answer retries follow the pinned temperatures `0, 0.5, 1, 1.5, 2`.
Infrastructure or malformed-output failures fail the evaluation job and are
not counted as incorrect model answers.

## Approved Narrow Differences

1. **EvoChart evaluator extension.** The pinned VLMEvalKit revision has no
   EvoChart dataset/evaluator. TRACE supplies a deterministic evaluator and
   records that provenance explicitly. It does not use a semantic judge.
2. **LogicVista numeric labels.** The upstream auxiliary parser accepts only
   alphabetic output, but at least one source item uses numeric option labels.
   For that case only, numeric labels are mapped to their corresponding option
   letters before the unchanged exact-set comparison. Conflicting or
   unresolvable labels remain failures.
3. **Fail-loud infrastructure semantics.** A missing, malformed, truncated, or
   non-boolean judge response retries according to the benchmark contract and
   then fails the scoring job. It is never silently converted to a zero.
4. **Source construction repairs.** ERQA is pinned to the intended EASI
   dataset class, and the known shifted TreeBench option row is repaired during
   dataset construction. These fixes preserve the benchmark prompt and answer
   content rather than changing evaluator semantics.

No expanded answer syntax is enabled for ScreenSpot or TableVQABench. No
generic Qwen extraction is inserted ahead of the 15 official
`dataset.evaluate` contracts.

## Historical Artifacts

The previous artifact audit scanned 39,168 custom Qwen extraction item files.
Those files remain useful for diagnosing the retired queue, but they are not
inputs to final scoring. In particular, old Physics whole-response binary
judgements and old generic MCQ/count extractions are not comparable to the
current pinned routes.

Regeneration is unnecessary when the saved prediction workbook contains the
original response for every current source row and its generation provenance
still matches. Rescoring starts from those saved predictions.

## Reporting Contract

- Preserve the source row identity, original model response, official
  evaluator artifacts, primary metric, and evaluator provenance.
- Report each benchmark's canonical primary metric; do not average arbitrary
  numeric fields returned by an evaluator.
- TableVQABench's TRACE primary metric remains the macro mean of the official
  split `average_scores` values.
- MMVP reports paired `Overall` as primary and per-question `Average` as
  secondary.
- A final run is invalid when generation and scoring row identities differ or
  an evaluator/infrastructure failure remains unresolved.

## Verification

```text
python -m unittest tests.test_trace_final25_scoring_contract -v
python -m pytest tests/test_final25_synthetic_pipeline.py -q
```
