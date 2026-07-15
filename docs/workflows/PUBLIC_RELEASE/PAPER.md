# Agent Brief: Paper

## Objective

Produce the Trace arXiv technical report. The report should establish Trace as
an extensible, executable visual RLVR environment and accurately present the
validated answer-only training results. It should read as a research paper,
not as internal project documentation.

## Read First

- `AGENTS.md`
- `docs/README.md`
- `docs/workflows/PUBLIC_RELEASE/README.md`
- `paper/README.md`
- `paper/trace/README.md`
- `paper/trace/ROADMAP.md`
- `docs/contracts/BLUEPRINT.md`
- `docs/contracts/SYSTEM_ARCHITECTURE.md`
- `docs/contracts/TAXONOMY.md`
- The canonical result artifact delivered by the results workstream

## Ownership

This agent exclusively owns `paper/**`. Do not edit repository code, root
documentation, RLVR scripts, or canonical result files.

## Required Scope

- Position Trace around task-environment breadth, executable task contracts,
  deterministic generation and replay, exact answer verification, and future
  extensibility.
- State the release scale precisely: 1,000 tasks across 11 domains.
- Use answer-only RLVR as the primary and validated experimental method.
- Describe annotation in no more detail than needed for an accurate system
  account: program-derived annotations supported implementation auditing and
  may enable future grounded supervision; reported results use answer-only RLVR.
- Do not present task-conditioned or annotation-supervised gains unless the
  user later approves a completed, controlled result for inclusion.
- Compare with RLVR-specific synthetic-data systems without claiming an
  apples-to-apples superiority that the experiments do not establish.
- Emphasize that Trace scales task and reasoning-program diversity, not merely
  generated row count.

## Deliverables

- Completed abstract, introduction, related work, system design, taxonomy,
  data-generation and quality sections, experiments, results, limitations,
  conclusion, and appendix.
- Exact 3B and 7B tables sourced from the canonical result artifact.
- Publication-quality figures with recorded provenance.
- Complete and deduplicated bibliography.
- A clean compiled PDF for the public repository and an internally retained,
  arXiv-compatible source tree.
- Updated paper README and roadmap reflecting actual completion state.

## Writing Rules

- Do not copy project-management prose into the paper.
- Do not use unsupported superlatives or broad claims such as covering all
  visual reasoning.
- Report absolute scores, deltas, evaluation protocol, training budget, and
  aggregation rules where available.
- Distinguish dataset size from task-contract and domain breadth.
- Keep current limitations explicit: synthetic visual grammars, exact-verifier
  task scope, and incomplete evaluation of annotation-aware training.

## Validation

From `paper/trace/`, run the documented clean build, inspect the complete log,
and visually inspect every page of the resulting PDF. Resolve missing
references, overfull layout that harms readability, placeholder text, and
low-resolution figures before handoff.

Use the shared handoff format in `README.md` and include the final PDF path.

## Publication Boundary

- Keep LaTeX sources, figure-generation scripts, provenance records,
  full-resolution atlas images, and reference-paper working copies out of the
  public Trace code repository.
- Publish the compiled paper PDF in the public repository and link to the arXiv
  record when available.
- Prepare the arXiv source upload as a separate submission bundle. It is not a
  GitHub release asset and must not be copied into the public code tree.
