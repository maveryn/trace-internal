# Domain Release-Readiness Reference Snapshot

This dated reference snapshot preserves issue-focused domain release-readiness
reports for the Trace task surface reviewed on 2026-07-06.

Solve-rate status was intentionally ignored for this pass.

| Domain | Scenes | Tasks | Decision | Issues | Blocker | Fix before calibration | Release cleanup | Follow-up |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| [`charts`](charts/charts_finalization_review.md) | 42 | 180 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`games`](games/games_finalization_review.md) | 52 | 170 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`geometry`](geometry/geometry_finalization_review.md) | 40 | 170 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`graph`](graph/graph_finalization_review.md) | 10 | 60 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`icons`](icons/icons_finalization_review.md) | 17 | 50 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`illustrations`](illustrations/illustrations_finalization_review.md) | 12 | 60 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`pages`](pages/pages_finalization_review.md) | 25 | 80 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`physics`](physics/physics_finalization_review.md) | 36 | 50 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`puzzles`](puzzles/puzzles_finalization_review.md) | 20 | 60 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`symbolic`](symbolic/symbolic_finalization_review.md) | 15 | 60 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |
| [`three_d`](three_d/three_d_finalization_review.md) | 8 | 60 | `accepted_for_training` | 0 | 0 | 0 | 0 | 0 |

## Validation Commands

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py --check
PYTHONPATH=. python scripts/check_active_inventory_integrity.py
PYTHONPATH=. python scripts/audit_active_domain_surfaces.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_docs_consistency.py tests/test_task_docs_query_id_policy.py tests/test_public_annotation_type_names.py
git diff --check -- docs/review/domain-release-readiness/reference/2026-07-06
```
