# Trace Manuscript

This is the tracked LaTeX source for the Trace paper. The current build is a
named-author arXiv preprint using the official NeurIPS 2026 `preprint` style.

## Start here

1. Read [`ROADMAP.md`](ROADMAP.md) for the paper thesis, section plan, required
   evidence, and writing order.
2. Read [`DMLR_SUBMISSION_CHECKLIST.md`](DMLR_SUBMISSION_CHECKLIST.md) before
   preparing a later DMLR submission; it is a venue checklist, not the current
   presentation template.
3. Record every numeric table and figure source in
   [`provenance/README.md`](provenance/README.md).
4. Build with `make -C paper/trace` from the repository root.

## Source layout

- `main.tex`: NeurIPS-preprint entry point and section order.
- `preamble.tex`: manuscript-only macros and packages.
- `sections/`: prose organized by rhetorical role.
- `references.bib`: references used by the manuscript.
- `scripts/`: deterministic paper-asset builders; run
  `python paper/trace/scripts/build_method_figures.py` from the repository root
  to regenerate the method, taxonomy, coverage, and rendering figures and
  tables. Run
  `python paper/trace/scripts/build_scene_atlas.py --review-root review/task-reviews`
  to regenerate the domain-stratified appendix atlas. The atlas uses twelve
  seeded examples per domain in a three-column by four-row page layout.
- `figures/` and `tables/`: generated, publication-ready assets.
- `provenance/`: claim, table, and figure provenance records.
- `neurips_2026.sty`: vendored, unmodified official NeurIPS 2026 style file.

The current manuscript is a compileable outline, not a submission draft.
Bracketed TODOs identify evidence or author decisions still required. Do not
replace them with unsupported estimates.

## Distribution boundary

The LaTeX source, figure builders, provenance records, and full-resolution
atlas inputs are internal authoring artifacts. The public Trace code repository
should publish only the compiled paper PDF and link to the arXiv record. The
arXiv source bundle is prepared and uploaded separately; it is not part of the
public code-repository release.
