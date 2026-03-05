# TRACE Lessons Learned

Compact history of recurring pitfalls and the reusable fix for each.

## Core lessons
1. **Helper placement drift**  
   Keep helper scope aligned with reuse reality. Start narrow; promote only when a second consumer appears.

2. **Wrapper/module surface sprawl**  
   Remove pass-through wrappers, shim modules, and dead re-exports once migration completes.

3. **Speculative shared APIs**  
   Do not keep speculative helpers or exports with zero consumers.

4. **Task contract bloat**  
   Keep `TaskOutput`/trace fields minimal and owned by the correct layer.

5. **Normalization duplication**  
   Shared config/style normalization should exist once and be reused by higher layers.

6. **Prompt consistency issues**  
   Keep prompts externalized, render deterministically, and always emit complete prompt metadata.

7. **Distribution bias regressions**  
   For multi-query value tasks, use feasible-answer-aware sampling and verify per-query distributions.

8. **Geometry ambiguity**  
   If overlap/touch is disallowed, enforce minimum-clearance checks in generation and tests.

9. **Determinism regressions**  
   Avoid unordered iteration in emitted payloads; canonicalize ordering at emit time.

10. **Leaky public helper APIs**  
   If a helper/type has no external consumers, keep it private to reduce API surface and maintenance burden.

11. **Shared type alias drift**  
   Reuse canonical shared aliases (for example `Point`) instead of duplicating equivalent local type aliases across modules.

## Maintenance rule
When a new cross-task issue is found:
1. Add one short lesson here.
2. Add one review rule in `docs/CODE_REVIEW_GUIDELINES.md`.
3. Add or adjust authoring guidance in `docs/TASK_AUTHORING.md` when behavior changes.
