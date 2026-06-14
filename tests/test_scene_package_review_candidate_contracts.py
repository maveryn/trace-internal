"""Enforcement gates for scene-package review-candidate scenes."""
from __future__ import annotations
import ast
import inspect
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
import pytest
import yaml
from trace.core.scene_package_migration import parse_public_task_id, scene_package_review_target_scenes
from trace.core.prompts import load_scene_prompt_bundle
_FORBIDDEN_SHARED_IDENTIFIER_NAMES = {'task_id', 'query_id', 'supported_query_ids', 'objective_contract', 'namespace_prefix', 'runtime_key', 'selected_query', 'query_params'}
_FORBIDDEN_SHARED_STRING_CONSTANTS = {'query_id', 'task_id', 'supported_query_ids', 'objective_contract'}
_SCALAR_DIFFICULTY_KEY = 'complex' + 'ity'
_FORBIDDEN_CONFIG_KEYS = {
    'query_id_weights',
    'query_variant_weights',
    'balanced_query_id_sampling',
    'task_' + _SCALAR_DIFFICULTY_KEY,
    _SCALAR_DIFFICULTY_KEY,
    'task_coverage',
    'coverage',
}
_FORBIDDEN_PROMPT_CONFIG_KEY_FRAGMENTS = ('answer_hint', 'annotation_hint', 'json_example', 'object_description', 'rule_text', 'prompt_required', 'required_prompt')
_PROMPT_RENDER_FUNCTIONS = {'render_prompt', 'render_prompt_variants', 'render_task_prompt_variants', 'render_scene_prompt_variants'}
_PUBLIC_TASK_ID_RE = re.compile('^task_[a-z0-9_]+__[a-z0-9_]+__[a-z0-9_]+$')

def _review_candidate_scene_pairs() -> list[tuple[str, str]]:
    return [(str(domain), str(scene_id)) for domain, scene_ids in sorted(scene_package_review_target_scenes().items()) for scene_id in sorted(scene_ids)]

def _active_task_ids_for_review_candidate_scenes() -> dict[tuple[str, str], list[str]]:
    scene_pairs = _review_candidate_scene_pairs()
    if not scene_pairs:
        return {}
    active_by_scene = {pair: [] for pair in scene_pairs}
    from trace.tasks.registry import TASK_REGISTRY, ensure_scene_tasks_registered

    for domain, scene_id in scene_pairs:
        ensure_scene_tasks_registered(domain, scene_id)
        for task_id, task_cls in dict.items(TASK_REGISTRY):
            try:
                parts = parse_public_task_id(str(task_id))
            except ValueError:
                continue
            key = (parts.domain, parts.scene_id)
            if key == (domain, scene_id) and bool(getattr(task_cls, "default_dataset_enabled", False)):
                active_by_scene[key].append(str(task_id))
    return {key: sorted(value) for key, value in active_by_scene.items()}

def _read_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}

def _walk_mapping(value: Any, *, path: tuple[str, ...]=()) -> Iterable[tuple[tuple[str, ...], Any]]:
    yield (path, value)
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _walk_mapping(child, path=path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_mapping(child, path=path + (str(index),))

def _collect_bundle_ids(config: Any) -> set[str]:
    bundle_ids: set[str] = set()
    for path, value in _walk_mapping(config):
        if path and path[-1] == 'bundle_id' and isinstance(value, str) and value.strip():
            bundle_ids.add(str(value))
    return bundle_ids

def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return str(node.id)
    if isinstance(node, ast.Attribute):
        return str(node.attr)
    return ''

def _parse_python(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding='utf-8'), filename=str(path))

def _assert_no_legacy_slots_calls(path: Path) -> None:
    tree = _parse_python(path)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node.func) not in _PROMPT_RENDER_FUNCTIONS:
            continue
        for keyword in node.keywords:
            if keyword.arg == 'slots':
                offenders.append(f'{path}:{node.lineno}')
    assert offenders == [], 'review-candidate prompt calls must use dynamic_slots, not slots'

def _assert_shared_code_is_identity_free(scene_dir: Path, task_ids: set[str]) -> None:
    shared_dir = scene_dir / 'shared'
    if not shared_dir.exists():
        return
    offenders: list[str] = []
    for path in sorted(shared_dir.rglob('*.py')):
        tree = _parse_python(path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if 'for_query' in node.name or 'for_objective' in node.name:
                    offenders.append(f"{path}:{node.lineno} function name '{node.name}' routes by identity")
                for arg in list(node.args.args) + list(node.args.kwonlyargs):
                    if arg.arg in _FORBIDDEN_SHARED_IDENTIFIER_NAMES:
                        offenders.append(f"{path}:{arg.lineno} argument '{arg.arg}' is public identity")
            elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_SHARED_IDENTIFIER_NAMES:
                offenders.append(f"{path}:{node.lineno} identifier '{node.id}' is public identity")
            elif isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_SHARED_IDENTIFIER_NAMES:
                offenders.append(f"{path}:{node.lineno} attribute '{node.attr}' is public identity")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and 'QUERY' in target.id and ('ID' in target.id):
                        offenders.append(f"{path}:{target.lineno} query-id table '{target.id}' is not shared code")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = str(node.value)
                if value in task_ids or _PUBLIC_TASK_ID_RE.match(value):
                    offenders.append(f'{path}:{node.lineno} public task id string in shared code')
                if value in _FORBIDDEN_SHARED_STRING_CONSTANTS:
                    offenders.append(f'{path}:{node.lineno} public identity string {value!r} in shared code')
    assert offenders == [], '\n'.join(offenders)

def _assert_one_public_task_per_file(task_ids: list[str]) -> None:
    import trace.tasks
    from trace.tasks.registry import TASK_REGISTRY
    path_to_task_ids: dict[Path, list[str]] = {}
    for task_id in task_ids:
        cls = TASK_REGISTRY[task_id]
        source_path = Path(inspect.getsourcefile(cls) or '').resolve()
        path_to_task_ids.setdefault(source_path, []).append(task_id)
    offenders = {str(path): ids for path, ids in sorted(path_to_task_ids.items(), key=lambda item: str(item[0])) if len(ids) != 1}
    assert offenders == {}

def _declared_supported_query_ids(task_cls: type) -> tuple[str, ...]:
    raw = getattr(task_cls, 'supported_query_ids', ())
    if raw is None:
        return tuple()
    if isinstance(raw, str):
        values = (raw,)
    else:
        values = tuple(raw)
    return tuple((str(value) for value in values if str(value)))


def _doc_supported_query_ids(path: Path) -> tuple[str, ...]:
    """Extract the supported query ids listed in one task contract doc."""

    if not path.exists():
        return tuple()
    for line in path.read_text(encoding="utf-8").splitlines():
        if "Supported" not in line or "`query_id`" not in line:
            continue
        values = tuple(
            value
            for value in re.findall(r"`([^`]+)`", line)
            if value != "query_id"
        )
        return values
    return tuple()

def test_review_candidate_scenes_have_scene_package_source_layout() -> None:
    active_by_scene = _active_task_ids_for_review_candidate_scenes()
    if not active_by_scene:
        return
    import trace.tasks
    from trace.tasks.registry import TASK_REGISTRY
    repo_root = Path.cwd().resolve()
    for (domain, scene_id), task_ids in active_by_scene.items():
        assert task_ids, f'review-candidate scene has no default tasks: {domain}/{scene_id}'
        _assert_one_public_task_per_file(task_ids)
        for task_id in task_ids:
            parts = parse_public_task_id(task_id)
            expected = (repo_root / 'trace' / 'tasks' / domain / scene_id / f'{parts.objective_contract}.py').resolve()
            actual = Path(inspect.getsourcefile(TASK_REGISTRY[task_id]) or '').resolve()
            assert actual == expected, f'{task_id} must live at {expected.relative_to(repo_root)}'

def test_review_candidate_scene_shared_code_is_identity_free() -> None:
    active_by_scene = _active_task_ids_for_review_candidate_scenes()
    for (domain, scene_id), task_ids in active_by_scene.items():
        scene_dir = Path('trace') / 'tasks' / domain / scene_id
        _assert_shared_code_is_identity_free(scene_dir, set(task_ids))

def test_review_candidate_scenes_do_not_use_legacy_shared_scene_module() -> None:
    active_by_scene = _active_task_ids_for_review_candidate_scenes()
    offenders = [str(Path('trace') / 'tasks' / domain / scene_id / 'shared' / 'scene.py') for domain, scene_id in active_by_scene if (Path('trace') / 'tasks' / domain / scene_id / 'shared' / 'scene.py').exists()]
    assert offenders == []

def test_review_candidate_scene_configs_do_not_own_query_weights_or_prompt_prose() -> None:
    active_by_scene = _active_task_ids_for_review_candidate_scenes()
    for domain, scene_id in active_by_scene:
        config_path = Path('configs') / 'domains' / domain / f'{scene_id}.yaml'
        config = _read_yaml(config_path)
        assert config, f'review-candidate scene config missing or empty: {config_path}'
        offenders: list[str] = []
        for path, _value in _walk_mapping(config):
            if not path:
                continue
            key = path[-1]
            normalized = key.lower()
            if normalized in _FORBIDDEN_CONFIG_KEYS:
                offenders.append('.'.join(path))
            if any((fragment in normalized for fragment in _FORBIDDEN_PROMPT_CONFIG_KEY_FRAGMENTS)):
                offenders.append('.'.join(path))
        assert offenders == [], f'config owns forbidden query/prompt fields: {offenders}'

def test_review_candidate_scenes_use_v1_scene_prompt_bundles() -> None:
    active_by_scene = _active_task_ids_for_review_candidate_scenes()
    for domain, scene_id in active_by_scene:
        config_path = Path('configs') / 'domains' / domain / f'{scene_id}.yaml'
        bundle_ids = _collect_bundle_ids(_read_yaml(config_path))
        assert bundle_ids, f'review-candidate scene has no prompt bundle_id: {domain}/{scene_id}'
        for bundle_id in sorted(bundle_ids):
            bundle = load_scene_prompt_bundle(domain=domain, scene_id=scene_id, bundle_id=bundle_id)
            assert bundle.schema_version == 'v1'
            assert bundle.source_hash

def test_review_candidate_task_code_uses_dynamic_prompt_slots() -> None:
    active_by_scene = _active_task_ids_for_review_candidate_scenes()
    for (domain, scene_id), task_ids in active_by_scene.items():
        for task_id in task_ids:
            objective = parse_public_task_id(task_id).objective_contract
            _assert_no_legacy_slots_calls(Path('trace') / 'tasks' / domain / scene_id / f'{objective}.py')

def test_review_candidate_generated_outputs_have_v1_prompt_metadata() -> None:
    active_by_scene = _active_task_ids_for_review_candidate_scenes()
    if not active_by_scene:
        return
    import trace.tasks
    from trace.tasks.registry import create_task
    for (_domain, _scene_id), task_ids in active_by_scene.items():
        for task_id in task_ids:
            output = create_task(task_id).generate(instance_seed=17, params={}, max_attempts=50)
            query_spec = output.trace_payload.get('query_spec')
            assert isinstance(query_spec, Mapping), f'{task_id} missing query_spec'
            prompt_variant = query_spec.get('prompt_variant')
            assert isinstance(prompt_variant, Mapping), f'{task_id} missing prompt_variant metadata'
            assert prompt_variant.get('prompt_schema_version') == 'v1'
            assert prompt_variant.get('prompt_bundle_path')
            assert prompt_variant.get('prompt_bundle_hash')
            assert isinstance(prompt_variant.get('selected_keys'), Mapping)
            assert isinstance(prompt_variant.get('selected_indices'), Mapping)
            assert isinstance(prompt_variant.get('slot_values'), Mapping)
            assert isinstance(prompt_variant.get('slot_sources'), Mapping)
            assert isinstance(query_spec.get('prompt_variants'), Mapping)

def test_review_candidate_tasks_validate_supported_query_id_params() -> None:
    active_by_scene = _active_task_ids_for_review_candidate_scenes()
    if not active_by_scene:
        return
    import trace.tasks
    from trace.tasks.registry import TASK_REGISTRY
    for (_domain, _scene_id), task_ids in active_by_scene.items():
        for task_id in task_ids:
            task_cls = TASK_REGISTRY[task_id]
            supported_query_ids = _declared_supported_query_ids(task_cls)
            assert supported_query_ids, f'{task_id} must declare supported_query_ids'
            if len(supported_query_ids) == 1:
                assert supported_query_ids == ('single',), f'{task_id} single-query tasks must use query_id=\"single\"'
            task = task_cls()
            default_output = task.generate(instance_seed=29, params={}, max_attempts=100)
            assert str(getattr(default_output, 'query_id', '') or 'single') in supported_query_ids
            for param_key in ('query_id', 'query_variant'):
                for query_index, query_id in enumerate(supported_query_ids):
                    output = task.generate(instance_seed=29 + int(query_index), params={param_key: query_id}, max_attempts=100)
                    assert str(getattr(output, 'query_id', '') or 'single') == query_id
                with pytest.raises(ValueError, match='query_id'):
                    task.generate(instance_seed=29, params={param_key: '__unsupported_query_id__'}, max_attempts=100)


def test_review_candidate_single_query_task_docs_use_single_sentinel() -> None:
    active_by_scene = _active_task_ids_for_review_candidate_scenes()
    offenders: list[str] = []
    for (domain, scene_id), task_ids in active_by_scene.items():
        for task_id in task_ids:
            doc_path = Path('docs') / 'tasks' / domain / scene_id / f'{task_id}.md'
            supported_query_ids = _doc_supported_query_ids(doc_path)
            if len(supported_query_ids) != 1:
                continue
            if supported_query_ids != ('single',):
                offenders.append(f'{doc_path}: {supported_query_ids[0]}')
    assert offenders == []
