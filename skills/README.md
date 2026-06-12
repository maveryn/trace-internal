# TRACE Skills

Repo-local skills are operational overlays for Codex agents. They should point
agents to the current source-of-truth docs; they are not a second copy of the
task registry, taxonomy, or domain contracts.

## Uniform Domain Skill Layout

Every active domain in `trace.core.taxonomy.ACTIVE_DOMAINS` must have exactly
one domain skill:

- Path: `skills/domain-<domain>/SKILL.md`
- Front matter: `name` and `description`
- Heading: `# <Domain> Domain`
- Required sections:
  - `## Read first`
  - `## Active-contract reminders`
  - `## Practical review checklist`

Every domain skill should link to:

- the active domain setup doc in `docs/domains/`
- `docs/ACTIVE_TASK_INVENTORY.md`
- `docs/workflows/TASK_AUTHORING.md`
- `docs/workflows/SHARED_UTILITIES.md`

Domain skills may add narrow sections such as `## Boundary reminders`,
`## Helper placement`, or `## Coverage reference`, but the required sections
above should remain present and recognizable.

`skills/domain-audit/` is a workflow skill, not a domain skill, even though its
directory name starts with `domain-`.

## Update Discipline

When active domains, setup docs, or domain boundaries change:

1. Update `trace/core/taxonomy.py`.
2. Update the relevant source-of-truth docs under `docs/`.
3. Update or add the matching `skills/domain-<domain>/SKILL.md`.
4. Run `PYTHONPATH=. python scripts/check_skill_consistency.py`.

For repo-wide docs/skills hygiene and anti-drift validation, follow
`docs/workflows/DOCS_AND_SKILLS_MAINTENANCE.md`.

Use `docs/README.md` as the canonical documentation navigation entry point.
