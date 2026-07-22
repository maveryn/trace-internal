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
| Base vs Trace RLVR benchmark table | Canonical `trace_eval_v1` metadata from the RLVR handoff | Complete; generated source, comprehensive result table, and checksums are recorded in `results_assets.json` |
| Base vs Trace external benchmark confidence intervals | Pinned row-level score and extraction ledgers for the 24-benchmark suite | Complete; 10,000 paired item-bootstrap replicates per benchmark and scale are recorded in `external_benchmark_bootstrap_cis.json` |
| Trace validation table | Canonical 2,000-instance validation report | Complete; generated table and source checksum are recorded in `results_assets.json` |
| Taxonomy-conditioned Trace validation analysis | Canonical 2,000-instance validation row scores, pinned validation dataset, and code-authoritative task metadata | Complete; 10,000 task-cluster bootstrap replicates and generated outputs are recorded in `iid_taxonomy_analysis.json` |
| RLVR training dynamics | Finished 3B and 7B W&B run histories | Complete; 500 updates per run and generated-figure checksums are recorded in `training_dynamics.json` |

## Training and result assets

The paper's 3B, 7B, and contextual-baseline results are generated with:

```bash
python paper/trace/scripts/build_results_assets.py
```

The builder pins and validates the evaluation-suite SHA-256, three canonical
score-file SHA-256 values, the matched-IID report SHA-256 value, result
schemas, run ids, model sets, seeds 42--44, all 24
benchmark identities, all six categories, and the 32,805-row suite total. It
then writes:

- `data/trace_eval_v1_paper_results.json`, the combined machine-readable paper
  result source;
- `tables/main_results.tex`, the complete benchmark-by-model result matrix;
- `tables/training_configuration.tex`; and
- `tables/evaluation_suite.tex`.

Exact input and output hashes are in `provenance/results_assets.json`.
`data/training_runs.json` is a paper-facing snapshot of the immutable 3B and 7B
model metadata and the completed W&B runs
`llm-reasoning-rl/trace_easyr1/kijsydl8` and
`llm-reasoning-rl/trace_easyr1/usqbkpd6`, retrieved on 2026-07-18. It records
the shared dataset revision, optimizer/reward settings, hardware, runtime, and
final IID monitoring values. The evaluation artifact revisions remain
`maveryn/trace-eval-runs@4178a839b689babe16f8ac36f0de7b1b2c5ef36c`
for the 3B and 7B base/Trace/Vero runs and
`maveryn/trace-eval-runs@4ca25af7a4d7daa644e6f35e070dbed1af078321`
for the three RL baseline runs.

The training-dynamics snapshot and figure are refreshed and rebuilt with:

```bash
python paper/trace/scripts/build_training_dynamics.py --refresh
```

The script retrieves all 500 update records from each pinned W&B run and stores
the reward, response-length, answer-accuracy, clipping, and sampled-token
entropy metrics in `data/training_dynamics_wandb.json`. Offline paper builds use
that snapshot and do not contact W&B. Figure generation applies only the
documented 25-update moving average; raw per-update values remain in the figure
and data file. Exact source, script, run-id, and output hashes are recorded in
`provenance/training_dynamics.json`.

The taxonomy-conditioned validation analysis is rebuilt with:

```bash
python paper/trace/scripts/build_iid_taxonomy_analysis.py
```

The script joins the immutable 2,000-instance validation dataset to pinned
row-level scores, then reads each active task's code-authoritative domain,
answer interface, query structure, and operation-family declarations. It
computes paired Base-to-Trace accuracy gains and 95% bootstrap percentile intervals from
10,000 bootstrap replicates that resample tasks while retaining both unseen
instances for each sampled task. Operation-family memberships are multi-label,
so those rows overlap and are not another partition of the validation set. The
machine-readable estimates are written to `data/iid_taxonomy_analysis.json`,
the paper figure to `figures/iid_taxonomy_gains.pdf`, and exact source,
parameter, script, and output hashes to
`provenance/iid_taxonomy_analysis.json`. The generated assets are committed so
ordinary paper builds remain offline.

External benchmark confidence intervals are rebuilt with:

```bash
python paper/trace/scripts/build_external_bootstrap_cis.py
```

For each of the 24 benchmarks at 3B and 7B, the script keeps Base and Trace
scores paired by benchmark item, carries all three decoding seeds with the
sampled item, and computes 95% bootstrap percentile intervals from 10,000 bootstrap
replicates. Sixteen benchmarks use archived row-score ledgers directly. WeMath
reconstructs its official strict metric over 525 paired problem families. For
the seven official scorers whose public ledgers retain only aggregate scores,
the script reconstructs item scores from pinned extraction ledgers and the
scorer implementation, and verifies the recovered mean against every immutable
aggregate before resampling. TableVQABench uses a split-stratified item
bootstrap that recomputes its five-component official macro score. Any
one-item-equivalent centering needed to reproduce an aggregate after archived
spreadsheet type coercion is recorded per model and seed. Estimates are written
to `data/external_benchmark_bootstrap_cis.json`, and the appendix table is
written to `tables/external_bootstrap_cis.tex`; source revisions, scorer hashes,
parameters, adjustments, and output hashes are recorded in
`provenance/external_benchmark_bootstrap_cis.json`. These assets are not a
dependency of the ordinary offline paper build.

## External baseline identities

System and dataset names in the related-work discussion are distinct from the
model artifacts used in experiments. The canonical evaluated checkpoint names,
repositories, and revisions are recorded in
`rlvr/experiments/final_answer_only_manifest.json`. The paper-facing labels are:

- `Game-RL Qwen2.5-VL-7B` for
  `OpenMOSS-Team/Game-RL-Qwen2.5-VL-7B` at revision
  `205b5934ce70504cfd6ae26b16f705d0b98b9306`;
- `Sphinx Qwen2.5-VL-7B 500` for `xashru/sphinx_qwen7b_500` at revision
  `6ffefb03d5cb0767683bfb42a084ea86b707ef9a`;
- `PCGRPO Qwen2.5-VL-7B Jigsaw CARE` for
  `armenjeddi/PCGRPO-Qwen2.5-VL-7B-Jigsaw-with-curriculum-with-grpo-care` at
  revision `921bbced4176f5d362e98c843a57656c5d78dad7`;
- `Vero-Qwen25-7B` for `zlab-princeton/Vero-Qwen25-7B` at revision
  `180e84be5acb2aa887cf51015b84b6a6e453ee90`.

GameQA is the dataset introduced by Game-RL, not the system or checkpoint name.

## Method, taxonomy, coverage, and quality assets

The title-page lockup is generated from the canonical vector brand asset with:

```bash
make -C paper/trace figures/trace-logo.pdf
```

The source is `assets/brand/trace-logo.svg`; the paper build converts it to PDF
without rasterization.

Figures `fig:domain-montage`, `fig:reachable-pipeline`, and
`fig:taxonomy-boundaries` are generated from pinned task-review instances.
Figure `fig:environment-statistics` is generated from the active inventory and
combines domain task counts, scene counts, and typed answer-interface counts.
Query-branch counts remain available in the coverage manifest but are reported
in prose rather than a dedicated figure. Figure `fig:domain-operation-matrix` is an
exhaustive multi-label summary generated from the literal
`reasoning_operations` declaration in every active task. Task documents mirror
those declarations; generation fails on missing metadata,
code/doc drift, invalid vocabulary or order, or direct-retrieval exclusivity
violations. Figure
`fig:rendering-variation` executes one pinned task
seed under six explicit render profiles and fails unless the task, query,
prompt, instance trace, and typed answer remain identical. Figure
`fig:rendering-pipeline` documents the corresponding conceptual control
boundaries. Table `tab:rendering-variation-profiles` is generated from the
pinned rendering sweep. All eight figures and one table are rebuilt by:

```bash
python paper/trace/scripts/build_method_figures.py
```

The builder verifies each pinned source task id, query id, instance seed,
review-data hash, and image hash before writing the paper assets. It also
requires current task-program definitions before computing answer-type, query-branch,
and cross-domain operation summaries. The
rendering sweep records each profile override, resolved render metadata,
semantic hash, prompt hash, answer, source-image hash, and final PDF hash. The
operation matrix does not infer labels from filenames or keywords. Its
provenance record contains every reviewed assignment, its source path
and source SHA-256, and a SHA-256 hash of the corresponding task-program
definition (the source document's `Program Contract` body), so source changes are visible even when the task id is
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
for rule-heavy outliers. A small set of publication-title and display-question
overrides removes mechanical identifier wording and repetitive prompt
scaffolding. Source-question hashes prevent stale curated wording from
surviving a prompt change. Recorded answers are preserved. Regenerate the atlas
with:

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
