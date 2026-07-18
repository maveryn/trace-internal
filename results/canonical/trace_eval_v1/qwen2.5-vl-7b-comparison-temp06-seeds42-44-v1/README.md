# Canonical Qwen2.5-VL-7B Evaluation Metadata

This directory is a local copy of the sanitized metadata for the canonical
7B comparison used by the Trace paper.

- Repository: `maveryn/trace-eval-runs`
- Repository type: Hugging Face dataset
- Revision: `4178a839b689babe16f8ac36f0de7b1b2c5ef36c`
- Remote run path:
  `runs/qwen2.5-vl-7b-comparison-temp06-seeds42-44-v1/`
- Suite: `trace_eval_v1`
- Models: Qwen2.5-VL-7B base, Trace Qwen2.5-VL-7B, and Vero Qwen2.5-VL-7B
- Decoding seeds: `42`, `43`, and `44`
- Downloaded: 2026-07-18

The downloaded `metadata/manifest.json` records the expected size and SHA-256
of every other file in this directory. In particular:

- `metadata/results/benchmark_scores.json`:
  `578e574d68702af0b83a9c1962bd73c36f8887787cc9ac10a8f7da3d207c10ac`
- `metadata/runs/qwen2.5-vl-7b-comparison-temp06-seeds42-44-v1.json`:
  `7a398d16cfeee3e50b6c82302d293c52a4bcc2bff7bf160aba68c9d85c00dc84`
- `metadata/suites/trace_eval_v1.json`:
  `67be4795badc51903fd498fd8b16cb0347dc3371012be640c574d021dd0a7538`

This copy contains result and provenance metadata only. It does not include
model responses, benchmark prompts, answers, media, or score Parquet slices.
