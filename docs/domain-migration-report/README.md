# Domain Migration Reports

This folder stores post-migration domain audit reports.

Use it for read-only domain consistency sweeps after a domain's migrated tasks
have passed human review in the browser app. The final domain report should be
issue-only: list the domain, scene, task, or query issues found by automated
checks or manual review, and omit tasks/scenes that passed.

Do not make source code, config, prompt, task-doc, review-artifact, or review
status changes during the report-only audit. If the audit finds a required
fix, record it here and handle the fix in a separate user-approved task.

Suggested path:

```text
docs/domain-migration-report/<domain>/<domain>_post_migration_checklist.md
```

Supporting audit outputs can live beside the report, for example:

```text
docs/domain-migration-report/<domain>/bbox_min_side_audit.md
docs/domain-migration-report/<domain>/semantic_sampling_modulo_audit.md
docs/domain-migration-report/<domain>/visual_candidate_modulo_audit.md
docs/domain-migration-report/<domain>/prompt_concision_audit.md
docs/domain-migration-report/<domain>/prompt_annotation_contracts/
```

If no issues are found, the report should contain only a short no-issues
statement, not a long pass summary.

## Prompt Issue Labels

Use `Prompt decorative-renderer trivia` for prompts whose opening scene
sentence lists style or renderer implementation details that are not needed to
answer the question. Example anti-pattern:

> The image shows a zebra-striped table with one Name column, several data
> columns, alternating row shading, and a shaded header row.

Unless the question asks about those visual properties, report this as an
issue and rewrite toward the semantic surface, for example: "The image shows a
table of named rows and data columns." Do not mention zebra striping, shaded
headers, background treatments, fonts, palettes, borders, rounded corners,
paper texture, or similar visual details unless they are answer-bearing cues.
