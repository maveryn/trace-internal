# Agent Brief: README And Documentation Site

## Objective

Create the public entry point for Trace: a concise root README and a polished,
searchable GitHub Pages documentation site that makes the environment useful
to researchers and contributors without exposing internal process clutter.

## Read First

- `AGENTS.md`
- `docs/README.md`
- `docs/workflows/PUBLIC_RELEASE/README.md`
- `docs/workflows/DOC_STRUCTURE.md`
- `docs/workflows/DOCS_AND_SKILLS_MAINTENANCE.md`
- `docs/contracts/BLUEPRINT.md`
- `docs/contracts/SYSTEM_ARCHITECTURE.md`
- `docs/contracts/TAXONOMY.md`
- The installation contract supplied by release engineering
- The result and gallery manifests supplied by their owning workstreams

## Ownership

This agent is the only agent allowed to edit the root `README.md`. It owns the
MkDocs configuration, public-facing documentation pages, and the documentation
deployment workflow. It does not own task behavior, paper content, canonical
metrics, gallery-generation code, or general package CI.

## Required Deliverables

### Root README

- Immediate statement of purpose and a representative visual montage.
- Accurate release-scale summary: 1,000 tasks and 11 domains.
- Links to installation, quickstart, task catalog, dataset, models, paper, and
  contribution guide.
- A short answer-only result summary populated from canonical result data.
- Minimal installation and first-generation example.
- Architecture summary and deterministic replay/verifier highlights.
- No internal review-app, migration, calibration, or worktree instructions.

### Documentation Site

Use MkDocs Material unless a repository constraint makes it unsuitable. Build
from canonical repository documentation rather than creating a second policy
source. Provide a curated public navigation with:

1. Overview
2. Quickstart
3. Core architecture and task model
4. Task catalog and gallery
5. Dataset and RLVR usage
6. Extending Trace
7. Contributing and validation

Annotation needs only a concise explanation: it is optional program-derived
metadata used for visual auditing and possible future supervision; reported
models use answer-only RLVR. Do not make it a landing-page feature.

### Deployment

- Add a GitHub Pages workflow limited to documentation deployment.
- Fail on broken internal links, missing generated references, and MkDocs build
  errors.
- Keep generated site output untracked.

## Quality Bar

- A new user can identify what Trace is within the first screen.
- A new user can install and generate one example in a few minutes.
- Code snippets are executable and match the final package/import contract.
- Result numbers come from the canonical result artifact.
- Catalog counts and images come from generated manifests.
- Public navigation does not expose stale or internal workflow documentation.
- The README remains useful without the hosted site.

Use placeholders only while waiting for another workstream and remove them
before handoff. Use the shared handoff format in `README.md` and include the
local docs build command and output.

