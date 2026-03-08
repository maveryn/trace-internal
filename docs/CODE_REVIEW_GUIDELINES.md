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
11. For mixed source-category + target-answer tasks, sample both distributions explicitly and validate realized distributions.
12. When sibling tasks share most generation/prompt/trace flow, extract a shared base/helper and keep task modules objective-specific.
13. Keep visual style ranges in domain/task-group config rather than hardcoded task-module constants.
14. After contract changes, remove deprecated helper paths and stale trace fields in the same patch.
15. If sibling tasks repeat the same fallback constants, centralize them in a task-group shared defaults helper instead of duplicating per-task literals.
16. Keep docs indexes contract-driven: avoid stale links/references after renames by updating docs in the same patch as code/config changes.
17. Remove orphaned helpers immediately when no call sites remain, and promote repeated generic transforms (for example sequence rotation) into task-shared utilities.
18. For visual/background/noise config parsing, consolidate repeated min/max normalization into `trace/core/visual` shared helpers instead of re-implementing range parsing per module.
19. Prompt JSON examples must be contract-valid for the active task/query/output-mode variant (correct keys, answer type, and evidence cardinality/semantics); reject mismatched examples.
20. If one task supports multiple evidence cardinalities across variants, require variant-aware prompt example selection (not one static example for all variants).

## 3) Process rule
When a new reusable issue is discovered:
1. Add one distilled rule here.
2. Update `docs/TASK_AUTHORING.md` if authoring behavior should change.
