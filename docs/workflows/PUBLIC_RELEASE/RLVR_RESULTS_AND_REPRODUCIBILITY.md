# Agent Brief: RLVR Results And Reproducibility

## Objective

Create one trustworthy release source for Trace's answer-only RLVR results and
the exact information required to reproduce training and evaluation. Do not
expand the experiment scope or rerun expensive jobs without approval.

## Read First

- `AGENTS.md`
- `docs/README.md`
- `docs/workflows/PUBLIC_RELEASE/README.md`
- `docs/RLVR_TRAINING_STRATEGY.md`
- `docs/workflows/RLVR_TRAINING_RUNBOOK.md`
- `docs/workflows/EXTERNAL_BENCHMARK_EVAL.md`
- `rlvr/README.md`
- `rlvr/REWARD_MODES.md`
- Existing consolidated files under `results/`

## Ownership

Own canonical release metrics, answer-only RLVR release/run documentation,
dataset and model card source, and focused reproducibility scripts. Do not edit
the paper, root README, task code, gallery, or public documentation prose.

## Required Deliverables

1. Identify the exact base and answer-only GRPO checkpoints for Qwen2.5-VL-3B
   and Qwen2.5-VL-7B.
2. Reconcile existing result files into one canonical machine-readable table.
3. For every benchmark record:
   - model and checkpoint;
   - split/subset and sample count;
   - decoding/evaluation mode;
   - base score;
   - trained score;
   - absolute delta;
   - scorer/extractor version;
   - source result artifact.
4. Define the exact macro-average used for headline gains and verify it from
   the per-benchmark rows.
5. Document dataset revision, prompt mode, reward mode, training steps, batch
   sizes, optimizer settings, checkpoint selection, and compute where records
   support them. Mark unknown information as unknown rather than inferring it.
6. Provide clean answer-only training, checkpoint export, and evaluation
   commands.
7. Prepare public dataset and model card sources that match the actual release.
8. Record task-conditioned and answer-and-annotation modes as experimental;
   do not mix their results into answer-only headline numbers.

## Result Integrity Rules

- Do not cherry-pick benchmark subsets after observing outcomes.
- Do not compare differently sized subsets as though they were identical.
- Do not silently substitute temperature, prompt, extractor, or judge modes.
- Do not copy spreadsheet values manually when a source CSV/JSON can be parsed.
- Do not claim superiority over another system without a controlled comparison.
- Do not run costly inference or training unless the user approves the command
  and expected cost first.

## Validation

Add a script or test that recomputes headline averages from the canonical rows.
Cross-check a sample of rows against raw outputs or the closest authoritative
result artifacts. The paper and docs agents must be able to consume the table
without transcribing values.

Use the shared handoff format in `README.md` and list all canonical tables,
cards, commands, and unresolved provenance gaps.

