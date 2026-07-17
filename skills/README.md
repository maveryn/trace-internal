# Trace Skills

Repo-local skills are workflow overlays for Codex agents. They route the agent
to the right source-of-truth docs, enforce a short execution sequence, and
define handoff expectations. They are not a second copy of domain policy,
taxonomy rules, task inventories, or historical workflow docs.

Use `docs/README.md` as the canonical documentation navigation entry point.
Documentation placement rules live in `docs/workflows/DOC_STRUCTURE.md`.
Non-normative future-version proposals live in `docs/future/` and must not be
treated as active workflow or contract instructions.

## Retained Workflow Skills
- `code-review` — review stance, changed-surface checks, and handoff shape.
- `prompt-design` — prompt bundle and prompt-facing contract workflow.
- `task-design` — task contract design before code.
- `task-implementation` — implementation/refactor workflow after the contract
  is known.
- `task-unit-audit` — task/query/program-schema boundary review.
- `verification-review` — tests, task-review artifacts, calibration, and
  reviewer-issue repair workflow.

## Skill Rules
1. A skill must change what the agent does in the current turn.
2. A skill may route to docs, list ordered actions, define stop conditions, and
   define handoff fields.
3. A skill must not duplicate domain policy, enumerate active tasks, or restate
   detailed taxonomy/source-layout rules.
4. Domain-specific policy belongs in `docs/domains/<domain>.md`; workflow
   skills should tell the agent to read that file when domain behavior matters.
5. Do not add domain-specific skill mirrors. If a domain needs new policy,
   update `docs/domains/<domain>.md`.

## Update Discipline
When workflow behavior changes:

1. Update the relevant source-of-truth docs under `docs/`.
2. Update only the workflow skill whose routing or action sequence changed.
3. Run `PYTHONPATH=. python scripts/check_skill_consistency.py`.

For repo-wide docs/skills hygiene and anti-drift validation, follow
`docs/workflows/DOCS_AND_SKILLS_MAINTENANCE.md`.
