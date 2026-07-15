# Trace Paper Workspace

The tracked manuscript lives in [`trace/`](trace/). Its current arXiv/preprint
presentation uses the official NeurIPS 2026 LaTeX style. The paper roadmap,
venue checklist, bibliography, and provenance notes live beside the source.

The related-work inventory and locally retained deep-reading papers are indexed
in [`reference-papers/README.md`](reference-papers/README.md). Local working
copies of the DMLR and NeurIPS template archives, the OpenThoughts paper, the
Sphinx source archive, and `ml-codex-skills` are intentionally ignored. They
are writing aids, not manuscript dependencies.

Build the draft with:

```bash
make -C paper/trace
```

Paper source and full-resolution authoring assets remain in the internal
workspace. The public Trace repository carries only the compiled PDF and an
arXiv link; the arXiv source bundle is a separate submission artifact.
