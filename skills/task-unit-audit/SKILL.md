---
name: task-unit-audit
description: Use when auditing TRACE task boundaries, query ids, program schemas, answer schemas, or annotation schemas against the current task-unit contract.
---

# Task-Unit Audit

Use this when reviewing whether a task contract, query branch, split, merge, or
rename follows the current TRACE taxonomy rules.

## Read first
1. `docs/contracts/TAXONOMY.md`
2. `docs/contracts/TASK_UNIT_POLICY.md`
3. `docs/contracts/PROGRAM_SCHEMA_CATALOG.md`
4. `docs/SCENE_PACKAGE_MIGRATION/TAXONOMY_REVIEW_CHECKLIST.md` for scene-package work
5. The relevant domain contract in `docs/domains/`

## Workflow
1. Identify the stable public contract: `domain`, `scene_id`, `task_id`,
   answer schema, annotation schema, prompt scaffold, and program schema.
2. Check each `query_id` branch. Keep it internal only when it is a narrow
   semantic branch of the same program, prompt meaning, answer schema, and
   annotation schema.
3. Split when a branch changes the core program, output schema, annotation
   schema, prompt scaffold, or rendered scene grammar.
4. Merge only when two public tasks have the same scene grammar, answer schema,
   annotation schema, prompt scaffold, and concrete program schema.
5. Verify program code is concrete and uses existing catalog vocabulary before
   adding a new schema.

## Stop conditions
- Do not implement split/merge/rename changes inside the audit unless the user
  explicitly asks for implementation.
- If the audit changes domain-level policy, update `docs/domains/<domain>.md`
  rather than adding skill-only rules.

## Handoff
Report audited items with:

- `Decision`: keep, split, merge, rename, or retire.
- `Contract reason`: which schema/program/query rule controls the decision.
- `Program schema`: concrete schema and argument axes.
- `Annotation fit`: whether witness roles are stable and minimally grounded.
- `Docs/code follow-up`: files that must change together.
