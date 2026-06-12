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
- Current serving/runbook details live in `review/docs/CALIBRATION_GUIDE.md`.

## Core engineering rules
- Use public taxonomy consistently: `domain -> scene_id -> task_id`; `scene_id` remains a module/config grouping layer.
- Task ids use taxonomy-v0 public form `task_<domain>__<scene_id>__<objective_contract>` (lowercase snake_case inside each segment). Active/default public tasks must use that public id form. The source layout `trace/tasks/<domain>/<scene_id>/<task_name>.py` is implementation routing only, not a task-id format; cell-board puzzle implementations live under `trace/tasks/puzzles/cell_board/`.
- Keep `scene_id` broad by reasoning style; for geometry value-style tasks use `scene_id=measurement` and keep intra-task query branches in `query_id`.
- Sampling policy is task-level globally (equal task weights by default); domain/scene_id probabilities are derived by aggregation, and query sampling happens inside each task (uniform by default unless task-config override).
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
- Follow `docs/workflows/SHARED_UTILITIES.md` strictly when deciding helper placement and reuse.
- Before introducing or moving helpers, review `docs/workflows/CODE_REVIEW_GUIDELINES.md` for prior placement mistakes (for example task-named modules containing non-task-specific helpers).
- Keep helper placement at the narrowest reusable layer that fits; use the workflow docs/skills for the detailed placement checklist.

## Documentation discipline
- After any change to architecture, module boundaries, shared utilities, or helper placement, update the relevant docs above in the same change.
