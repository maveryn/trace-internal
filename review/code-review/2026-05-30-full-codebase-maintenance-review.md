# Full Codebase Maintenance Review

Date: 2026-05-30

Scope: TRACE repository maintenance review excluding `rlvr/`. The audit focused on repo-owned code and docs under `trace/`, `scripts/`, `tests/`, `docs/`, `skills/`, `configs/`, `prompts/`, `assets/`, `eval/`, `review/`, and root project metadata. Generated outputs, benchmark/external bundles, logs, run outputs, checkpoints, and `rlvr/` were not reviewed.

## Validation Performed

- `PYTHONPATH=. python scripts/check_skill_consistency.py`: passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_docs_consistency.py`: passed.
- `python -m py_compile ...` over `scripts/` and `trace/` Python files excluding generated/external/run folders: passed.
- `PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache`: passed.
- `git diff --check -- trace scripts docs configs prompts tests skills assets eval review AGENTS.md README.md pyproject.toml`: passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_graph_edge_source_common_sampling.py tests/test_graph_counting_source_sink_count_tasks.py tests/test_graph_counting_source_sink_count_contracts.py tests/test_graph_relation_common_neighbor_count_tasks.py tests/test_graph_relation_common_neighbor_count_contracts.py`: passed, 17 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_graph_degree_sampling.py tests/test_graph_sample_types.py tests/test_graph_feasibility.py tests/test_graph_counting_degree_count_tasks.py tests/test_graph_counting_degree_count_contracts.py`: passed, 18 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_graph_label_color_profile_sampling.py tests/test_graph_counting_node_color_count_tasks.py tests/test_graph_counting_edge_color_count_tasks.py tests/test_graph_counting_edge_text_label_count_tasks.py tests/test_graph_counting_cross_color_edge_count_tasks.py tests/test_graph_relation_edge_attribute_label_tasks.py tests/test_graph_relation_unique_node_label_tasks.py`: passed, 31 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_graph_*.py`: passed, 224 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_three_d_object_scene_rendering.py tests/test_three_d_spatial_camera_distance.py tests/test_three_d_street_intersection_nearest.py tests/test_three_d_street_lane_ahead_object.py tests/test_three_d_street_same_road_arm_reference.py tests/test_three_d_street_intersection_rendering.py tests/test_three_d_camera_projection.py`: passed, 22 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_three_d_*.py`: passed, 83 tests.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m py_compile trace/tasks/charts/map/choropleth_region_label.py trace/tasks/charts/map/choropleth_geometry.py trace/tasks/charts/map/choropleth_geography.py tests/test_charts_choropleth_shared_helpers.py`: passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_charts_choropleth_shared_helpers.py tests/test_charts_map_tasks.py`: passed, 19 tests.
- `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_three_d_street_intersection_rendering.py tests/test_three_d_street_intersection_nearest.py tests/test_three_d_street_lane_ahead_object.py tests/test_three_d_street_same_road_arm_reference.py`: passed, 14 tests.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m py_compile trace/tasks/graph/shared/graph_sampling.py trace/tasks/graph/shared/graph_*sampling.py trace/tasks/graph/shared/graph_topology_helpers.py`: passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_graph_*.py`: passed, 224 tests.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m py_compile trace/tasks/charts/shared/chart_scene.py trace/tasks/charts/shared/chart_scene_*.py trace/tasks/charts/map/choropleth_*.py trace/tasks/charts/map/choropleth_region_label.py`: passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_chart_scene_primitives.py tests/test_chart_scene_types.py tests/test_charts_distribution_tasks.py tests/test_charts_multiseries_tasks.py tests/test_charts_statistics_tasks.py tests/test_charts_trend_tasks.py tests/test_charts_counting_tasks.py`: passed, 96 tests.
- `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_three_d_object_scene_rendering.py tests/test_three_d_*.py`: passed, 85 tests.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m py_compile trace/tasks/three_d/street/intersection_rendering_common.py trace/tasks/three_d/street/intersection_rendering.py trace/tasks/three_d/street/intersection_*_rendering.py`: passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_three_d_street_intersection_rendering.py tests/test_three_d_street_intersection_nearest.py tests/test_three_d_street_lane_ahead_object.py tests/test_three_d_street_same_road_arm_reference.py`: passed, 14 tests.
- `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_three_d_*.py`: passed, 83 tests.

## Findings Summary

| ID | Severity | Status | Area | Finding |
| --- | --- | --- | --- | --- |
| CR-001 | High | Triaged | Repo hygiene | The working tree has a very large amount of source-like dirty state that should be resolved before release, merge, or authoritative review. |
| CR-002 | High | Resolved | Benchmark scripts | Vero/benchmark coverage scripts reference inactive public task ids, so coverage mapping can silently under-report or misroute gaps. |
| CR-003 | Medium | Resolved | Skills/docs | Icon complexity guidance references removed icon task ids. |
| CR-004 | Medium | Resolved | Docs | `CODE_REVIEW_GUIDELINES.md` has duplicate rule numbers in the same distilled-list sequence. |
| CR-005 | Medium | Resolved | Packaging | `pyproject.toml` declares no dependencies while `requirements.txt` contains the actual runtime/test dependency set. |
| CR-006 | Medium | Resolved | Maintainability | Shared/facade monolithic hotspots were split into narrower ownership modules. |
| CR-007 | Low | Resolved | Skills/docs | Chart skill repeats one read-first doc and carries detailed policy that should stay canonical in workflow/domain docs. |
| CR-008 | Low | Resolved | Duplication | Coordinate geometry tasks duplicate small default-parameter resolver helpers. |

## Detailed Findings

### CR-001: Dirty source tree needs triage before authoritative review

Severity: High

Status: Triaged. Cache directories, notebook checkpoint directories, and Python bytecode under active source/review roots were removed. A file-level dirty-tree manifest was created at `review/code-review/2026-05-30-dirty-tree-triage.md` and `review/code-review/2026-05-30-dirty-tree-triage.json`, with a cleanup action list at `review/code-review/2026-05-30-cr001-cleanup-action-list.md`. Deleted tracked files were reviewed as retired/inactive surfaces to keep deleted, including the deleted illustration code/test paths after checking for active import references. Untracked source-like files were reviewed as active additions to keep/stage. The remaining tracked-modified set still needs commit splitting rather than blind reversion.

Evidence:
- `git status --short` over reviewed source roots reported approximately 1033 modified files, 52 deleted files, and 134 untracked files.
- Source-like untracked examples include `docs/workflows/TASK_REVIEW_WEB_APP.md`, `trace/review_app/`, `scripts/run_review_app.py`, and `tests/test_review_app.py`.

Impact:
- It is hard to distinguish intentional source changes from generated artifacts or stale leftovers.
- Code review, release readiness, and calibration provenance become unreliable while source files are untracked or mixed with unrelated edits.

Recommendation:
- Split the workspace into intentional change sets.
- Stage or explicitly discard every source-like file before treating this branch as reviewable.
- Keep generated review output under `review/task-reviews/` and persistent review/audit notes under `review/docs/` or `review/code-review/`.

Validation target:
- `git status --short -- trace scripts docs configs prompts tests skills assets eval review AGENTS.md README.md pyproject.toml` should be clean or contain only the intended patch.

### CR-002: Benchmark coverage scripts reference inactive task ids

Severity: High

Status: Resolved. Benchmark/coverage scripts now reference active task ids, and `tests/test_docs_consistency.py` scans those scripts for inactive task ids.

Evidence:
- `scripts/analyze_vero_benchmark_failures.py:306` references `task_pages__control_board__filter_count`.
- `scripts/analyze_vero_benchmark_failures.py:323` references `task_physics__resistor__total_resistance_value`.
- `scripts/analyze_vero_benchmark_failures.py:355` references `task_games__crossing__safe_route_label`.
- `scripts/review_vero_coverage.py:328` references `task_pages__infographic__column_profile_comparison_value`.
- `scripts/review_vero_coverage.py:329` and `scripts/review_vero_round2_expansion.py:572` reference `task_pages__infographic__section_ranked_total_label`.

Impact:
- These scripts use stale task-id strings as coverage candidates.
- If the helper filters unknown ids, the intended coverage links disappear silently.
- Benchmark gap notes can mislead future domain expansion and task-prioritization work.

Recommendation:
- Replace hard-coded task-id lists with registry-derived lookups where possible.
- Where benchmark notes intentionally mention retired tasks, mark them as retired and include the replacement active task ids.
- Add a lightweight test that scans benchmark/coverage scripts for `task_*__*__*` strings and verifies each id is active or explicitly listed as retired.

Validation target:
- A registry consistency check should report zero unannotated inactive task ids in benchmark review scripts.

### CR-003: Icon complexity skill references removed task ids

Severity: Medium

Status: Resolved. The icon complexity reference now uses active icon task ids, and `scripts/check_skill_consistency.py` scans skill Markdown for inactive task-id references.

Evidence:
- `skills/task-complexity/references/icons.md:35-36` references removed reference-canvas tasks.
- `skills/task-complexity/references/icons.md:48` repeats one removed reference-canvas task id.
- `skills/task-complexity/references/icons.md:95-96` references removed pair-grid tasks.
- `skills/task-complexity/references/icons.md:133-134` references removed pattern-grid tasks.

Impact:
- Agents using the complexity skill can calibrate against non-active task families.
- Domain audit and difficulty guidance can drift from the active task inventory.

Recommendation:
- Update this skill reference to active icon task ids, or convert removed ids into historical examples with explicit replacement mappings.
- Add the same active-id scan used for docs to repo-local skills.

Validation target:
- Skill/document task-id scan reports zero unannotated missing ids.

### CR-004: Code review guideline rule numbering has duplicates

Severity: Medium

Status: Resolved. The distilled findings section was renumbered contiguously, and `tests/test_docs_consistency.py` now rejects duplicate or non-contiguous numbering in that section.

Evidence:
- `docs/workflows/CODE_REVIEW_GUIDELINES.md:43-46` duplicates rule numbers 27 and 28.
- `docs/workflows/CODE_REVIEW_GUIDELINES.md:98-105` duplicates rule numbers 80 through 83.
- `docs/workflows/CODE_REVIEW_GUIDELINES.md:165-168` duplicates rule numbers 143 and 144.
- `docs/workflows/CODE_REVIEW_GUIDELINES.md:215-225` duplicates rule numbers 191 and 198.

Impact:
- Reviewers cannot cite rules unambiguously.
- The file appears append-only and is likely to keep accumulating contradictory or duplicate guidance.

Recommendation:
- Renumber the distilled-list section once, or convert it to unnumbered bullets plus stable anchors for high-value rules.
- Add a doc lint check for duplicate numeric prefixes within the distilled-list section.

Validation target:
- A duplicate-rule-number scan over `docs/workflows/CODE_REVIEW_GUIDELINES.md` reports no duplicates within a single numbered sequence.

### CR-005: Project metadata under-declares dependencies

Severity: Medium

Status: Resolved. Runtime dependencies now live in `pyproject.toml` under `[project].dependencies`, while test and review-app tooling are available through `[project.optional-dependencies]` extras. `README.md` documents editable installs with `pip install -e ".[test,review]"`, and `requirements.txt` remains valid as the all-in-one bootstrap path.

Evidence:
- `pyproject.toml:11` declares `dependencies = []`.
- `requirements.txt:4-27` lists runtime and tooling dependencies such as Pillow, cairosvg, PyYAML, numpy, scipy, pydantic, FastAPI, uvicorn, jinja2, and httpx.

Impact:
- `pip install .` does not install dependencies needed by core generation, rendering, tests, or the review app.
- Environments created from packaging metadata can fail differently from environments created from `requirements.txt`.

Recommendation:
- Either move runtime dependencies into `[project].dependencies` and keep test/review extras separate, or document that TRACE is requirements-file only and should not be installed from package metadata.
- If package installation is supported, add extras such as `test` and `review` for pytest/openpyxl/FastAPI tooling.

Validation target:
- A clean virtual environment installed through the documented path can import core modules and run the doc consistency tests.

### CR-006: Monolithic modules and scripts are maintenance hotspots

Severity: Medium

Status: Resolved for the triaged shared/facade hotspot scope. Task-review routing, workbook rendering, calibration helpers, prompt/evidence auditing, calibration sweep orchestration, graph sampling, chart rendering, choropleth map construction/rendering, object-scene assembly/rendering, street-intersection scene assembly, and street-intersection rendering have all been moved into narrower modules with compatibility facades where existing tasks/tests still import old names. Large domain-specific task modules still exist elsewhere, but those should be handled as new targeted refactor items rather than left attached to this shared-hotspot CR.

Evidence:
- `trace/tasks/graph/shared/graph_sampling.py`: about 142 lines after splitting sampler families into `graph_node_degree_sampling.py` (~848), `graph_path_order_sampling.py` (~793), `graph_reachability_sampling.py` (~557), `graph_component_sampling.py` (~436), `graph_bridge_articulation_sampling.py` (~397), `graph_isolation_sampling.py` (~361), `graph_mst_sampling.py` (~181), and `graph_edge_path_label_sampling.py` (~132).
- `trace/tasks/three_d/shared/object_scene_rendering.py`: about 371 lines after moving named-object glyph rendering into `object_scene_glyphs_*.py` family modules, all currently under about 835 lines.
- `trace/tasks/charts/shared/chart_scene.py`: about 40 lines after splitting renderers into `chart_scene_labeled.py` (~983), `chart_scene_multiseries.py` (~574), `chart_scene_stacked.py` (~469), `chart_scene_histogram.py` (~248), `chart_scene_boxplot.py` (~622), and `chart_scene_violin.py` (~314).
- `trace/tasks/charts/map/choropleth_region_label.py`: about 602 lines after splitting config, dataset construction, rendering, marker rendering, and region/world/marker dataset helpers into map-local modules; the largest new choropleth helper is about 955 lines.
- `trace/tasks/three_d/spatial/camera_distance.py`: about 750 lines after shared camera/projection and object-scene extraction.
- `trace/tasks/three_d/street/intersection_nearest.py`: about 845 lines after shared street scene extraction.
- `trace/tasks/three_d/street/intersection_rendering.py`: about 83 lines after splitting street rendering into common (~261), road (~524), vehicle (~398), fixture/signage (~393), pedestrian (~268), building/storefront (~603), landscape/street furniture (~282), and dispatch (~127) modules.
- `scripts/run_task_review.py`: about 820 lines after task-review helper extraction.

Impact:
- Large modules make ownership boundaries unclear and increase regression risk.
- Shared helpers can become task-specific dumping grounds.
- Script behavior is harder to test at function-level granularity.

Recommendation:
- Split by stable responsibility, not by arbitrary line count. Good candidate seams are sampler/contracts/rendering/projection/review export/app indexing.
- For scripts, move reusable logic into importable modules and keep CLI files as thin argument parsing wrappers.
- Prioritize files that repeatedly receive cross-domain changes or contain shared contracts.

Validation target:
- New shared/helper modules have focused tests and no circular imports; CLI behavior remains covered by existing smoke checks.

### CR-007: Chart skill duplicates docs and one read-first entry

Severity: Low

Status: Resolved. `skills/domain-charts/SKILL.md` no longer repeats the information-scene workflow in the read-first list, and its detailed review/handoff bullets now defer to canonical workflow/domain docs.

Evidence:
- `skills/domain-charts/SKILL.md:19` and `skills/domain-charts/SKILL.md:22` both point to `docs/workflows/INFORMATION_SCENE_RENDERING_UPGRADE.md`.
- `skills/domain-charts/SKILL.md:39-66` copies a detailed practical review checklist and handoff procedure that belongs in canonical workflow/domain docs.

Impact:
- Skill guidance can drift from source-of-truth docs.
- Agents may update one copy while leaving the other stale.

Recommendation:
- Remove the duplicate read-first entry.
- Keep the skill as a thin routing overlay that points to `docs/domains/CHART_TASK_SETUP.md`, `docs/workflows/INFORMATION_SCENE_RENDERING_UPGRADE.md`, and `review/docs/CALIBRATION_GUIDE.md`.

Validation target:
- Skill consistency check passes and chart review policy is stated once in canonical docs.

### CR-008: Coordinate geometry default resolver helper is duplicated

Severity: Low

Status: Resolved. `trace/tasks/geometry/coordinate/params.py` now owns `resolve_int_param(...)`, and the coordinate algebra, locus-region, and quadrilateral task modules import it instead of defining local copies.

Evidence:
- `trace/tasks/geometry/coordinate/algebra.py:211-212` defines `_resolve_int_param`.
- `trace/tasks/geometry/coordinate/locus_region.py:207-208` defines the same helper.
- `trace/tasks/geometry/coordinate/quadrilateral.py:528-529` defines the same helper.

Impact:
- Small duplicated helpers are easy to change inconsistently.
- New coordinate tasks are likely to copy the same pattern again.

Recommendation:
- Promote common parameter/default resolvers into a narrow coordinate-domain shared helper.
- Keep task-local wrappers only when they encode task-specific validation.

Validation target:
- Coordinate tasks import the shared helper and behavior tests still pass for default/config override resolution.
