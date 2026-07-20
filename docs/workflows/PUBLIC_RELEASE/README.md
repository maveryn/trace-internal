# Public Release Workstreams

This folder contains the handoff briefs for the Trace public-release cycle.
Each brief is self-contained enough to give to one agent, but this file is the
coordination contract shared by all workstreams.

The internal coordinator should track cross-workstream completion in
[`RELEASE_COMPLETION_CHECKLIST.md`](RELEASE_COMPLETION_CHECKLIST.md). That
checklist starts from the verified GPU-host handoff and distinguishes internal
provenance work from the public `main` and `rlvr` release surfaces.

The frozen answer-only training/evaluation boundary, reviewed per-file map,
canonical results, and historical exclusions are summarized in
[`RLVR_RELEASE_INPUT_FREEZE.md`](RLVR_RELEASE_INPUT_FREEZE.md).

## Workstreams

1. [`PAPER.md`](PAPER.md) - arXiv technical report, figures, references, and PDF.
2. [`RELEASE_ENGINEERING.md`](RELEASE_ENGINEERING.md) - repository hygiene,
   packaging, security, CI, and release gates.
3. [`README_AND_DOCS_SITE.md`](README_AND_DOCS_SITE.md) - root README, public
   documentation, and GitHub Pages.
4. [`TASK_CATALOG_AND_GALLERY.md`](TASK_CATALOG_AND_GALLERY.md) - generated
   task catalog, representative examples, and web assets.
5. [`RLVR_RESULTS_AND_REPRODUCIBILITY.md`](RLVR_RESULTS_AND_REPRODUCIBILITY.md)
   - canonical answer-only results, run metadata, and release cards.
6. [`PUBLIC_API_AND_EXAMPLES.md`](PUBLIC_API_AND_EXAMPLES.md) - public API
   examples, replay and verification demonstrations, and smoke tests.

## Before Starting

1. Read `AGENTS.md` and `docs/README.md`.
2. Read this file and the assigned workstream brief.
3. Confirm the assigned workstream and base commit with the user or release
   coordinator before editing.
4. Use an isolated branch and worktree. Do not work in another agent's dirty
   worktree. For the current cycle, non-paper release work is expected to branch
   from `release/public-v0.1.0` unless the coordinator supplies a newer base.
5. Record the base commit in the final handoff.

## Shared Scope

The release presents Trace as an extensible RLVR environment with 1,000
procedural visual-reasoning tasks across 11 domains. The validated experimental
result is answer-only RLVR. Annotation generation may be documented briefly as
implementation-auditing metadata and a future supervision capability, but it
is not a headline result.

Do not make task-behavior, taxonomy, prompt, renderer, or reward changes unless
a release-blocking defect is demonstrated and the user approves the change.
This cycle packages and explains the reviewed task environment; it does not
restart task design.

## Ownership Boundaries

- Only the paper agent edits `paper/**`.
- Only the README/docs agent edits the root `README.md`.
- Release engineering owns root packaging configuration, security cleanup, and
  general CI. The docs agent owns only the documentation deployment workflow.
- The catalog agent owns generated catalog scripts and gallery assets.
- The results agent owns canonical release metrics and RLVR release metadata.
- The API agent owns public examples and their focused tests.
- No agent may copy numbers into a second hand-maintained results source.
- No agent may add credentials, local paths, review databases, logs, generated
  task-review artifacts, model caches, or private output to a commit.
- Do not push branches, upload artifacts, publish packages, create releases, or
  modify Hugging Face repositories unless the user explicitly requests it.

If a required change crosses an ownership boundary, stop and write a concise
handoff request to the owning agent. Do not edit the shared file opportunistically.

## Shared Interfaces

Parallel work converges through three artifacts:

- The results agent provides one canonical machine-readable answer-only result
  table for the paper and documentation agents.
- The catalog agent provides generated inventory and gallery manifests for the
  documentation and paper agents.
- Release engineering publishes the final installation/import contract for the
  documentation and API agents. A package-wide import rename requires explicit
  user approval before implementation.

Agents may use temporary placeholders while waiting for these artifacts, but
must not invent final values or duplicate the source data.

## Required Handoff

Every agent finishes with:

```text
Workstream:
Branch:
Base commit:
Final commit(s):
Changed paths:
Validation run:
Generated artifacts:
Open decisions or blockers:
```

The worktree must be clean after the agent's commit, apart from files that were
already dirty before that agent began and are outside its ownership.

## Integration Order

1. Merge release-engineering decisions that affect installation or imports.
2. Rebase and validate public API examples against that installation contract.
3. Merge canonical results and generated catalog/gallery artifacts.
4. Finalize README and documentation references to those artifacts.
5. Finalize the paper using the same canonical results and approved figures.
6. Run clean-install, package, documentation, link, test, and PDF gates.
7. Publish only after the user reviews the integrated repository and report.
