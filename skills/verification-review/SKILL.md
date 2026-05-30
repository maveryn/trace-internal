---
name: verification-review
description: Use when validating TRACE changes with tests, task reviews, and answer-distribution checks, or when debugging review failures and support skew.
---

# Verification Review

Use this after task or infrastructure changes, especially when answer support or prompts changed.

## Read first
1. `docs/workflows/BUILD_VALIDATION.md`
2. `docs/workflows/VALIDATION_ERROR_CODES.md`
3. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
4. `docs/workflows/TASK_REVIEW_WEB_APP.md`
5. `review/task-reviews/README.md`

## Standard workflow
1. Run focused pytest coverage for the changed area first.
2. Run broader integration checks if shared infrastructure moved.
3. For new or distribution-changing tasks, run:
   - `PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews`
4. If review artifacts changed, click **Reload Index** in the browser review
   app or call `POST /api/reload`. If app templates, CSS/JS, routes, indexer,
   resource indexing, feedback storage, or schema code changed, restart the app.
   Then inspect the affected
   domain/scene/task/query samples there and verify the page reflects the
   updated local files. Use app feedback for sample-specific prompt, evidence,
   rendering, answer, or calibration issues.
5. Review per-variant metrics:
   - `unique_answers`
   - `max_answer_frequency`
   - numeric summary fields when relevant
6. If distribution fails, debug support skew before adding more rejection loops.
   - Prefer target-first or constructive samplers.
   - Validate fallback deterministic selectors against the actual review seed stream.

## Acceptance checks
- Tests pass.
- Task reviews pass per variant, regenerated samples are inspectable in the
  browser app, manual audit gates are checked only after prompt/image/evidence/
  distribution are acceptable, and completion requires accepted solve-rate.
- Prompt examples and emitted evidence remain contract-valid.
- Determinism still holds for fixed seeds.

## Handoff
If you are reviewing a patch rather than authoring it, also use `skills/code-review/SKILL.md`.
