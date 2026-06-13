# Geometry Angle Relations Taxonomy Review

Status: failed  
Checked at: 2026-06-13T23:57:27+00:00

## Summary

The scene has three public tasks. Two single-query tasks are taxonomy-aligned, but `task_geometry__angle_relations__algebraic_angle_value` currently exposes a construction variant as public `query_id`, so the scene should not be marked taxonomy-passed yet.

## Task Findings

| Task | Query ids | Answer schema | Annotation schema | Taxonomy status |
| --- | --- | --- | --- | --- |
| `task_geometry__angle_relations__algebraic_angle_value` | `triangle_single_extension_expression`, `triangle_double_extension_expression` | `integer_value` | `keyed_point_map`: `ABC`, `BAC`, `BCD` | Fails: query ids are not user-facing semantic branches. |
| `task_geometry__angle_relations__parallel_supplement_angle` | `parallel_supplement_angle` | `integer_value` | `keyed_point_map`: `CFE`, `AEF` | Passes. |
| `task_geometry__angle_relations__triangle_exterior_angle` | `triangle_exterior_angle` | `integer_value` | `keyed_point_map`: `ABC`, `BAC`, `BCD` | Passes. |

## Blocking Issue

`algebraic_angle_value` uses `triangle_single_extension_expression` and `triangle_double_extension_expression` as public `query_id` values. In the current prompt bundle both branches ask the same question: what is the measure of angle `"ABC"`? They also share the same answer schema and the same annotation role keys.

Under `docs/SCENE_PACKAGE_MIGRATION/TAXONOMY_REVIEW_CHECKLIST.md`, this is not a valid public query boundary because the prompt operation does not change. The branch is currently a generated construction/layout case, not a user-facing semantic query.

## Recommended Fix

Collapse the algebraic task to one semantic query id, such as `algebraic_triangle_extension_expression`, and record the construction case as trace metadata, for example `extension_case=single|double`. Keep both case families in sampling if they are useful visually. Update task docs, prompt assets, generated review artifacts, and this taxonomy status after the fix.

If reviewers decide single-extension and double-extension diagrams are genuinely different reasoning programs, split them into separate public tasks instead. Based on current prompt, answer, and annotation contracts, collapsing to one query id is the safer taxonomy fix.
