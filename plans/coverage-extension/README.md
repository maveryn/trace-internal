# TRACE Coverage Extension

This folder tracks domain-by-domain coverage extensions motivated by external
benchmark failure analysis.

Domain notes:

- `charts.md`
- `games.md`
- `geometry.md`
- `graph.md`
- `icons.md`
- `illustrations.md`
- `noise_augmentation.md`
- `pages.md`
- `physics.md`
- `puzzles.md`
- `three_d.md`

Noise-profile review artifacts are generated on demand with
`generate_noise_profile_task_review.py`; generated workbooks, manifests, and
preview image folders should not be treated as source-of-truth planning docs.

Use these notes to decide whether a gap should be handled by:

- adding scene/rendering/style variation inside an existing domain,
- adding task/query variants to an existing scene,
- adding a new scene family inside an existing domain,
- or, only if necessary, creating a new domain.

Current working rule: prefer patching existing domains and scenes first. Create
new domains only when the underlying world model, renderer, metadata contract,
and task family do not fit an existing domain.
