"""Scene-package migration enforcement tests.

The structural checks are gated by ``MIGRATED_SCENE_PACKAGE_DOMAINS`` so they
can land before any full domain migration is complete.
"""

from __future__ import annotations

import ast
from collections import defaultdict
import inspect
from pathlib import Path
from typing import Any

import pytest

import trace.core.scene_package_migration as scene_package_migration
from trace.core.reward_contracts import resolve_reward_contract
from trace.core.taxonomy import TaxonomyEntry, inject_taxonomy_metadata
from trace.core.scene_package_migration import (
    MIGRATED_SCENE_PACKAGE_DOMAINS,
    MIGRATED_SCENE_PACKAGE_SCENES,
    SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_COMPLETE_SCENES,
    SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_PENDING_SCENES,
    SCENE_PACKAGE_PILOT_TASK_IDS,
    is_scene_package_objective_ownership_complete_scene,
    is_scene_package_migrated_scene,
    parse_public_task_id,
)
from trace.core.types import CurriculumIndex, ImageRecord, TaskComplexity, TraceRef, TrainInstance, TypedValue


REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_MIGRATED_KEYS = (
    "task_group",
    "source_task_group",
    "task_group_sampling_probabilities",
)
SCENE_LOCAL_SHARED_SUFFIXES = (
    "_scene",
    "_common",
    "_rendering",
    "_sampling",
    "_style",
    "_annotation",
)


def _task_registry() -> dict[str, type[Any]]:
    import trace.tasks  # noqa: F401 - populate task registry only when enforcement is active
    from trace.tasks.registry import TASK_REGISTRY

    return TASK_REGISTRY


def _active_migrated_task_entries() -> list[tuple[str, type[Any]]]:
    if not MIGRATED_SCENE_PACKAGE_DOMAINS and not MIGRATED_SCENE_PACKAGE_SCENES:
        return []
    entries: list[tuple[str, type[Any]]] = []
    for task_id, cls in sorted(_task_registry().items()):
        parts = parse_public_task_id(str(task_id))
        if parts.domain in MIGRATED_SCENE_PACKAGE_DOMAINS or is_scene_package_migrated_scene(parts.domain, parts.scene_id):
            entries.append((str(task_id), cls))
    return entries


def _expected_task_path(task_id: str) -> Path:
    parts = parse_public_task_id(str(task_id))
    return (
        REPO_ROOT
        / "trace"
        / "tasks"
        / parts.domain
        / parts.scene_id
        / f"{parts.objective_contract}.py"
    )


def _migrated_domain_scenes(domain: str) -> set[str]:
    scenes: set[str] = set()
    for task_id in _task_registry():
        parts = parse_public_task_id(str(task_id))
        if parts.domain != str(domain):
            continue
        if parts.domain in MIGRATED_SCENE_PACKAGE_DOMAINS or is_scene_package_migrated_scene(parts.domain, parts.scene_id):
            scenes.add(parts.scene_id)
    return scenes


def _import_module_name(node: ast.AST) -> str:
    if isinstance(node, ast.Import):
        return ""
    if isinstance(node, ast.ImportFrom):
        return str(node.module or "")
    return ""


@pytest.mark.parametrize(("task_id", "cls"), _active_migrated_task_entries())
def test_migrated_scene_package_task_source_path_and_class_contract(task_id: str, cls: type[Any]) -> None:
    expected = _expected_task_path(task_id).resolve()
    actual = Path(inspect.getsourcefile(cls) or "").resolve()
    assert actual == expected
    assert not hasattr(cls, "task_group")


def test_migrated_scene_package_modules_define_one_active_task() -> None:
    tasks_by_path: dict[Path, list[str]] = defaultdict(list)
    for task_id, cls in _active_migrated_task_entries():
        source_path = Path(inspect.getsourcefile(cls) or "").resolve()
        tasks_by_path[source_path].append(task_id)

    for source_path, task_ids in sorted(tasks_by_path.items()):
        assert len(task_ids) == 1, f"{source_path} owns multiple active public tasks: {task_ids}"


def test_migrated_scene_package_domain_configs_are_scene_keyed() -> None:
    for domain in sorted(MIGRATED_SCENE_PACKAGE_DOMAINS):
        scenes = _migrated_domain_scenes(str(domain))
        config_dir = REPO_ROOT / "configs" / "domains" / str(domain)
        expected_files = {"base.yaml", *(f"{scene_id}.yaml" for scene_id in scenes)}
        actual_files = {path.name for path in config_dir.glob("*.yaml")}

        assert config_dir.exists()
        assert expected_files.issubset(actual_files)
        assert actual_files == expected_files


def test_migrated_scene_package_scene_configs_exist() -> None:
    for domain, scenes in sorted(MIGRATED_SCENE_PACKAGE_SCENES.items()):
        config_dir = REPO_ROOT / "configs" / "domains" / str(domain)
        assert config_dir.exists()
        for scene_id in sorted(scenes):
            assert (config_dir / f"{scene_id}.yaml").exists()


def test_migrated_scene_package_domain_shared_has_no_scene_local_modules() -> None:
    for domain in sorted(MIGRATED_SCENE_PACKAGE_DOMAINS):
        scenes = _migrated_domain_scenes(str(domain))
        shared_dir = REPO_ROOT / "trace" / "tasks" / str(domain) / "shared"
        if not shared_dir.exists():
            continue

        for path in shared_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            stem = path.stem
            for scene_id in scenes:
                assert not stem.startswith(f"{scene_id}_"), f"{path} is scene-local and belongs under {scene_id}/shared"
                assert not any(
                    f"{scene_id}{suffix}" in stem for suffix in SCENE_LOCAL_SHARED_SUFFIXES
                ), f"{path} is scene-local and belongs under {scene_id}/shared"


def test_migrated_scene_package_tasks_do_not_import_retired_task_group_paths() -> None:
    for task_id, cls in _active_migrated_task_entries():
        parts = parse_public_task_id(task_id)
        source_path = Path(inspect.getsourcefile(cls) or "")
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        active_scenes = _migrated_domain_scenes(parts.domain)

        for node in ast.walk(tree):
            module_name = _import_module_name(node)
            if not module_name.startswith(f"trace.tasks.{parts.domain}."):
                continue
            route = module_name.removeprefix(f"trace.tasks.{parts.domain}.").split(".", 1)[0]
            assert route in active_scenes or route == "shared", f"{task_id} imports retired task-group path {module_name}"
            assert route in {parts.scene_id, "shared"}, f"{task_id} imports sibling scene path {module_name}"


def test_three_d_is_not_allowlisted_before_full_scene_package_migration() -> None:
    assert "three_d" not in MIGRATED_SCENE_PACKAGE_DOMAINS


def test_games_is_structurally_routed_but_objective_ownership_pending() -> None:
    assert "games" not in MIGRATED_SCENE_PACKAGE_DOMAINS
    assert "games" in MIGRATED_SCENE_PACKAGE_SCENES
    pending = SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_PENDING_SCENES.get("games", frozenset())
    assert pending == MIGRATED_SCENE_PACKAGE_SCENES["games"]
    assert "2048" in pending
    assert not is_scene_package_objective_ownership_complete_scene("games", "2048")


def test_objective_ownership_complete_registry_starts_empty() -> None:
    assert SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_COMPLETE_SCENES == {}


def test_objective_ownership_pending_scenes_are_structurally_routed() -> None:
    pilot_scenes = {
        (parts.domain, parts.scene_id)
        for task_id in SCENE_PACKAGE_PILOT_TASK_IDS
        for parts in (parse_public_task_id(task_id),)
    }
    for domain, scenes in sorted(SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_PENDING_SCENES.items()):
        for scene_id in sorted(scenes):
            assert is_scene_package_migrated_scene(domain, scene_id) or (domain, scene_id) in pilot_scenes


def test_scene_package_task_detects_scene_allowlist() -> None:
    assert scene_package_migration.is_scene_package_task(
        "task_charts__hexbin_density__threshold_bin_count",
        domain="charts",
    )
    assert scene_package_migration.is_scene_package_task(
        "task_icons__pair_grid__attribute_delta_pair_count",
        domain="icons",
    )
    assert scene_package_migration.is_scene_package_task(
        "task_icons__single_transform_options__geometric_transform_result_label",
        domain="icons",
    )
    assert scene_package_migration.is_scene_package_task(
        "task_icons__paired_canvas__panel_attribute_change_count",
        domain="icons",
    )


def test_scene_package_runtime_records_omit_task_group_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_dummy__scene_package_demo__integer_count"
    monkeypatch.setattr(
        scene_package_migration,
        "MIGRATED_SCENE_PACKAGE_DOMAINS",
        frozenset({"dummy"}),
    )
    assert scene_package_migration.is_scene_package_task(task_id, domain="dummy")

    complexity = TaskComplexity(complexity_score=0.1, complexity_components={})
    train_record = TrainInstance(
        instance_version="v0",
        instance_id="dummy_instance",
        instance_seed=123,
        domain="dummy",
        task_group=None,
        task=task_id,
        scene_id="scene_package_demo",
        query_id="integer_count",
        prompt="How many marked dots are visible?",
        images=[ImageRecord(image_id="dummy_image", format="png", image_hash="abc", path="images/dummy.png")],
        answer_gt=TypedValue(type="integer", value=1),
        annotation_gt=TypedValue(type="point_set", value=[[8.0, 8.0]]),
        reward_contract=resolve_reward_contract(answer_type="integer", annotation_type="point_set"),
        task_complexity=complexity,
        trace_ref=TraceRef(shard_id="trace_shard_0001.jsonl.zst", line_index=0, trace_record_hash="abc"),
        versions={"renderer_version": "v0"},
    ).to_dict()
    curriculum_record = CurriculumIndex(
        instance_id="dummy_instance",
        domain="dummy",
        task_group=None,
        task=task_id,
        scene_id="scene_package_demo",
        query_id="integer_count",
        task_complexity=complexity,
    ).to_dict()
    trace_record = inject_taxonomy_metadata(
        {
            "scene_ir": {},
            "query_spec": {},
            "render_spec": {},
            "execution_trace": {},
        },
        task_id=task_id,
        taxonomy=TaxonomyEntry(
            domain="dummy",
            scene_id="scene_package_demo",
            source_domain="dummy",
            source_task_group="scene_package_demo",
        ),
        query_id="integer_count",
        registered_domain="dummy",
        registered_task_group=None,
    )

    for record in (train_record, curriculum_record, trace_record):
        for key in FORBIDDEN_MIGRATED_KEYS:
            assert key not in record

    taxonomy = trace_record["taxonomy"]
    assert "task_group" not in taxonomy["registered"]
    assert "implementation_task_group" not in taxonomy["source"]
    assert "config_task_group" not in taxonomy["source"]
    assert "prompt_task_group" not in taxonomy["source"]
