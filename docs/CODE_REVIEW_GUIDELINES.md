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

## 2) Distilled recurring findings
1. Do not promote representation adapters to cross-domain shared without a second real consumer.
2. Keep representation-agnostic graph algorithms separate from representation adapters.
3. Remove pass-through wrappers once canonical shared helpers exist.
4. Keep `TaskOutput` and trace contracts minimal; remove fields unused by build/validation.
5. Remove migration shims/re-export wrappers once call sites are migrated.
6. Keep package/module export surfaces narrow; avoid dead re-exports.
7. Avoid speculative shared helpers with zero consumers.
8. Keep intermediate helper steps private until imported by another module.
9. After refactors, audit public symbols again and demote externally unused public helpers/types to private names.
10. Reuse canonical shared type aliases (for example `geometry_primitives.Point`) instead of redefining equivalent local aliases.
11. Enforce strict config schema usage: defaults belong in `shared`, task-specific deltas in `task_overrides`, and unsupported legacy/flat keys should not be reintroduced.

## 3) Process rule
When a new reusable issue is discovered:
1. Add one distilled rule here.
2. Add one matching entry in `docs/LESSONS_LEARNED.md`.
3. Update `docs/TASK_AUTHORING.md` if authoring behavior should change.
