# Canonical TRACE paper release results

[`results.json`](results.json) is the single machine-readable result source for
the paper's answer-only RLVR comparison. It contains all three decoding seeds
for exactly these models:

- Qwen2.5-VL-3B base and TRACE;
- Qwen2.5-VL-7B base, TRACE, VERO, Game-RL, Sphinx, and PCGRPO.

The file is generated, not hand-maintained. It binds every input result file
to its immutable Hugging Face repository revision and SHA-256, retains all
576 model/seed/benchmark scores, and recomputes benchmark, category, overall,
and paired-delta summaries. The overall score is the unweighted macro mean of
the 24 benchmark scores for the same model and decoding seed. Reported
standard deviations are sample standard deviations across seeds 42, 43, and
44.

## Immutable inputs

The 3B base/TRACE and 7B base/TRACE/VERO inputs come from:

```text
maveryn/trace-eval-runs@4178a839b689babe16f8ac36f0de7b1b2c5ef36c
```

The Game-RL/Sphinx/PCGRPO inputs come from:

```text
maveryn/trace-eval-runs@4ca25af7a4d7daa644e6f35e070dbed1af078321
```

The exact run ids and result/manifest hashes are recorded under
`source_artifacts` in `results.json`. The builder verifies every metadata file
listed by each source manifest before it reads a score.

## Rebuilding and validation

Place immutable snapshots in the input layout documented by
[`build_trace_eval_release_results.py`](../../../../scripts/build_trace_eval_release_results.py),
then run:

```bash
python scripts/build_trace_eval_release_results.py --inputs-root <snapshot-root>
python scripts/build_trace_eval_release_results.py \
  --inputs-root <snapshot-root> --check
python scripts/validate_rlvr_release_inputs.py
```

The final command validates the result identities and aggregates against the
suite, validates all 24 provenance rows, verifies the reviewed public file
map, and confirms the historical experiment manifest is not an input.

## Historical boundary

`rlvr/experiments/final_answer_only_manifest.json` is deliberately excluded.
It describes the earlier Final25 workflow and earlier training runs. It must
remain internal and must not be used to generate paper tables, public model
cards, or public reproducibility commands.
