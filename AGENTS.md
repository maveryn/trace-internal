# TRACE AGENTS

## Project goal
TRACE is a grounded visual reasoning task environment for RLVR.
Each generated instance should include:
- prompt
- typed answer
- image(s)
- metadata-grounded verifier payload

## Source-of-truth docs
- Docs index and reading order: `docs/README.md`
- Use `docs/README.md` as the canonical navigation entry point for core, workflow, domain, project, and task docs.
- Python dependencies: `requirements.txt`
- Domain/scene defaults (generation/rendering/visual): `configs/domains/<domain>/base.yaml` and `configs/domains/<domain>/<scene_id>.yaml`
- Repo-local execution skills: `skills/` (workflow overlays; docs remain source of truth)

## Scope and boundaries
- Work in this repository unless the user explicitly asks otherwise.
- Prefer additive, reusable infrastructure over one-off task code.
- If behavior/contracts change, update the relevant source-of-truth docs above.
- Use the repo-local skills under `skills/` for workflow-specific guidance; keep `AGENTS.md` focused on repo-wide invariants.

## Review app workflow
- Generated task-review artifacts belong under `review/task-reviews/<domain>/<scene_id>/<task_id>/`; do not use stale review roots.
- The browser review app is the default manual inspection surface. Reload its index after generated artifact changes, and restart it after app, template, CSS/JS, indexer, resource, feedback, or schema changes.
- Reviewer-facing comments are **issues** and browser issue pages use `/issues`. Internal APIs, SQLite paths, and code identifiers still use `feedback`; legacy `/feedback` browser paths are compatibility redirects/aliases. Do not rename those internals without an explicit migration.
- Reviewer issues stay open until a human verifies the updated task/sample. When an agent fixes an issue, add a brief repair note to the relevant issue item describing what changed and whether artifacts were regenerated or the app was refreshed; do not mark the issue resolved unless explicitly instructed.
- Task completion requires both browser-app manual audit passing and accepted current solve-rate artifacts.

## Local vLLM serving
- This machine has one calibration GPU. The shared qwen25 vLLM endpoint is `http://127.0.0.1:8002/v1` serving `Qwen/Qwen2.5-VL-7B-Instruct`.
- Do not start additional vLLM servers on other local ports for calibration. Use the calibration runner's server-pool lock at `logs/vllm/locks/qwen25vl7b_8002.lock`; if another agent holds it, wait for the lock instead of bypassing it.
- Current serving/runbook details live in `docs/workflows/CALIBRATION_GUIDE.md`.

## Core engineering rules
- Use public taxonomy consistently: `domain -> scene_id -> task_id`; `scene_id` is the visible rendering grammar, not a source-routing or config grouping layer.
- Task ids use taxonomy-v0 public form `task_<domain>__<scene_id>__<objective_contract>` (lowercase snake_case inside each segment). Active/default public tasks must use that public id form. The target scene-package source layout is `trace/tasks/<domain>/<scene_id>/<objective_contract>.py`; transitional source routing is implementation metadata only, not a task-id format.
- Keep intra-task mirrors and branch diagnostics in `query_id`; query ids are internal replay/review metadata, not public taxonomy nodes or sampling units.
- Sampling policy is task-level globally (equal task weights by default); domain/scene_id probabilities are derived by aggregation, and query sampling happens inside each task. Query ids are uniform by default, and review-candidate migrated scenes must not use config-level query weights unless a later global policy explicitly allows them.
- Domain/scene defaults (generation/rendering/visual variation) should follow precedence `domain -> scene_id -> task/params`: shared domain defaults under `configs/domains/<domain>/base.yaml`, group overrides under `configs/domains/<domain>/<scene_id>.yaml`, then optional task-level overrides.
- Do not hardcode user-facing prompt text in task modules; prompts must come from external template assets.
- Prompt composition must be reusable: one scene layer and one task layer (plus optional query layer), each with deterministic template selection.
- Keep prompt templates versioned and recorded in trace metadata (`prompt_bundle_id`, keys, variant indices).
- Keep generation factorized into explicit specs (`SceneSpec`, `QuerySpec`, `RenderSpec`, `PromptSpec`, `VerifierSpec`, `SamplerSpec`, `InstanceRecordSpec`).
- Generators must be deterministic given seeds/specs/versions.
- No hidden randomness: all random sources must be explicit and recorded.
- Verifiers must rely on metadata contracts and projections, not pixels as source of truth.
- Answers and annotation must come from the same execution trace.
- Task instances must have unique final answers by construction.
- Never auto-relax semantic constraints to force acceptance.
- Sidecar trace export is mandatory; each `TrainInstance` must include `trace_ref`.

## Reuse and code organization
- Before adding new logic, search for reusable helpers and extend shared modules when possible.
- Do not duplicate utilities across tasks/domains unless there is a strong reason.
- Keep helper placement at the narrowest reusable layer that fits: `trace/core`,
  `trace/tasks/shared`, `trace/tasks/<domain>/shared`, scene-local `shared/`,
  then task-local code.
- For scene-package migration work, follow
  `docs/SCENE_PACKAGE_MIGRATION/README.md` and
  `docs/SCENE_PACKAGE_MIGRATION/SCENE_MIGRATION_GUIDE.md`; domain-specific
  shared-boundary docs under `docs/SCENE_PACKAGE_MIGRATION/` apply when present.
- Before introducing or moving helpers, review
  `docs/workflows/CODE_REVIEW_GUIDELINES.md` for current source-boundary and
  migration red flags.

## Documentation discipline
- After any change to architecture, module boundaries, shared utilities, or helper placement, update the relevant docs above in the same change.
