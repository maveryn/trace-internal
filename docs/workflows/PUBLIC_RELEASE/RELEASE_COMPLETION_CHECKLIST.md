# Release Completion Checklist

This is the internal coordinator checklist for completing the Trace paper and
public code release from a new machine. It records the work that remains after
the GPU-host handoff without turning private experiment history into public
release scope.

Use this checklist with:

- [`REMOTE_ARTIFACT_HANDOFF.md`](../REMOTE_ARTIFACT_HANDOFF.md) for immutable
  source, model, dataset, evaluation, and telemetry revisions;
- [`README.md`](README.md) for workstream ownership and integration order;
- the individual workstream briefs in this directory for implementation
  details.

## Durable Starting Point

The GPU-host retirement audit passed. The following inputs are already durable:

- Internal GPU-host snapshot:
  `maveryn/trace-internal@5cea97310204b197fdacecdd83ef938c1e3b67cd`.
- Internal handoff tag: `gpu-host-handoff-20260717`, which dereferences to that
  snapshot. The `rlvr` and `codex/machine-handoff` branches may contain later
  documentation-only handoff commits.
- Public source recovery target:
  `d5d0215ff887e15c2ffafac632f27a3e0e76b5e8`.
- Public GitHub `main` and `rlvr` still point to
  `e8b27f0ab6244545d241196efa1978ab525938c6`; pushing the two recovered commits
  remains pending because the GPU-host credential lacks `workflow` scope.
- Public package contract at that target: distribution `trace-tasks`, Python
  namespace `trace_tasks`, with the internal package name left unchanged.
- Public recovery patches:
  `maveryn/trace-internal-eval-runs@a53ce5f687851532db7ba4f8c761237634b4f96a`
  under `handoff/public-repository/d5d0215/`.
- TRACE dataset:
  `maveryn/trace@e317b746b258630682367cc6a9d87dedd195113c`.
- TRACE 7B merged model:
  `maveryn/trace-qwen2.5-vl-7b@4d0f1ae8ee25022058090dbdbff61957ece7331d`.
- TRACE 3B merged model:
  `maveryn/trace-qwen2.5-vl-3b@2ec2374d5c219e6b12e26bda93d3b3adeb1e30c5`.
- Canonical 7B and 3B evaluation bundles:
  `maveryn/trace-eval-runs@4178a839b689babe16f8ac36f0de7b1b2c5ef36c`.
- Game-RL, Sphinx, and PCGRPO evaluation bundle:
  `maveryn/trace-eval-runs@4ca25af7a4d7daa644e6f35e070dbed1af078321`.
- Evaluation repository documentation head:
  `b61d7702d0c95435869597b1050c8140d5b0d1f2`.
- Internal supplementary and historical evaluation artifacts at the revisions
  recorded in `REMOTE_ARTIFACT_HANDOFF.md`.
- Finished W&B runs and resolved training configurations for TRACE 7B
  (`usqbkpd6`) and TRACE 3B (`kijsydl8`).

Every canonical response, extraction, score, aggregate result, and provenance
manifest required to reconstruct the reported tables is remote. Do not upload
benchmark media, credentials, model caches, or machine logs as part of release
completion.

## Before Retiring The GPU Host

- [x] Push the internal handoff commit to `trace-internal` and create the
  annotated handoff tag.
- [x] Verify the TRACE dataset and merged 3B/7B model files against their HF
  LFS hashes.
- [x] Verify all canonical and baseline evaluation bundles by immutable HF
  revision.
- [x] Preserve the two unpushed public commits as tested recovery patches.
- [ ] Decide whether exact post-step-500 optimizer continuation is required.

The last item is optional for release. Exact continuation requires preserving
the approximately 109 GB 7B and 51 GB 3B EasyR1/FSDP checkpoint trees from
`/dev/shm`. The merged HF models, pinned base models, launch configurations,
reward contract, dataset revision, and W&B telemetry are sufficient for
inference, evaluation, and fresh training reproduction. If exact optimizer,
dataloader, and scheduler continuation is not required, the full FSDP trees
may be discarded.

## Bootstrap On The Next Machine

1. Clone `maveryn/trace-internal` and verify that
   `gpu-host-handoff-20260717^{}` resolves to
   `5cea97310204b197fdacecdd83ef938c1e3b67cd`.
2. Clone `maveryn/trace`. Until the public commits are pushed normally, fetch
   the private recovery bundle and apply its two patches in lexical order to a
   clean checkout of `e8b27f0ab6244545d241196efa1978ab525938c6`.
3. Verify that the recovered public tree matches
   `d5d0215ff887e15c2ffafac632f27a3e0e76b5e8`, then push `main` and `rlvr`
   using a GitHub credential with both `repo` and `workflow` scopes.
4. Create new machine-local credentials through the appropriate secret
   manager. Never copy token files into a repository or artifact bundle.
5. Download only the model, dataset, judge, and benchmark inputs needed for
   the current workstream. Verify immutable revisions and content hashes before
   using them.
6. Create separate worktrees for internal provenance work and public release
   integration. Do not develop release changes in the historical dirty
   GPU-host checkout.

For this release cycle, the recovered and pushed public `main` based on
`d5d0215ff887e15c2ffafac632f27a3e0e76b5e8` is the coordinator-supplied
release base. It supersedes the older default `release/public-v0.1.0` base
mentioned in the generic workstream instructions. Reconfirm the exact pushed
commit before creating workstream branches.

## Internal Repository Work

The internal repository remains the complete provenance and development
source. Complete these items there before or alongside public integration:

- [ ] Record the final decision about preserving or discarding the full FSDP
  continuation checkpoints.
- [ ] Freeze a reviewed allowlist of training and evaluation files that may be
  copied to the public `rlvr` branch. The allowlist must contain only the
  paper-reported 3B/7B answer-only training workflow and canonical
  `trace_eval_v1` evaluation workflow.
- [ ] Produce one canonical machine-readable release results source from the
  immutable HF score metadata. It must cover the 3B base/TRACE comparison and
  the 7B base/TRACE/VERO/Game-RL/Sphinx/PCGRPO comparison without creating a
  second hand-maintained truth source.
- [ ] Complete the 24-benchmark provenance matrix: public benchmark name,
  source repository, immutable source revision or released version, split,
  row count, license/terms, citation, official prompt route, official scorer,
  and any narrowly documented adapter.
- [ ] Review every deviation from pinned VLMEvalKit. Retain only demonstrated
  parser/scorer bug fixes needed for the reported results, with raw-output and
  code provenance. Do not change generation behavior except for queueing,
  parallelism, resume integrity, and faithful model-specific runtime setup.
- [ ] Keep baseline-specific processor aliases, recovery incidents, private
  paths, judge caches, and parser repair receipts internal. Public
  documentation may describe a required deviation, but must not expose
  private recovery machinery as an API.
- [ ] Create a public-file mapping that identifies the internal source path,
  destination public path, owner, and review status for every released RLVR
  file.
- [ ] Update the handoff receipt with the final public commit, release tag,
  artifact visibility changes, and paper citation once those exist.

Do not spend release time refactoring historical Final24/25/26/31 campaigns,
provisional benchmark candidates, or old result workbooks. They remain
internal provenance and are not the public workflow.

## Public `main` Work

Public `main` owns the task environment rather than paper training or external
benchmark evaluation:

- [ ] Push and protect the recovered public `main` head.
- [x] Establish the public package/import contract as distribution
  `trace-tasks` and Python namespace `trace_tasks`, while keeping the internal
  package name unchanged.
- [ ] Reconfirm that package/import contract after integrating the remaining
  public workstreams; do not perform another rename during release cleanup.
- [ ] Run the existing public release check in a clean clone for Python
  3.10-3.12: build the wheel, install it, run CLI smoke checks, validate
  registries/manifests, generate representative deterministic tasks, and scan
  for secrets and machine paths.
- [ ] Review the public dependency constraints and license inventory against
  the exact tested environment.
- [ ] Finalize the public API examples and verifier examples without exposing
  internal evaluation infrastructure.
- [ ] Generate the task catalog and representative gallery from the reviewed
  task inventory.
- [ ] Finalize the root README and documentation site only after installation,
  result, and gallery inputs are stable.
- [ ] Remove or rewrite references to private repositories, W&B projects,
  local paths, private review artifacts, internal issue history, and
  unreleased benchmark experiments.
- [ ] Confirm that public `main` contains no training launchers, external
  benchmark judge pipeline, model-specific compatibility fixtures, private
  evaluation receipts, or historical result dumps.

The public package test surface should cover task generation, typed answer and
verifier contracts, installation, CLI behavior, manifests, and repository
hygiene.

## Public `rlvr` Work

Public `rlvr` owns only the paper-reported training and canonical evaluation
workflow:

- [ ] Branch from the reviewed public `main` release base and record that base
  commit.
- [ ] Copy the approved 3B and 7B answer-only EasyR1 configurations, launchers,
  reward implementation, prompt asset, checkpoint merge instructions, and
  smoke/full-run commands.
- [ ] Preserve the exact answer system-prompt asset
  `rlvr/examples/prompts/trace_vero_json_system_prompt_answer.txt`, expected
  SHA-256
  `f394927d9abcfb7a1e43ef48a30c29b8c70e6facdbda314d7b27c59d8c3ae900`.
- [ ] Document the actual training contract: `prompt_answer`, exact JSON answer
  reward weight `1.0`, JSON-format reward weight `0.05`, annotation reward
  `0`, KL disabled, batch/rollout settings, validation settings, 500 steps,
  and checkpoint retention.
- [ ] Copy the canonical `trace_eval_v1` suite manifest and the minimum
  generation, extraction, scoring, verification, summary, and background
  publication code required to reproduce the 24-benchmark tables.
- [ ] Adapt released imports, resource lookup, and commands to the public
  `trace_tasks` namespace and repository-relative paths. Do not carry internal
  package assumptions or GPU-host paths into `rlvr`.
- [ ] Pin the exact VLMEvalKit commit, Qwen3-32B judge revision, dataset
  revision, prompt files, media contract, decoding settings, retry contract,
  score failure semantics, and immutable revisions for every evaluated model:
  base, TRACE, VERO, Game-RL, Sphinx, and PCGRPO.
- [ ] Provide one resumable launcher for generation followed by shared
  extraction/scoring, plus one status command and one artifact verification
  command.
- [ ] Document response-to-dataset provenance and the sanitized Parquet/HF
  artifact layout without redistributing benchmark prompts, answers, media, or
  local paths.
- [ ] Bind every released table to the canonical machine-readable result
  source and immutable artifact revisions.
- [ ] Add at most one lightweight, model-agnostic TRACE checkpoint smoke test
  if it materially protects the released workflow. Do not add Game-RL,
  Sphinx, PCGRPO, VERO, or other baseline-specific test fixtures.
- [ ] Validate the released workflow from a clean environment. Broad internal
  exploratory evaluator tests do not need to move to the public repository.

## Results, Models, And Artifact Cards

- [ ] Review the canonical 3B, 7B, and RL-baseline tables directly from
  `metadata/results/benchmark_scores.json`.
- [ ] Confirm category and overall macro calculations and seed aggregation
  against the immutable score slices.
- [ ] Preserve the documented LogicVista terminal-period repair and
  SpatialVizBench fallback counts in internal provenance. Include only the
  minimum result-relevant explanation in the public reproducibility notes.
- [ ] Prepare TRACE dataset and 3B/7B model cards with the final public code
  revision, intended use, limitations, training contract, evaluation artifact
  links, and a clearly marked paper-citation placeholder.
- [ ] Prepare the evaluation repository card with the final public evaluator
  commit and the same paper-citation placeholder.
- [ ] After the paper identifier is assigned, replace every card and public
  documentation placeholder with the final citation and verify the links.
- [ ] Decide the coordinated visibility date for the dataset, models, and
  evaluation repository. Keep them private until the reviewed public code and
  paper references are ready.
- [ ] Verify all cards and artifact links after any visibility change.

## Paper And Documentation

Follow the workstream briefs rather than maintaining parallel plans:

- [`PAPER.md`](PAPER.md): final text, approved tables/figures, references, PDF,
  and arXiv metadata.
- [`README_AND_DOCS_SITE.md`](README_AND_DOCS_SITE.md): public narrative,
  installation path, documentation site, and result links.
- [`TASK_CATALOG_AND_GALLERY.md`](TASK_CATALOG_AND_GALLERY.md): generated task
  inventory and representative visual assets.
- [`RLVR_RESULTS_AND_REPRODUCIBILITY.md`](RLVR_RESULTS_AND_REPRODUCIBILITY.md):
  canonical metrics, training/evaluation metadata, and cards.
- [`RELEASE_ENGINEERING.md`](RELEASE_ENGINEERING.md): packaging, CI, security,
  clean-install, versioning, and publication gates.
- [`PUBLIC_API_AND_EXAMPLES.md`](PUBLIC_API_AND_EXAMPLES.md): focused public
  examples and smoke validation.

No paper or README number may be copied from a provisional workbook. Generate
reported values from the canonical release results source.

## Final Validation Gates

- [ ] Public `main` and `rlvr` are clean, reviewed, and pushed at immutable
  commits.
- [ ] A clean clone passes package build/install, supported-Python CI, CLI,
  registry, deterministic-generation, verifier, manifest, secret, path, and
  license checks.
- [ ] The released RLVR smoke path and canonical evaluation metadata validate
  against the pinned models, dataset, evaluator, prompts, and artifacts.
- [ ] The benchmark provenance/license/citation matrix has no missing entry.
- [ ] Paper tables, public documentation tables, model cards, and HF cards are
  generated from or checked against the same canonical result source.
- [ ] All public links resolve without credentials except artifacts explicitly
  scheduled to become public at release time.
- [ ] The paper PDF builds cleanly and contains approved references, figures,
  limitations, and artifact links.
- [ ] A final secret/path scan finds no credentials, home-directory paths,
  private repository identifiers, or private operational logs.
- [ ] The user reviews the integrated public tree, paper, cards, and visibility
  plan before publication.

## Publication Order

1. Freeze and tag the reviewed public source commits.
2. Prepare the private dataset, model, and evaluation cards with those
   immutable commits and a paper-citation placeholder.
3. Build and verify the final documentation site and paper PDF.
4. Submit the paper and obtain its stable identifier.
5. Replace citation placeholders in cards and public documentation.
6. Publish or schedule the HF artifact visibility changes.
7. Create the GitHub release and attach only approved release artifacts.
8. Re-run public link and artifact readback checks.
9. Update `REMOTE_ARTIFACT_HANDOFF.md` with the final release identities and
   archive this checklist as completed provenance.

PyPI publication is not part of this release unless it is approved as a
separate workstream. The repository must still install cleanly from a clone and
built wheel so a later package release does not require redesign.

## Definition Of Done

The release is complete when a new user can clone the public repository,
install Trace, generate and verify representative tasks, understand the public
task and answer contracts, reproduce the paper's 3B/7B training setup, rebuild
the reported 24-benchmark evaluation tables from immutable artifacts, and
follow links to the released dataset and models without relying on private
paths, undocumented patches, or the retired GPU host.
