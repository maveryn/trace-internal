# Future Trace Proposals

This folder contains non-normative design proposals for materially different
future Trace versions. These documents do not change the active runtime,
dataset ABI, prompts, rewards, or task contracts.

Current behavior remains defined by `docs/contracts/`, `docs/workflows/`,
`docs/domains/`, and `docs/tasks/`. A proposal becomes active only through an
explicit versioned implementation and corresponding updates to those
source-of-truth documents.

## Proposals

- `NATURAL_IMAGE_SUPPORT.md` - proposal for adding a future photo domain using
  a bounded Places365-derived scene ontology, mixed Places365 and COCO asset
  sources, eligibility-aware source sampling, and leakage-safe verifier
  contracts.
- `TASK_AWARE_ANSWER_DISTRIBUTION.md` - proposal for replacing global answer-
  distribution gates with centralized, versioned profiles for visual choices,
  labels, counts, broad numeric measurements, and small outcome spaces.
- `TYPED_ANSWER_CONTRACT_V1.md` - roadmap for replacing public annotation
  prompting and separate supervision modes with one typed answer contract,
  one task prompt family, and optional internal visual witnesses.
