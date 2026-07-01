# Games Canonical Annotation Coordinate Notation Audit

Audit date: 2026-06-27

Status: resolved

Scope: current `prompts/games/**/*.json` source prompt bundles.

Rule:

- Bbox-family prompt hints/examples must use `[x0, y0, x1, y1]`.
- Segment-family prompt hints/examples must use `[[x0, y0], [x1, y1]]`.
- Legacy variable names such as `[x1, y1, x2, y2]` and
  `[[x1, y1], [x2, y2]]` are high-severity prompt-contract issues.
- Negative annotation-format wording such as `do not include` or `do not mark`
  must not appear in annotation hints.
- Missing repeated pixel-space wording is not counted here because the shared
  system prompt owns the global image-coordinate convention.

Current result:

- games prompt bundles validated as JSON: `51`
- non-canonical coordinate prompt slots: `0`
- negative annotation-format prompt slots: `0`
- canonical segment hints missing explicit `[x, y]` endpoint wording: `0`

Resolved changes:

- Normalized the previous `48` non-canonical prompt slots across `35` games
  tasks.
- Replaced `41` bbox prompt slots with canonical `[x0, y0, x1, y1]` wording.
- Replaced `7` segment prompt slots with canonical
  `[[x0, y0], [x1, y1]]` wording.
- Tightened those segment hints so they explicitly describe the segment
  endpoints as `[x, y]` points.
- Removed negative annotation-format wording from:
  - `task_games__2048__merge_count`
  - `task_games__radial_hunt_board__marked_piece_destination_count`
  - `task_games__sixteen_soldiers__marked_piece_destination_count`

Review artifacts were not regenerated because this was a prompt-only wording
normalization with no answer, annotation, rendering, sampling, or verifier
contract changes.
