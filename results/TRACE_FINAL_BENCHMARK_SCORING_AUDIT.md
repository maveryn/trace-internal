# TRACE Final Benchmark Scoring Audit

> Superseded for the frozen 25-benchmark suite by
> `results/TRACE_FINAL25_SCORING_AUDIT.md`.

Date: 2026-07-15

Scope: final benchmark set from `trace_final20_temp06_3b7b_all_methods_results`, excluding `Game-QA-Lite`, plus `EvoChart` and `MathVerse`.

## Summary

No new generation or judge calls were needed for this audit.

Real issue found and fixed:
- `MathVerse`: cached local Qwen3-32B judge tables had rows with `Judge output: Judgement: 1` but `score=False`. Existing judged outputs were repaired and summaries were regenerated.

Previously known fixes remain active:
- `ScreenSpot`: deterministic point extraction handles final-answer wrappers and positional `pyautogui.click(x, y)` / `moveTo(x, y)`.
- `TableVQABench`: deterministic answer extraction handles final-answer wrappers before official table scoring.
- `VisualPuzzles`: cached Qwen3 extraction outputs are scored with the benchmark-wide A-D option contract.
- `EvoChart`: boxed deterministic extraction was replaced with direct Qwen3-32B judge scoring.

## High-Risk Checks

| Benchmark | Scoring path | Audit result | Status |
|---|---|---:|---|
| ChartQAPro | Qwen3 extraction, then ChartQAPro scorer | 16 cached temp0.6 judged files, 31,168 rows, 0 empty extracted answers | OK |
| EvoChart | Direct Qwen3-32B judge | 1,250 rows per model, 0 invalid judge JSON rows in the direct-judge rerun | OK |
| MathVerse | Local Qwen3-32B binary judge | Repaired cached `Judgement: 1` rows; consistency check now has 0 `judge1_score0` rows | Fixed |
| ScreenSpot | Deterministic grounding scorer | Cached predictions repaired for positional click wrappers | Fixed |
| TableVQABench | Official table scorers after deterministic final-answer extraction | Cached predictions repaired for final-answer wrappers | Fixed |
| VisualPuzzles | Qwen3 extraction, A-D option scoring | Re-scored with global A-D option contract | Fixed |

## Benchmark Status

| Benchmark | Final action |
|---|---|
| Blink | OK: Qwen3 extraction + deterministic option scoring. |
| ChartMuseum | OK: direct/local judge-backed scoring. |
| ChartQAPro | OK: Qwen3 extraction is nonempty across audited cached rows; ChartQAPro scorer consumes cleaned answers. |
| CharXivReason | OK: direct/local judge-backed scoring. |
| CountBenchQA | OK: Qwen3 extraction + numeric scoring. |
| CV-Bench 3D | OK: Qwen3 extraction + deterministic option scoring. |
| LogicVista | OK: direct/local judge-backed scoring. |
| MathVision | OK: direct/local judge-backed scoring. |
| MathVista | OK: direct/local judge-backed scoring. |
| MMMU-ProVis | OK: Qwen3 extraction + deterministic option scoring. |
| Physics | OK: Qwen3-backed binary judgement/scoring. |
| PhyX mini MC | OK: Qwen3 extraction + deterministic option scoring. |
| PuzzleVQA | OK: Qwen3 extraction + deterministic option scoring. |
| ScreenSpot | Fixed: positional click parser repair applied. |
| SpatialVizBench COT | OK: Qwen3 extraction + deterministic option scoring; spot audit did not show a systemic issue. |
| TableVQABench | Fixed: final-answer wrapper repair applied before official scoring. |
| TreeBench | OK: Qwen3 extraction + deterministic option scoring. |
| VisualPuzzles | Fixed: A-D option-contract repair applied. |
| WeMath | OK: local Qwen3 extraction/judge path; spot audit did not show a systemic issue. |
| EvoChart | Fixed/OK: direct Qwen3 judge path is now used; boxed extraction path should not be used for final scores. |
| MathVerse | Fixed: `Judgement: 1` is counted as correct and result summaries were regenerated. |

## Corrected MathVerse Temp0.6 Three-Seed Values

| Model | Mean | Std |
|---|---:|---:|
| Qwen2.5-VL-3B Base | 34.09 | 0.07 |
| Qwen2.5-VL-3B Answer GRPO 500 | 39.59 | 1.37 |
| Qwen2.5-VL-7B Base | 43.82 | 0.29 |
| Qwen2.5-VL-7B Answer GRPO 500 | 46.40 | 1.11 |
