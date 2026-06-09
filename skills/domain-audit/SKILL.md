---
name: domain-audit
description: Use when doing repo-wide TRACE sanitation or domain-by-domain audit passes, especially to review active tasks for contract drift, visual clarity, annotation quality, stale docs/configs/tests, and review-artifact freshness.
---

# Domain Audit

Use this for broad cleanup passes that review one active domain at a time.

## Read first
1. `docs/workflows/DOMAIN_AUDIT_REVIEW.md`
2. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
3. `docs/workflows/BUILD_VALIDATION.md`
4. `docs/workflows/TASK_REVIEW_WEB_APP.md`
5. `docs/workflows/DOCS_AND_SKILLS_MAINTENANCE.md`
6. The relevant domain setup doc in `docs/domains/`
7. The relevant domain skill in `skills/domain-<domain>/`

## Workflow
1. Inventory the active tasks and shared helpers for the target domain.
2. Audit each task for contract, prompt, annotation, visual, and review-artifact drift.
3. Fix safe issues immediately and keep changes domain-scoped unless the fix is truly shared.
4. Re-run focused validation and full task review for every touched task.
5. Reload the browser review app index after regenerated review artifacts, or
   restart the app after app-code changes, then inspect regenerated samples
   there.
6. Use existing task/sample feedback threads for reviewer issues. After fixing
   feedback, add an agent repair note with the validation/review run and leave
   resolution to human review unless explicitly instructed otherwise.
7. If a reusable issue is discovered, add one distilled rule to `docs/workflows/CODE_REVIEW_GUIDELINES.md`.

## Handoff
Report findings under:
- `Fixed`
- `Deferred`
- `Rules added`
- `Validation`
