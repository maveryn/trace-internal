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
- Domain/task-group defaults (generation/rendering/visual): `configs/domains/<domain>/base.yaml` and `configs/domains/<domain>/<task_group>.yaml`
- Repo-local execution skills: `skills/` (workflow overlays; docs remain source of truth)

## Scope and boundaries
- Work in this repository unless the user explicitly asks otherwise.
- Prefer additive, reusable infrastructure over one-off task code.
- If behavior/contracts change, update the relevant source-of-truth docs above.
- Use the repo-local skills under `skills/` for workflow-specific guidance; keep `AGENTS.md` focused on repo-wide invariants.

## Core engineering rules
- Use taxonomy consistently: `domain -> task_group -> task`.
- Task ids must follow `task_<domain>_<task_group>_<task_name>` (lowercase snake_case). Default task module layout is `trace/tasks/<domain>/<task_group>/<task_name>.py`; tile is the explicit flat-layout exception and uses `trace/tasks/tile/<task_group>_<task_name>.py`.
- Keep `task_group` broad by reasoning style; for geometry value-style tasks use `task_group=measurement` and keep intra-task variants in `task_variant`.
- Sampling policy is task-level globally (equal task weights by default); domain/task_group probabilities are derived by aggregation, and task-variant sampling happens inside each task (uniform by default unless task-config override).
- Domain/task-group defaults (generation/rendering/visual variation) should follow precedence `domain -> task_group -> task/params`: shared domain defaults under `configs/domains/<domain>/base.yaml`, group overrides under `configs/domains/<domain>/<task_group>.yaml`, then optional task-level overrides.
- Do not hardcode user-facing prompt text in task modules; prompts must come from external template assets.
- Prompt composition must be reusable: one task-family layer and one task layer (plus optional task-variant layer), each with deterministic variant selection.
- Keep prompt templates versioned and recorded in trace metadata (`prompt_bundle_id`, keys, variant indices).
- Keep generation factorized into explicit specs (`SceneSpec`, `QuerySpec`, `RenderSpec`, `PromptSpec`, `VerifierSpec`, `SamplerSpec`, `InstanceRecordSpec`).
- Generators must be deterministic given seeds/specs/versions.
- No hidden randomness: all random sources must be explicit and recorded.
- Verifiers must rely on metadata contracts and projections, not pixels as source of truth.
- Answers and evidence must come from the same execution trace.
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
