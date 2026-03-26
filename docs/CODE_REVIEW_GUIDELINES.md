# TRACE Code Review Guidelines

Use this checklist during implementation and refactor reviews.

## 1) Required review checklist
1. Helper placement is correct (`core -> tasks/shared -> domain/shared -> task-local`).
2. No duplicate deterministic utility logic was introduced.
3. Prompt text remains externalized in bundle assets.
4. Answer/evidence/witness are consistent from one execution trace.
5. Determinism holds for fixed seeds and emitted ordering.
6. Public API surfaces (`__all__`, package exports) only include active consumers.
7. Docs were updated for changed contracts or module boundaries.
8. Task naming contract holds: `task_id` matches `task_<domain>_<task_group>_<task_name>` and module filename is `<task_name>.py` in the corresponding domain/task-group path.
9. Task docs stay in sync: each active `task_id` has `docs/tasks/<task_id>.md` and `docs/tasks/README.md` links match active tasks.

## 2) Distilled recurring findings
1. Promote helpers only when reuse is real (second consumer), and keep representation adapters separate from representation-agnostic algorithms.
2. Remove pass-through wrappers/migration shims after call sites migrate; keep module exports narrow and avoid dead re-exports.
3. Keep task contracts minimal (`TaskOutput`, trace fields, public types/functions) and demote private-only symbols after refactors.
4. Reuse canonical shared aliases/helpers instead of duplicating equivalent local utilities or normalization logic.
5. Keep prompt text externalized; verify deterministic variant selection and complete emitted prompt metadata for all output modes.
6. Source static prompt slot text from prompt config/templates; enforce required prompt/config keys with fail-fast shared helpers.
7. Enforce strict config schema usage: defaults in `shared`, task-specific deltas in `task_overrides`, no legacy flat-key reintroduction.
8. Keep tests behavior-focused: shared-family invariant tests first, task tests for task-specific behavior, and avoid brittle literal-default assertions.
9. For geometry feasibility, compute bounds from selected candidates (not global worst-case margins) and validate acceptance under default ranges.
10. Require overlap-aware label placement for labeled geometry; reject fixed/radial placements that ignore line/label collisions.
11. For task reviews, use `scripts/run_task_review.py` (`--mode full` by default); enforce distribution checks per `task_variant`, fail on `no_samples_collected`, and use `--mode inspection` when only visual/prompt review is intended.
12. When sibling tasks share most generation/prompt/trace flow, extract a shared base/helper and keep task modules objective-specific.
13. Keep visual style ranges in domain/task-group config rather than hardcoded task-module constants.
14. After contract changes, remove deprecated helper paths and stale trace fields in the same patch.
15. If sibling tasks repeat the same fallback constants, centralize them in a task-group shared defaults helper instead of duplicating per-task literals.
16. Keep docs indexes contract-driven: avoid stale links/references after renames by updating docs in the same patch as code/config changes.
17. Remove orphaned helpers immediately when no call sites remain, and promote repeated generic transforms (for example sequence rotation) into task-shared utilities.
18. For visual/background/noise config parsing, consolidate repeated min/max normalization into `trace/core/visual` shared helpers instead of re-implementing range parsing per module.
19. Prompt JSON examples must be contract-valid for the active task/variant/output-mode contract (correct keys, answer type, and evidence cardinality/semantics); reject mismatched examples.
20. If one task supports multiple evidence cardinalities across variants, require variant-aware prompt example selection (not one static example for all variants).
21. For domain-agnostic shared helpers (for example color sampling), keep primary behavior tests in shared test modules rather than domain-specific task tests.
22. Keep test suites compact by merging overlapping assertions into behavior-centric tests; avoid parallel tests that validate the same contract surface.
23. Treat prompt-slot values as punctuation-neutral fragments; keep sentence punctuation in template variants to avoid duplicated punctuation in rendered prompts.
24. For task-group visual defaults, remove zero-weight/no-op style keys and avoid fallback style merge when a family requires a strict style subset.
25. For new/distribution-changing tasks, run answer-distribution checks at least at 100 samples and report: `unique_answers`, `max_answer_count / sample_count`, and numeric bin summaries such as `max_five_bin_frequency`; use the first two as hard anti-degeneracy gates unless a task family explicitly adds tighter distribution rules.
26. Distribution-check tooling must evaluate rules per task variant at fixed per-variant sample targets, and worker parallelism must not change collected-answer outcomes for fixed seeds.
27. Keep prompt bundles tight: use exactly 5 strong variants per required template list, and remove filler paraphrases that make prompts less natural or less precise.
28. When prompt fragments append variant-specific label lists, route that formatting through one shared helper so punctuation and sentence boundaries stay consistent across tasks.
29. Keep task-level `question_text` slots free of output-format duplicates when the task template already supplies that instruction (for example rounding/precision wording).
30. When graph-paper evidence only needs coordinates (not label identity), prefer unlabeled `graph_point` / `graph_point_set` evidence and keep any label-to-point correspondence in trace projections instead of the primary task answer contract.
31. When scene layout constrains which target answers can fit, sample the target answer from the feasible support before placement/layout so easier-to-fit values do not become overrepresented by construction.
32. When target-conditioned feasibility logic can be reused across sibling shape variants, keep the support probe/sampler in a domain-shared geometry helper rather than embedding task-local rejection loops.
33. When a generic procedural sampler collapses one variant to a tiny answer set, prefer a constructive variant-specific sampler that preserves the task contract while broadening feasible support.
34. When review/sample scripts need the same evidence-projection or overlay-rendering behavior, centralize it in `trace/core/review_overlays.py` so graph-unit evidence is consistently projected into pixel space before drawing.
35. When trace payloads store pixel-space projections of evidence, prefix those projected keys with `pixel_` (for example `pixel_point_set`, `pixel_point_map`) so they cannot be mistaken for primary evidence-type contracts.
36. Prompt JSON examples for point-based evidence must use valid non-degenerate layouts (not placeholder collinear points) so examples match the intended task semantics.
37. When a task ships variant-specific JSON examples in config, prefer those over generic placeholder builders whenever the answer depends on the illustrated geometry (for example area vs perimeter on the same point layout).
38. For polygon-based tasks, reject adjacent collinear vertices in shared polygon samplers so an `n`-gon never visually collapses into fewer effective sides.
39. When target-answer sampling uses feasible-support cycling, do not key that selection directly off the same raw seed used for task-variant choice; use `_sampling_index` when provided and otherwise derive a namespaced deterministic index so variant choice and target answer do not become accidentally coupled.
40. When a feasibility probe selects a target answer before layout, carry forward the minimum required scene capacity from that same probe; do not assume a loose bound like `answer + margin` is enough for all constructive variants.
41. When a second sibling task starts reusing a helper module named after the first task/objective, rename that module to the shared family concept immediately (for example `analytical_3d_volume.py` -> `analytical_3d_solids.py`) instead of keeping a misleading task-specific container.
42. When a prompt-family stem already describes the image context, keep task-layer prompt variants focused on the question itself; do not repeat phrases like `from the image`, `from the figure`, or `from the diagram` on the next line.
43. For graph-paper tasks that require points strictly inside the plotted grid, compute feasibility/capacity against the visible interior cell span (including padding/partial-edge effects) before selecting target answers or scene layouts.
44. When adding constructive shape catalogs that feed a shared instance type, validate every shared invariant that instance encodes (for example integer perimeter on `PolygonInstance`), not just the task's primary target metric.
45. When a second analytical objective needs the same prompt-slot, answer-bound, or variant-resolution helper flow, move those helpers into an analytical-family shared module instead of keeping them under a 3D-only or objective-only filename.
46. In supersampled scenes, verify that geometry primitives and label/annotation placement use the same coordinate scale; mismatched scaled-vs-unscaled drawing can make text appear detached even when placement logic is correct.
47. For analytical scenes with segment- or point-anchored text, cap scene occupancy and use collision-aware local placement so numeric annotations and labels fall beside geometry instead of crossing lines or crowding the border.
48. When a new board/scene family needs dynamic rectangular canvases, extend shared visual/background helpers to support non-square sizes instead of adding task-local background rendering forks.
49. When prompts query a named color, include its canonical hex code in square brackets (`name [#RRGGBB]`) and route that formatting through a shared helper rather than task-local string assembly.
50. Tile-domain boards should not sit on graph-paper or external grid backgrounds unless the task explicitly depends on that second coordinate scaffold; keep the board as the only grid-like structure in tile scenes.
51. When a second tile objective needs 4-neighbor grid helpers outside shortest-path logic, move those helpers into a grid-family shared module (for example `grid_graph.py`) instead of reusing or extending a path-named module.
52. When multiple tile task groups use the same background/noise fallback plumbing, promote those loaders into one tile-shared visual-defaults module instead of cloning near-identical task-group wrappers.
53. For tile path tasks whose answer is a uniform per-step graph distance, use square cells and tile-coordinate path evidence so the image does not imply unequal horizontal vs vertical move costs.
54. When a second tile task group needs named-color board rendering or palette/scene serialization, move that logic into a tile-shared named-color board module instead of importing helpers from a `tile/count`-named file.
55. For extremum-over-components tasks, reject non-unique winning components and expose only the winning component as prompt-facing evidence; keep the full component partition in trace.
56. For row/column run-count tasks, expose one canonical witness run per qualifying line in prompt-facing evidence instead of every overlapping or repeated run on that same line.
57. For transition tasks with one uniquely optimal mover, keep all mover outcomes in trace but expose only the winning mover's trajectory as prompt-facing evidence.


## 3) Process rule
When a new reusable issue is discovered:
1. Add one distilled rule here.
2. Update `docs/TASK_AUTHORING.md` if authoring behavior should change.
