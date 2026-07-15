# Paper Provenance Ledger

Every numeric table, plot, and quantitative prose claim must be entered here
before it is treated as final.

## Required record

For each artifact, record:

- manuscript label and short description;
- claim category: contract, inventory, dataset, or experiment;
- source file(s) or dataset revision;
- Trace git commit;
- generation command or script;
- important parameters and seeds;
- generated output path and checksum;
- reviewer and verification date.

## Initial sources

| Planned artifact | Canonical source | Status |
|---|---|---|
| Active domain/scene/task inventory | Active task registry and `docs/ACTIVE_TASK_INVENTORY.md` | Counts verified and recorded by `scripts/build_method_figures.py` on 2026-07-14 |
| Dataset split and row counts | Dataset manifests plus `docs/RLVR_TASK_SPLIT_PLAN.md` | Must bind to public dataset revision |
| Base vs answer-RLVR benchmark table | Canonical consolidated result artifact from the RLVR handoff | Pending exact source binding and protocol cross-check |

## Method, taxonomy, coverage, and quality assets

The title-page lockup is generated from the canonical vector brand asset with:

```bash
make -C paper/trace figures/trace-logo.pdf
```

The source is `assets/brand/trace-logo.svg`; the paper build converts it to PDF
without rasterization.

Figures `fig:domain-montage`, `fig:reachable-pipeline`, and
`fig:taxonomy-boundaries` are generated from pinned task-review instances.
Figure `fig:domain-landscape` is generated from the active inventory. Figure
`fig:answer-reward-summary` summarizes the typed answer interfaces governed by
the shared exact-match reward contract. Query-branch counts remain available
in the coverage manifest but are reported in prose rather than a dedicated
figure. Figure `fig:domain-operation-matrix` is an
exhaustive multi-label summary generated from the literal
`reasoning_operations` declaration in every active task. Task documents mirror
those declarations; generation fails on missing metadata,
code/doc drift, invalid vocabulary or order, or direct-retrieval exclusivity
violations. Figure
`fig:rendering-variation` executes one pinned task
seed under six explicit render profiles and fails unless the task, query,
prompt, semantic execution trace, and typed answer remain identical. Figure
`fig:rendering-pipeline` documents the corresponding conceptual control
boundaries. Table `tab:rendering-variation-profiles` is generated from the
pinned rendering sweep. All eight figures and one table are rebuilt by:

```bash
python paper/trace/scripts/build_method_figures.py
```

The builder verifies each pinned source task id, query id, instance seed,
review-data hash, and image hash before writing the paper assets. It also
requires current task contracts before computing answer-type, query-branch,
and cross-domain operation summaries. The
rendering sweep records each profile override, resolved render metadata,
semantic hash, prompt hash, answer, source-image hash, and final PDF hash. The
operation matrix does not infer labels from filenames or keywords. Its
provenance record contains every reviewed assignment, its source path
and source SHA-256, and a SHA-256 hash of the corresponding Program Contract
body, so source or contract changes are visible even when the task id is
stable. The complete
source, environment coverage, rendering-variation, and output records are
stored in `provenance/method_figures.json`, including output
dimensions and SHA-256 checksums. Figure~1 is a PDF montage
that embeds each source review image at its original raster resolution; LaTeX
scales the images for display without downsampling their stored pixels. The
current figures were generated and visually inspected on 2026-07-15.
Regenerate them after the release commit is frozen so the recorded repository
revision identifies the final paper source.

## Representative task atlas

Appendix `app:task-atlas` contains 12 seeded examples from each of the 11
domains. The generator selects review samples deterministically, copies their
images without resampling or recompression, displays the complete semantic
question whenever it fits, and uses reviewed complete-sentence condensations
for rule-heavy outliers. Source-question hashes prevent stale condensed wording
from surviving a prompt change. Recorded answers are preserved. Regenerate the
atlas with:

```bash
python paper/trace/scripts/build_scene_atlas.py \
  --review-root review/task-reviews
```

The complete task, query, seed, source/display question, display mode,
source-path, and SHA-256 records are stored in `provenance/scene_atlas.json`;
the generated LaTeX source is
`sections/scene_atlas.tex`, and the copied images are under
`figures/scene_atlas/assets/`.

Do not use the older files under `paper/` as quantitative sources unless their
historical scope is explicitly documented and verified against the current
release.
