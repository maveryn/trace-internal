# TRACE Final25 Answer Extraction and Scoring Audit

Date: 2026-07-15

## Conclusion

The current Final25 pipeline has an explicit extraction and scoring contract
for every benchmark. The contracts are machine-readable in
`scripts/trace_final25_contract.py`, partitioned into 9 direct-score routes,
15 Qwen3-extraction routes, and 1 dedicated mixed route. The partition is
disjoint and covers exactly 25 benchmarks. `trace_final25` is now accepted by
the generation and direct-scoring CLIs; the direct scorer selects only its 9
valid routes and refuses accidental fallback scoring for the other 16.

The code is ready for a clean final evaluation after the fixes in this audit.
Older cached results are not uniformly final: several old MCQ extraction
queues omitted choice text, PhyX requires extraction/scoring reruns, the
repaired TreeBench source row requires model regeneration, and MME-Reasoning
should be rescored with the strict deterministic judge wrapper.

## Findings Fixed

1. **TreeBench source row 330 had an invalid prompt.** Ground-truth D was
   absent because option B was embedded at the end of column A and later
   choices were shifted left. Dataset construction now performs a narrow,
   logged repair and fails if any ground-truth option remains absent. The
   benchmark also has OCR rows whose choices intentionally appear only in the
   image. Their choice text and actual label set are validated from the
   `multi-choice options` metadata field without adding them to the model
   prompt. This preserves the official A-C row and the source image that
   repeats label C instead of inventing an A-D contract.
2. **PhyX row 22 had an invalid extraction contract.** Prose beginning
   `A. H. Pfund...` was treated as the only option before the later
   `OPTION: A: ... B: ... C: ... D: ...` block. Inline `OPTION:` parsing now
   takes precedence and PhyX is pinned to A-D.
3. **ERQA was not reproducible on a clean cache.** VLMEvalKit registers two
   incompatible classes under alias `ERQA`. TRACE now explicitly constructs
   the 400-row EASI `ERQABench` class and uses its checksum.
4. **ScreenSpot and TableVQABench fixes existed only as cached-result repair
   code.** Their robust parsers are now in the active scoring path.
5. **Judge failures could be counted as model errors.** ChartMuseum,
   CharXivReason, EvoChart, MathVision, MathVista, MathVerse, LogicVista,
   Physics, and MME-Reasoning now validate expected judge output. Malformed or
   unresolved judge output fails the scoring job.
6. **Physics binary parsing had an unsafe fuzzy-positive fallback.** Text that
   merely contained `correct`, `equivalent`, or `matches` could receive 1,
   including negated statements. Only explicit binary decisions are accepted.
7. **MME-Reasoning judge retries were nondeterministic.** Extraction and open
   scoring retries now remain at temperature 0; unresolved rows fail instead
   of silently receiving zero.
8. **MMStar used a one-off extraction invocation.** It is now registered in
   the canonical Final25 Qwen3 extraction route with an A-D option contract.
9. **The frozen suite was not selectable from the actual CLIs.** The registry
   accepted `trace_final25`, but generation and scoring argument parsers did
   not. All generation/direct-scoring entry points now share one run-set
   registry, and the MME release URL/checksum is installed by the common
   dataset builder.
10. **MCQ validation could hide malformed choices.** The extractor used to
    add a missing ground-truth letter to its valid-letter set. It now requires
    actual parsed choice text, requires all A-D choices for fixed contracts,
    and fails before judge inference when the ground truth does not map to a
    real choice.
11. **MME-Reasoning multi-select formatting was inconsistent upstream.** Its
    extraction prompt demonstrates `[A, C]`, while `choice_function` compares
    comma-separated tokens and does not remove brackets. TRACE now validates
    and canonicalizes single/multi-option judge output to `A` or `A,C` before
    invoking the official function.

## Historical Artifact Audit

`scripts/audit_trace_final25_scoring_artifacts.py` recursively scanned 39,168
persisted Qwen3 extraction item files. These are artifact instances, not
unique questions: the same source row can appear for multiple models and
queues. It found no malformed extracted option values and no missing binary
decisions. It also exposed older queues created before choice text was retained
in extraction items:

| Historical issue | Persisted artifact count | Required action |
|---|---:|---|
| BLINK extraction items without choice text | 2,000 artifacts | Re-run extraction/scoring from saved model responses under the current contract. |
| CV-Bench 3D extraction items without choice text | 2,000 artifacts | Re-run extraction/scoring from saved model responses under the current contract. |
| ERQA extraction items without choice text | 1,596 artifacts | Re-run extraction/scoring with the pinned EASI dataset and current inline-choice parser. |
| PhyX ground truth excluded from valid options | 4 artifacts at source index 22 | Re-run Qwen3 extraction and scoring; model generation can be reused. |
| TreeBench missing parsed choice text / ground-truth choice | 272 / 276 artifacts | Re-run extraction for parser-only cases. Regenerate repaired source row 330 before rescoring it. |
| Physics empty extracted-answer field | 19 artifacts | Not automatically invalid because each has a strict semantic judge decision; retain for row audit. |

The machine-readable scan is in
`results/trace_final25_historical_llm_artifact_audit.json`.

## Final25 Contract Matrix

| Category | Benchmark | Output | Extraction | Scoring | Qwen3 role | Status |
|---|---|---|---|---|---|---|
| Charts, Tables & Structured Figures | ChartMuseum | Short/free-form | Preserve response; unwrap answer tag | Semantic correctness against reference | Scoring | Ready; malformed judge output is fatal. |
| Charts, Tables & Structured Figures | ChartQAPro | Short answer after CoT | Qwen3 final-answer extraction | Official/local ChartQAPro normalized scorer | Extraction | Ready. |
| Charts, Tables & Structured Figures | CharXivReason | Free-form chart answer | Benchmark grading prompt | Rubric score from benchmark grading prompt | Both | Ready; explicit score required. |
| Charts, Tables & Structured Figures | TableVQABench | Text/number/boolean | Deterministic answer-tag, boxed, JSON, or final-answer parser | Official four-split scorers | None | Ready; active path fixed. |
| Charts, Tables & Structured Figures | EvoChart | Short/free-form | Extract while judging | Semantic judge with numeric-format tolerance | Both | Ready; binary JSON decision required. |
| Visual Mathematics | MathVision | Math answer | Official prefetch, else Qwen3 extraction | Official MathVision normalization | Extraction | Ready; empty extraction is fatal. |
| Visual Mathematics | MathVista | Math/MCQ answer | Official prefetch, else Qwen3 extraction | Official MathVista normalization | Extraction | Ready; empty extraction is fatal. |
| Visual Mathematics | MathVerse | Math answer | Qwen3 extraction | Official prefetch, else strict binary judge | Both | Ready; `Judgement: 0/1` is parsed correctly. |
| Visual Mathematics | WeMath | MCQ | Qwen3 option extraction | Exact option letter | Extraction | Ready. |
| Science & Academic Reasoning | PhyX mini MC | MCQ | Qwen3 option extraction, fixed A-D | Exact option letter | Extraction | Fixed; rerun old extraction scores. |
| Science & Academic Reasoning | Physics | Free-form physics | Extract while judging | Semantic correctness | Both | Ready; explicit binary decision required. |
| Science & Academic Reasoning | MMMU-ProVis | MCQ | Qwen3 option extraction | Exact option letter | Extraction | Ready. |
| Science & Academic Reasoning | MMStar | MCQ | Qwen3 option extraction, fixed A-D | Exact option letter | Extraction | Ready; canonicalized from one-off path. |
| Spatial, 3D, Embodied & UI Grounding | ScreenSpot | Click point | Deterministic GUI-coordinate parser | Point inside target box | None | Ready; active path fixed and parse failures are explicit. |
| Spatial, 3D, Embodied & UI Grounding | SpatialVizBench COT | MCQ | Qwen3 option extraction | Exact option letter | Extraction | Ready. |
| Spatial, 3D, Embodied & UI Grounding | CV-Bench 3D | MCQ | Qwen3 option extraction | Exact option letter | Extraction | Ready. |
| Spatial, 3D, Embodied & UI Grounding | ERQA | MCQ | Qwen3 option extraction, fixed A-D | Exact option letter | Extraction | Ready; EASI class pinned. |
| Visual Perception, Counting & Evidence Grounding | BLINK | MCQ | Qwen3 option extraction | Exact option letter | Extraction | Ready. |
| Visual Perception, Counting & Evidence Grounding | CountBenchQA | Integer | Qwen3 integer extraction | Normalized exact integer | Extraction | Ready. |
| Visual Perception, Counting & Evidence Grounding | CountQA | Integer | Qwen3 integer extraction | Normalized exact integer | Extraction | Ready. |
| Visual Perception, Counting & Evidence Grounding | TreeBench | MCQ, including image-embedded OCR choices | Qwen3 option extraction using source labels; choice metadata retained for validation | Exact option letter | Extraction | Fixed; regenerate repaired source row. |
| Puzzles & Abstract Logic | PuzzleVQA | Option/value | Qwen3 extraction and value-to-letter mapping | Exact option letter | Extraction | Ready. |
| Puzzles & Abstract Logic | VisualPuzzles | MCQ | Qwen3 extraction, fixed A-D | Exact option letter | Extraction | Ready. |
| Puzzles & Abstract Logic | LogicVista | Option set | Qwen3 option-set extraction | Official normalized set equality | Extraction | Ready; malformed extraction is fatal. |
| Puzzles & Abstract Logic | MME-Reasoning | Mixed open/MCQ/structured | Official task-specific Qwen3 prompts with normalized single/multi-choice output | Official functions; judge only for open answers | Both | Ready; old scores should be rerun under strict wrapper. |

## Reporting Contract

- Preserve original model response, extracted answer, raw judge output,
  normalized prediction/ground truth, and row score.
- Judge temperature is always 0. Evaluated model decoding remains the chosen
  benchmark setting and is reported separately.
- Report each benchmark's canonical primary metric; do not average count fields
  or arbitrary numeric fields from evaluator output.
- TableVQABench remains the macro mean over all values in the official split
  `average_scores` arrays, matching prior TRACE result tables.
- A final run is invalid if any extraction job is missing, any required binary
  decision is malformed, any MCQ ground truth is excluded from valid choices,
  required MCQ choice text is absent, or generation/scoring row counts differ.

## Verification

```text
python -m unittest \
  tests.test_external_benchmark_generation_api_queue \
  tests.test_external_benchmark_score_queue \
  tests.test_trace_final25_scoring_contract -v

30 tests passed.
```
