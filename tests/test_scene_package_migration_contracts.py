"""Scene-package migration enforcement tests.

The structural checks are gated by ``MIGRATED_SCENE_PACKAGE_DOMAINS`` so they
can land before any full domain migration is complete.
"""
from __future__ import annotations
import ast
from collections import defaultdict
import difflib
import inspect
import io
import os
from pathlib import Path
import token
import tokenize
from typing import Any
import pytest
import yaml
from trace.core.query_ids import NO_BRANCH_QUERY_IDS
import trace.core.scene_package_migration as scene_package_migration
from trace.core.scene_package_file_policies import scene_package_file_policy
from trace.core.scene_package_migration import MIGRATED_SCENE_PACKAGE_DOMAINS, MIGRATED_SCENE_PACKAGE_SCENES, SCENE_PACKAGE_PILOT_TASK_IDS, SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES, is_scene_package_migrated_scene, parse_public_task_id, scene_package_review_target_scenes
REPO_ROOT = Path(__file__).resolve().parents[1]
SCENE_LOCAL_SHARED_SUFFIXES = ('_scene', '_common', '_rendering', '_sampling', '_style', '_annotation')
IGNORED_GENERATED_DIR_NAMES = frozenset({'__pycache__', '.ipynb_checkpoints'})
TASK_IDENTITY_CONSTANT_NAMES = frozenset({'TASK_ID', 'QUERY_ID', 'SUPPORTED_QUERY_IDS'})
TASK_IDENTITY_FILENAME_SUFFIXES = ('_runtime', '_builder', '_generator', '_task', '_support', '_common')
LARGE_FUNCTION_DOCUMENTATION_MIN_LOC = 40
RETIRED_GAMES_SHARED_SYMBOLS = {'trace.tasks.games.shared.sampling': frozenset({'resolve_games_query_id'})}

def test_scene_package_domain_file_policies_are_registered() -> None:
    """Pin the domain-specific role-file policies used by review-candidate scenes."""
    charts_policy = scene_package_file_policy('charts')
    assert charts_policy is not None
    assert charts_policy.allowed_private_scene_files == frozenset({'_lifecycle.py'})
    assert charts_policy.role_shared_files == frozenset({'state.py', 'data.py', 'sampling.py', 'rendering.py', 'annotations.py', 'prompts.py', 'output.py', 'defaults.py', 'styles.py', 'layout.py', 'scales.py', 'metrics.py', 'spatial_primitives.py', 'projection.py', 'assets.py', 'option_rendering.py'})
    assert not charts_policy.allow_shared_subdirectories
    games_policy = scene_package_file_policy('games')
    assert games_policy is not None
    assert games_policy.allowed_private_scene_files == frozenset({'_lifecycle.py'})
    assert games_policy.role_shared_files == frozenset({'state.py', 'sampling.py', 'rendering.py', 'prompts.py', 'output.py', 'defaults.py', 'styles.py', 'layout.py', 'rules.py', 'annotations.py', 'option_rendering.py', 'components.py', 'labels.py'})
    assert not games_policy.allow_shared_subdirectories
    geometry_policy = scene_package_file_policy('geometry')
    assert geometry_policy is not None
    assert geometry_policy.allowed_private_scene_files == frozenset({'_lifecycle.py'})
    assert geometry_policy.role_shared_files == frozenset({'state.py', 'construction.py', 'relations.py', 'rendering.py', 'annotations.py', 'prompts.py', 'output.py', 'defaults.py', 'sampling.py', 'layout.py', 'styles.py', 'spatial_primitives.py', 'algebra.py', 'measurements.py', 'projection.py', 'option_rendering.py'})
    assert not geometry_policy.allow_shared_subdirectories
    graph_policy = scene_package_file_policy('graph')
    assert graph_policy is not None
    assert graph_policy.allowed_private_scene_files == frozenset({'_lifecycle.py'})
    assert graph_policy.role_shared_files == frozenset({'state.py', 'sampling.py', 'algorithms.py', 'rendering.py', 'annotations.py', 'prompts.py', 'output.py', 'defaults.py', 'layout.py', 'styles.py', 'labels.py', 'metrics.py', 'topology.py', 'projection.py', 'option_rendering.py'})
    assert not graph_policy.allow_shared_subdirectories
    symbolic_policy = scene_package_file_policy('symbolic')
    assert symbolic_policy is not None
    assert symbolic_policy.allowed_private_scene_files == frozenset({'_lifecycle.py'})
    assert symbolic_policy.role_shared_files == frozenset({'state.py', 'sampling.py', 'rules.py', 'layout.py', 'rendering.py', 'annotations.py', 'prompts.py', 'output.py', 'defaults.py', 'styles.py', 'assets.py', 'components.py', 'relations.py', 'metrics.py', 'transforms.py', 'spatial_primitives.py', 'option_rendering.py'})
    assert not symbolic_policy.allow_shared_subdirectories
    icons_policy = scene_package_file_policy('icons')
    assert icons_policy is not None
    assert icons_policy.allowed_private_scene_files == frozenset({'_lifecycle.py'})
    assert icons_policy.role_shared_files == frozenset({'state.py', 'defaults.py', 'sampling.py', 'layout.py', 'rendering.py', 'annotations.py', 'prompts.py', 'output.py', 'styles.py', 'assets.py', 'transforms.py', 'metrics.py', 'spatial_primitives.py', 'option_rendering.py', 'labels.py'})
    assert not icons_policy.allow_shared_subdirectories
    illustrations_policy = scene_package_file_policy('illustrations')
    assert illustrations_policy is not None
    assert illustrations_policy.allowed_private_scene_files == frozenset({'_lifecycle.py'})
    assert illustrations_policy.role_shared_files == frozenset({'state.py', 'defaults.py', 'sampling.py', 'layout.py', 'rendering.py', 'annotations.py', 'prompts.py', 'output.py', 'styles.py', 'assets.py', 'components.py', 'labels.py', 'objects.py', 'people.py', 'regions.py', 'relations.py', 'transforms.py', 'metrics.py', 'spatial_primitives.py', 'option_rendering.py', 'cutouts.py', 'edits.py', 'source_images.py'})
    assert not illustrations_policy.allow_shared_subdirectories
    three_d_policy = scene_package_file_policy('three_d')
    assert three_d_policy is not None
    assert three_d_policy.allowed_private_scene_files == frozenset({'_lifecycle.py'})
    assert three_d_policy.role_shared_files == frozenset({'state.py', 'defaults.py', 'sampling.py', 'layout.py', 'projection.py', 'rendering.py', 'annotations.py', 'prompts.py', 'output.py', 'objects.py', 'relations.py', 'metrics.py', 'components.py', 'labels.py', 'styles.py', 'option_rendering.py', 'spatial_primitives.py'})
    assert not three_d_policy.allow_shared_subdirectories

def _task_registry() -> dict[str, type[Any]]:
    from trace.tasks.registry import TASK_REGISTRY, ensure_all_tasks_registered, ensure_scene_tasks_registered
    if os.environ.get('TRACE_SCENE_PACKAGE_REVIEW_SCENE', '').strip():
        for domain, scenes in sorted(scene_package_review_target_scenes().items()):
            for scene_id in sorted(scenes):
                ensure_scene_tasks_registered(str(domain), str(scene_id))
        return TASK_REGISTRY
    ensure_all_tasks_registered()
    return TASK_REGISTRY

def _active_migrated_task_entries() -> list[tuple[str, type[Any]]]:
    if not MIGRATED_SCENE_PACKAGE_DOMAINS and (not MIGRATED_SCENE_PACKAGE_SCENES):
        return []
    entries: list[tuple[str, type[Any]]] = []
    for task_id, cls in sorted(dict.items(_task_registry())):
        parts = parse_public_task_id(str(task_id))
        if parts.domain in MIGRATED_SCENE_PACKAGE_DOMAINS or is_scene_package_migrated_scene(parts.domain, parts.scene_id):
            entries.append((str(task_id), cls))
    return entries

def _review_candidate_task_entries() -> list[tuple[str, type[Any]]]:
    entries: list[tuple[str, type[Any]]] = []
    target_scenes = _scene_package_review_target_scenes()
    for task_id, cls in sorted(dict.items(_task_registry())):
        parts = parse_public_task_id(str(task_id))
        if parts.scene_id in target_scenes.get(parts.domain, frozenset()):
            entries.append((str(task_id), cls))
    return entries

def _scene_package_review_target_scenes() -> dict[str, frozenset[str]]:
    """Return review-candidate scenes checked before artifact handoff."""
    return scene_package_review_target_scenes()

def _review_candidate_task_query_entries() -> list[tuple[str, type[Any], str, int]]:
    entries: list[tuple[str, type[Any], str, int]] = []
    for task_id, cls in _review_candidate_task_entries():
        supported_query_ids = getattr(cls, 'supported_query_ids', None)
        if supported_query_ids is None:
            entries.append((str(task_id), cls, '', 0))
            continue
        for query_id in tuple((str(value) for value in supported_query_ids)):
            seed = 2026061100 + len(entries) * 101
            entries.append((str(task_id), cls, str(query_id), seed))
    return entries

def _expected_task_path(task_id: str) -> Path:
    parts = parse_public_task_id(str(task_id))
    return REPO_ROOT / 'trace' / 'tasks' / parts.domain / parts.scene_id / f'{parts.objective_contract}.py'

def _migrated_domain_scenes(domain: str) -> set[str]:
    scenes: set[str] = set()
    for task_id in dict.keys(_task_registry()):
        parts = parse_public_task_id(str(task_id))
        if parts.domain != str(domain):
            continue
        if parts.domain in MIGRATED_SCENE_PACKAGE_DOMAINS or is_scene_package_migrated_scene(parts.domain, parts.scene_id):
            scenes.add(parts.scene_id)
    return scenes

def _import_module_name(node: ast.AST) -> str:
    if isinstance(node, ast.Import):
        return ''
    if isinstance(node, ast.ImportFrom):
        return str(node.module or '')
    return ''

def _module_name_for_path(source_path: Path) -> str:
    relative = source_path.resolve().relative_to(REPO_ROOT).with_suffix('')
    return '.'.join((str(part) for part in relative.parts))

def _resolve_import_modules(source_path: Path, node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [str(alias.name) for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    if int(node.level or 0) <= 0:
        return [str(node.module or '')]
    module_name = _module_name_for_path(source_path)
    package_parts = module_name.split('.')
    if source_path.name != '__init__.py':
        package_parts = package_parts[:-1]
    keep = len(package_parts) - int(node.level or 0) + 1
    if keep < 0:
        return [f"<invalid-relative-import:{node.module or ''}>"]
    resolved_parts = package_parts[:keep]
    if node.module:
        resolved_parts.extend(str(node.module).split('.'))
    return ['.'.join(resolved_parts)]

def _scene_source_files(domain: str, scene_id: str) -> list[Path]:
    scene_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id)
    return [path for path in sorted(scene_dir.rglob('*.py')) if path.name != '__init__.py' and (not any((part in IGNORED_GENERATED_DIR_NAMES for part in path.parts)))]

def _source_function_loc(source_lines: list[str], node: ast.AST) -> int:
    start = int(getattr(node, 'lineno', 1))
    end = int(getattr(node, 'end_lineno', start))
    body_lines = source_lines[start - 1:end]
    return sum((1 for line in body_lines if line.strip() and (not line.lstrip().startswith('#'))))

def _has_orientation_docstring_or_comment(source_lines: list[str], node: ast.AST) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return True
    docstring = ast.get_docstring(node, clean=True)
    if docstring and len(str(docstring).split()) >= 6:
        return True
    if not node.body:
        return True
    first_body_line = int(getattr(node.body[0], 'lineno', node.lineno))
    header_to_body = source_lines[int(node.lineno):max(int(node.lineno), first_body_line - 1)]
    for line in header_to_body:
        stripped = line.strip()
        if stripped.startswith('#') and len(stripped.lstrip('#').strip().split()) >= 6:
            return True
    return False

def _review_candidate_task_files_by_scene() -> dict[tuple[str, str], dict[Path, list[str]]]:
    grouped: dict[tuple[str, str], dict[Path, list[str]]] = defaultdict(lambda: defaultdict(list))
    for task_id, cls in _review_candidate_task_entries():
        parts = parse_public_task_id(task_id)
        source_path = Path(inspect.getsourcefile(cls) or '').resolve()
        grouped[parts.domain, parts.scene_id][source_path].append(task_id)
    return {key: {path: sorted(task_ids) for path, task_ids in sorted(files.items())} for key, files in sorted(grouped.items())}

def _normalized_source_tokens(source: str) -> tuple[str, ...]:
    normalized: list[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in {token.ENCODING, token.ENDMARKER, token.INDENT, token.DEDENT, token.NEWLINE, token.NL, token.COMMENT}:
            continue
        if tok.type == token.STRING:
            normalized.append('STR')
        elif tok.type == token.NUMBER:
            normalized.append('NUM')
        else:
            normalized.append(tok.string)
    return tuple(normalized)

def _normalized_public_task_tokens(source_path: Path) -> tuple[str, ...]:
    return _normalized_source_tokens(source_path.read_text(encoding='utf-8'))

def _normalized_source_units(source_path: Path) -> list[tuple[str, tuple[str, ...]]]:
    source = source_path.read_text(encoding='utf-8')
    tree = ast.parse(source)
    units: list[tuple[str, tuple[str, ...]]] = []

    def add_unit(name: str, node: ast.AST) -> None:
        segment = ast.get_source_segment(source, node)
        if segment:
            units.append((name, _normalized_source_tokens(segment)))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_unit(node.name, node)
        elif isinstance(node, ast.ClassDef):
            add_unit(node.name, node)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add_unit(f'{node.name}.{item.name}', item)
    return units

def _top_level_structure_signature(source_path: Path) -> tuple[str, ...]:
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    signature: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            method_names = [item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
            base_count = len(node.bases)
            decorator_count = len(node.decorator_list)
            signature.append(f"class:bases={base_count}:decorators={decorator_count}:methods={','.join(method_names)}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            signature.append(f'function:{node.name}:args={len(node.args.args)}:body={len(node.body)}')
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            signature.append(type(node).__name__)
        elif isinstance(node, ast.ImportFrom):
            signature.append(f"importfrom:{node.level}:{node.module or ''}")
        elif isinstance(node, ast.Import):
            signature.append('import')
        else:
            signature.append(type(node).__name__)
    return tuple(signature)

def _sequence_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    return difflib.SequenceMatcher(a=left, b=right, autojunk=False).ratio()

def _token_set_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)

def _token_fingerprint(tokens: tuple[str, ...], *, window: int=12, max_size: int=256) -> frozenset[int]:
    if len(tokens) < window:
        return frozenset()
    hashes = {hash(tokens[index:index + window]) for index in range(0, len(tokens) - window + 1)}
    return frozenset(sorted(hashes)[:max_size])

def _fingerprint_overlap(left: frozenset[int], right: frozenset[int]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)

def _similar_length(left_size: int, right_size: int, *, min_ratio: float) -> bool:
    smaller = min(int(left_size), int(right_size))
    larger = max(int(left_size), int(right_size))
    return larger > 0 and smaller / larger >= float(min_ratio)

def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return str(node.id)
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f'{prefix}.{node.attr}' if prefix else str(node.attr)
    return ''

def _meaningful_function_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], 'value', None), ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    return body

def _shared_imported_names(source_path: Path, tree: ast.AST, *, domain: str, scene_id: str) -> set[str]:
    shared_names: set[str] = set()
    scene_shared_prefix = f'trace.tasks.{domain}.{scene_id}.shared'
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        modules = _resolve_import_modules(source_path, node)
        if not any((module_name.startswith(scene_shared_prefix) for module_name in modules)):
            continue
        for alias in node.names:
            shared_names.add(str(alias.asname or alias.name))
    return shared_names

def _shared_import_modules(source_path: Path, tree: ast.AST, *, domain: str, scene_id: str) -> set[str]:
    modules: set[str] = set()
    scene_shared_prefix = f'trace.tasks.{domain}.{scene_id}.shared'
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        for module_name in _resolve_import_modules(source_path, node):
            if module_name.startswith(scene_shared_prefix):
                modules.add(str(module_name))
    return modules

def _private_scene_imported_names(source_path: Path, tree: ast.AST, *, domain: str, scene_id: str) -> set[str]:
    policy = scene_package_file_policy(str(domain))
    if policy is None:
        return set()
    scene_prefix = f'trace.tasks.{domain}.{scene_id}'
    private_modules = {f'{scene_prefix}.{Path(filename).stem}' for filename in policy.allowed_private_scene_files}
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        modules = _resolve_import_modules(source_path, node)
        if not any((module_name in private_modules for module_name in modules)):
            continue
        for alias in node.names:
            imported_names.add(str(alias.asname or alias.name))
    return imported_names

def _assignment_target_names(node: ast.Assign | ast.AnnAssign) -> set[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    names: set[str] = set()
    for target in targets:
        if isinstance(target, ast.Name):
            names.add(str(target.id))
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                if isinstance(item, ast.Name):
                    names.add(str(item.id))
    return names

def _has_local_objective_hooks(tree: ast.AST, *, class_name: str) -> bool:
    hook_prefixes = ('_prepare_', '_construct_', '_build_', '_bind_', '_resolve_')
    for node in getattr(tree, 'body', []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith(hook_prefixes) and len(_meaningful_function_body(node)) >= 1:
                return True
        if isinstance(node, ast.ClassDef) and node.name == str(class_name):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith(hook_prefixes) and len(_meaningful_function_body(item)) >= 1:
                        return True
    return False

def _static_string_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return str(node.value)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_string_value(node.left)
        right = _static_string_value(node.right)
        if left is not None and right is not None:
            return f'{left}{right}'
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return None
            parts.append(str(value.value))
        return ''.join(parts)
    return None

def _scene_public_identities(domain: str, scene_id: str, files: dict[Path, list[str]]) -> set[str]:
    identities: set[str] = set()
    for task_ids in files.values():
        for task_id in task_ids:
            parts = parse_public_task_id(task_id)
            identities.add(str(task_id))
            identities.add(str(parts.objective_contract))
            cls = _task_registry()[str(task_id)]
            identities.add(str(cls.__name__))
            for query_id in tuple((str(value) for value in getattr(cls, 'supported_query_ids', ()))):
                if query_id and query_id not in NO_BRANCH_QUERY_IDS:
                    identities.add(str(query_id))
    identities.discard(str(domain))
    identities.discard(str(scene_id))
    return {value for value in identities if value}

def _shared_filename_matches_public_identity(stem: str, identity: str) -> bool:
    if not identity:
        return False
    if stem == identity:
        return True
    if stem.startswith(f'{identity}_') or stem.endswith(f'_{identity}') or f'_{identity}_' in stem:
        return True
    return any((stem == f'{identity}{suffix}' for suffix in TASK_IDENTITY_FILENAME_SUFFIXES))

def _walk_mapping_keys(value: Any, *, path: tuple[str, ...]=()) -> list[tuple[tuple[str, ...], str]]:
    keys: list[tuple[tuple[str, ...], str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = (*path, key_text)
            keys.append((child_path, key_text))
            keys.extend(_walk_mapping_keys(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            keys.extend(_walk_mapping_keys(child, path=(*path, f'[{index}]')))
    return keys

@pytest.mark.parametrize(('task_id', 'cls'), _active_migrated_task_entries())
def test_migrated_scene_package_task_source_path_and_class_contract(task_id: str, cls: type[Any]) -> None:
    expected = _expected_task_path(task_id).resolve()
    actual = Path(inspect.getsourcefile(cls) or '').resolve()
    assert actual == expected
    assert not hasattr(cls, 'scene_id')

def test_migrated_scene_package_modules_define_one_active_task() -> None:
    tasks_by_path: dict[Path, list[str]] = defaultdict(list)
    for task_id, cls in _active_migrated_task_entries():
        source_path = Path(inspect.getsourcefile(cls) or '').resolve()
        tasks_by_path[source_path].append(task_id)
    for source_path, task_ids in sorted(tasks_by_path.items()):
        assert len(task_ids) == 1, f'{source_path} owns multiple active public tasks: {task_ids}'

def test_migrated_scene_package_domain_configs_are_scene_keyed() -> None:
    for domain in sorted(MIGRATED_SCENE_PACKAGE_DOMAINS):
        scenes = _migrated_domain_scenes(str(domain))
        config_dir = REPO_ROOT / 'configs' / 'domains' / str(domain)
        expected_files = {'base.yaml', *(f'{scene_id}.yaml' for scene_id in scenes)}
        actual_files = {path.name for path in config_dir.glob('*.yaml')}
        assert config_dir.exists()
        assert expected_files.issubset(actual_files)
        assert actual_files == expected_files

def test_migrated_scene_package_scene_configs_exist() -> None:
    for domain, scenes in sorted(MIGRATED_SCENE_PACKAGE_SCENES.items()):
        config_dir = REPO_ROOT / 'configs' / 'domains' / str(domain)
        assert config_dir.exists()
        for scene_id in sorted(scenes):
            assert (config_dir / f'{scene_id}.yaml').exists()

def test_migrated_scene_package_domain_shared_has_no_scene_local_modules() -> None:
    for domain in sorted(MIGRATED_SCENE_PACKAGE_DOMAINS):
        scenes = _migrated_domain_scenes(str(domain))
        shared_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / 'shared'
        if not shared_dir.exists():
            continue
        for path in shared_dir.rglob('*.py'):
            if path.name == '__init__.py':
                continue
            stem = path.stem
            for scene_id in scenes:
                assert not stem.startswith(f'{scene_id}_'), f'{path} is scene-local and belongs under {scene_id}/shared'
                assert not any((f'{scene_id}{suffix}' in stem for suffix in SCENE_LOCAL_SHARED_SUFFIXES)), f'{path} is scene-local and belongs under {scene_id}/shared'

def test_migrated_scene_package_tasks_do_not_import_retired_scene_id_paths() -> None:
    for task_id, cls in _active_migrated_task_entries():
        parts = parse_public_task_id(task_id)
        source_path = Path(inspect.getsourcefile(cls) or '')
        tree = ast.parse(source_path.read_text(encoding='utf-8'))
        active_scenes = _migrated_domain_scenes(parts.domain)
        for node in ast.walk(tree):
            module_name = _import_module_name(node)
            if not module_name.startswith(f'trace.tasks.{parts.domain}.'):
                continue
            route = module_name.removeprefix(f'trace.tasks.{parts.domain}.').split('.', 1)[0]
            assert route in active_scenes or route == 'shared', f'{task_id} imports retired scene path {module_name}'
            assert route in {parts.scene_id, 'shared'}, f'{task_id} imports sibling scene path {module_name}'

def test_review_candidate_scene_packages_do_not_import_sibling_scenes_or_other_domains() -> None:
    allowed_task_roots = {'base', 'registry', 'shared'}
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        for scene_id in sorted(scenes):
            scene_prefix = f'trace.tasks.{domain}.{scene_id}'
            policy = scene_package_file_policy(str(domain))
            allowed_private_modules = {f'{scene_prefix}.{Path(filename).stem}' for filename in (policy.allowed_private_scene_files if policy is not None else frozenset())}
            for source_path in _scene_source_files(str(domain), str(scene_id)):
                tree = ast.parse(source_path.read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    for module_name in _resolve_import_modules(source_path, node):
                        if not module_name.startswith('trace.tasks.'):
                            continue
                        parts = module_name.split('.')
                        if len(parts) < 3:
                            continue
                        task_root = parts[2]
                        if task_root in allowed_task_roots:
                            continue
                        assert task_root == str(domain), f'{source_path} imports another domain task package {module_name}; review-candidate scenes may use only their own domain, trace.tasks.<domain>.shared, or trace.tasks.shared'
                        route = parts[3] if len(parts) > 3 else ''
                        assert route in {'', str(scene_id), 'shared'}, f'{source_path} imports sibling scene package {module_name}; promote reusable helpers to domain/shared after scene migration'
                        if module_name == scene_prefix:
                            continue
                        if module_name in allowed_private_modules:
                            continue
                        if module_name.startswith(f'{scene_prefix}.'):
                            suffix = module_name.removeprefix(f'{scene_prefix}.')
                            assert suffix.startswith('shared'), f'{source_path} imports public task module {module_name}; public objectives must not depend on sibling public task files'

def test_review_candidate_public_task_files_do_not_import_sibling_public_task_modules() -> None:
    failures: list[str] = []
    for (domain, scene_id), files in _review_candidate_task_files_by_scene().items():
        public_file_modules = {_module_name_for_path(source_path) for source_path in files}
        for source_path in sorted(files):
            source_module = _module_name_for_path(source_path)
            tree = ast.parse(source_path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                for module_name in _resolve_import_modules(source_path, node):
                    if module_name == source_module:
                        continue
                    if module_name in public_file_modules:
                        failures.append(f'{domain}/{scene_id}: {source_path.name} imports sibling public task module {module_name}')
    assert not failures, '\n'.join(failures[:80])

def test_games_domain_shared_modules_do_not_import_scene_packages() -> None:
    """Domain-shared games helpers must not depend on scene packages."""
    failures: list[str] = []
    shared_dir = REPO_ROOT / 'trace' / 'tasks' / 'games' / 'shared'
    for source_path in sorted(shared_dir.glob('*.py')):
        if source_path.name == '__init__.py':
            continue
        tree = ast.parse(source_path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            for module_name in _resolve_import_modules(source_path, node):
                if not module_name.startswith('trace.tasks.games.'):
                    continue
                parts = module_name.split('.')
                route = parts[3] if len(parts) > 3 else ''
                if route != 'shared':
                    failures.append(f'{source_path.relative_to(REPO_ROOT)} imports games scene package {module_name}; domain-shared helpers must be scene-neutral')
    assert not failures, '\n'.join(failures[:80])

def test_three_d_object_resource_registry_does_not_import_scene_packages() -> None:
    """The 3D object registry is domain-owned data, not a scene-shared adapter."""
    failures: list[str] = []
    source_path = REPO_ROOT / 'trace' / 'tasks' / 'three_d' / 'shared' / 'object_resources.py'
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        for module_name in _resolve_import_modules(source_path, node):
            if not module_name.startswith('trace.tasks.three_d.'):
                continue
            parts = module_name.split('.')
            route = parts[3] if len(parts) > 3 else ''
            if route != 'shared':
                failures.append(f'{source_path.relative_to(REPO_ROOT)} imports three_d scene package {module_name}; domain-owned resource registries must not depend on scene shared code')
    assert not failures, '\n'.join(failures[:80])

def test_three_d_task_support_exposes_identity_free_namespace_helpers() -> None:
    """New three_d migration code should use namespace helpers, not public task ids."""
    from trace.tasks.three_d.shared import task_support
    axis_signature = inspect.signature(task_support.resolve_axis_variant_for_namespace)
    count_signature = inspect.signature(task_support.resolve_count_for_namespace)
    assert 'namespace' in axis_signature.parameters
    assert 'task_id' not in axis_signature.parameters
    assert 'namespace' in count_signature.parameters
    assert 'task_id' not in count_signature.parameters
    axis_kwargs = {
        'gen_defaults': {},
        'instance_seed': 90210,
        'supported_variants': ('front', 'back'),
        'explicit_key': 'query_id',
        'weights_key': 'query_id_weights',
        'balance_flag_key': 'balanced_query_id_sampling',
        'allow_locked': True,
    }
    new_axis = task_support.resolve_axis_variant_for_namespace(
        {'query_id': 'back'},
        namespace='three_d.test.axis',
        **axis_kwargs,
    )
    legacy_axis = task_support.resolve_axis_variant(
        {'query_id': 'back'},
        task_id='three_d.test',
        axis_namespace='axis',
        **axis_kwargs,
    )
    assert new_axis == legacy_axis == ('back', {'back': 1.0, 'front': 0.0})
    count_kwargs = {
        'gen_defaults': {},
        'instance_seed': 90211,
        'key': 'target_count',
        'default_min': 2,
        'default_max': 4,
        'lower': 1,
        'upper': 5,
    }
    new_count = task_support.resolve_count_for_namespace(
        {'target_count': 3},
        namespace='three_d.test.target_count',
        **count_kwargs,
    )
    legacy_count = task_support.resolve_count(
        {'target_count': 3},
        task_id='three_d.test',
        **count_kwargs,
    )
    assert new_count == legacy_count == (3, {'3': 1.0})

def test_three_d_projected_object_geometry_is_not_owned_by_object_scene() -> None:
    """Generic projected-object geometry should live outside object-scene grammar."""
    from trace.tasks.three_d.shared import object_scene
    from trace.tasks.three_d.shared import projected_object_geometry
    assert object_scene.object_reference_points is projected_object_geometry.object_reference_points
    assert object_scene.object_screen_bbox is projected_object_geometry.object_screen_bbox
    assert object_scene.bbox_intersection_area is projected_object_geometry.bbox_intersection_area
    assert object_scene._object_reference_points is projected_object_geometry.object_reference_points
    assert object_scene._object_screen_bbox is projected_object_geometry.object_screen_bbox
    assert object_scene._bbox_intersection_area is projected_object_geometry.bbox_intersection_area
    assert projected_object_geometry.bbox_intersection_area([0, 0, 10, 10], [4, 5, 12, 14]) == 30.0

def test_review_candidate_games_scenes_do_not_import_retired_domain_shared_helpers() -> None:
    """Migrated games scenes must not keep legacy query-selection helpers."""
    failures: list[str] = []
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        if str(domain) != 'games':
            continue
        for scene_id in sorted(scenes):
            for source_path in _scene_source_files('games', str(scene_id)):
                tree = ast.parse(source_path.read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    for module_name in _resolve_import_modules(source_path, node):
                        if isinstance(node, ast.ImportFrom):
                            retired_symbols = RETIRED_GAMES_SHARED_SYMBOLS.get(str(module_name), frozenset())
                            for alias in node.names:
                                if alias.name in retired_symbols:
                                    failures.append(f'{source_path.relative_to(REPO_ROOT)} imports retired games domain helper {module_name}.{alias.name}; use task-owned query selection')
    assert not failures, '\n'.join(failures[:100])

def test_three_d_is_not_allowlisted_before_full_scene_package_migration() -> None:
    assert 'three_d' not in MIGRATED_SCENE_PACKAGE_DOMAINS

def test_scene_package_migration_registries_only_track_review_candidate_scenes() -> None:
    assert not MIGRATED_SCENE_PACKAGE_DOMAINS
    expected_candidate_scenes = {'charts': frozenset({'annotated_series', 'area', 'bar_3d', 'boxplot', 'candlestick', 'combo_mark', 'contour_density', 'curve_panels', 'dashboard', 'density_curve', 'dumbbell', 'error_interval', 'errorbar_series', 'heatmap', 'hexbin_density', 'histogram', 'marker_map', 'matrix', 'multiseries', 'parallel_coords', 'part_whole', 'pictogram', 'population_pyramid', 'radar', 'radial_progress', 'radial_sankey', 'region_map', 'sankey', 'scatter_cluster', 'scatter_facet_grid', 'scatter_points', 'scatter_readout', 'scientific_axis_frame', 'single_series'}), 'games': frozenset({'2048', 'backgammon', 'battleship', 'bingo', 'bowling', 'brick_breaker', 'bubble_shooter', 'cards', 'checkers', 'chess', 'chess_variant', 'circular_chess', 'connect_four', 'crossing', 'darts', 'dominoes', 'dots_and_boxes', 'go', 'hex', 'irregular_link_board', 'lane_runner', 'ludo_board', 'mancala_pit_board', 'marble_chain', 'match3', 'minecraft', 'minesweeper', 'minigolf', 'nine_mens_morris', 'pacman', 'pinball_table', 'platformer', 'pool', 'racing_track', 'radial_hunt_board', 'reversi', 'rhythm', 'rule_override_board', 'sixteen_soldiers', 'sliding_block', 'snake', 'snakes_ladders', 'sokoban', 'solitaire', 'space_shooter'}), 'geometry': frozenset({'angle_relations', 'area_partition', 'bearing_route', 'circle_centerline_overlap', 'circle_pair_tangents', 'circle_polygon_composite', 'circle_theorem', 'composite_shape', 'concentric_chord', 'cone_net', 'container_volume_transfer', 'coordinate_composite', 'coordinate_panels', 'coordinate_plane', 'cuboid_views', 'cylinder_wrap', 'function_graph', 'function_panels', 'graph_paper', 'incircle_tangents', 'marked_polygon_equation', 'measuring_tools', 'paper_fold'}), 'graph': frozenset({'adjacency', 'automaton', 'binary_tree', 'flow_network', 'graph_options', 'metro', 'node_link', 'pedigree_chart'}), 'icons': frozenset({'icon_cutout', 'icon_field', 'mirror_grid', 'named_field', 'named_grid', 'named_path', 'named_ring', 'pair_grid', 'paired_canvas', 'pattern_grid', 'reference_canvas', 'sequence_strip', 'single_transform_options', 'venn_field'}), 'illustrations': frozenset({'construction_site', 'environment', 'indoor_room', 'isometric_farmstead', 'isometric_harbor', 'isometric_quarry', 'library', 'park_playground', 'pixel_village', 'rpg_dungeon', 'rpg_house'}), 'three_d': frozenset({'object_cluster', 'surface_fixture'})}
    expected_candidate_scenes = {
        **expected_candidate_scenes,
        "charts": frozenset((*expected_candidate_scenes["charts"], "size_encoding", "small_multiple", "style_legend", "sunburst", "surface_3d", "table", "treemap", "uncertainty_band", "violin", "waterfall")),
        "games": frozenset((*expected_candidate_scenes["games"], "tetris", "tic_tac_toe_3d", "tower_defense", "tower_draughts_board", "ultimate_tictactoe")),
        "geometry": frozenset((*expected_candidate_scenes["geometry"], "parallel_segment_proportion", "polygon_angle_chase", "pythagorean_dissection", "pythagorean_tree", "rectangular_solid", "regular_polygon_decomposition", "right_triangle_altitude_theorem", "sector", "shape_gallery", "similar_figure_measure_transfer", "solid_cross_section", "solid_formula", "solid_revolution", "special_quadrilateral")),
        "icons": frozenset((*expected_candidate_scenes["icons"], "named_strip", "overlap_grid", "wallpaper_panels")),
        "illustrations": frozenset((*expected_candidate_scenes["illustrations"], "rpg_tactical_map")),
        "graph": frozenset((*expected_candidate_scenes["graph"], "phylogeny_tree")),
        "three_d": frozenset((*expected_candidate_scenes["three_d"], "object_scene", "room", "street")),
    }
    assert MIGRATED_SCENE_PACKAGE_SCENES == expected_candidate_scenes
    assert SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES == expected_candidate_scenes
    assert not SCENE_PACKAGE_PILOT_TASK_IDS
    assert scene_package_migration.is_scene_package_task('task_charts__annotated_series__callout_endpoint_change_value', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__area__interval_area_value', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__density_curve__mean_extremum_label', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__error_interval__reference_containment_count', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__errorbar_series__bound_extremum_x_label', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__histogram__interval_mass', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__marker_map__marker_region_threshold_count', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__matrix__threshold_cell_count', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__radial_progress__progress_threshold_count', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__radial_sankey__transfer_total_value', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__scatter_points__axis_threshold_point_count', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__scatter_readout__series_x_extremum_label', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_charts__scientific_axis_frame__axis_span_value', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_geometry__angle_relations__triangle_exterior_angle', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__area_partition__total_area_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__bearing_route__final_bearing_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__circle_polygon_composite__tangent_angle_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__circle_theorem__diameter_perpendicular_chord_length_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__concentric_chord__chord_length_from_radii', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__container_volume_transfer__fill_count_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__coordinate_composite__intersection_point_count', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__coordinate_panels__quadrilateral_shape_match_label', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__cuboid_views__cuboid_projection_surface_area_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__function_graph__average_rate_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__marked_polygon_equation__side_variable_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__measuring_tools__shape_length_value_polygon_side_ruler_reading', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__paper_fold__paper_fold_angle_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__parallel_segment_proportion__variable_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__right_triangle_altitude_theorem__altitude_to_hypotenuse_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__sector__sector_area_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__solid_revolution__revolution_cylinder_volume_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_geometry__special_quadrilateral__diagonal_angle_value', domain='geometry')
    assert scene_package_migration.is_scene_package_task('task_graph__adjacency__traversal_kth_label', domain='graph')
    assert scene_package_migration.is_scene_package_task('task_graph__automaton__state_after_input_label', domain='graph')
    assert scene_package_migration.is_scene_package_task('task_graph__flow_network__max_flow_value', domain='graph')
    assert scene_package_migration.is_scene_package_task('task_graph__graph_options__same_structure_label', domain='graph')
    assert scene_package_migration.is_scene_package_task('task_graph__metro__station_membership_count', domain='graph')
    assert scene_package_migration.is_scene_package_task('task_icons__icon_cutout__partial_match_label', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__icon_field__singleton_type_count', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__icon_field__most_frequent_type_count', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__mirror_grid__mirror_symmetry_match_label', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__named_grid__scoped_attribute_count', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__named_path__path_neighbor_label', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__named_ring__scoped_attribute_count', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__pattern_grid__attribute_pattern_violation_index', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_illustrations__rpg_house__swapped_tile_pair_label', domain='illustrations')
    assert scene_package_migration.is_scene_package_task('task_illustrations__rpg_tactical_map__movement_reachable_tile_label', domain='illustrations')
    assert scene_package_migration.is_scene_package_task('task_three_d__surface_fixture__repeated_element_count', domain='three_d')
    assert scene_package_migration.is_scene_package_task('task_three_d__street__intersection_nearest_label', domain='three_d')

def test_task_classes_do_not_claim_scene_package_migration_independently() -> None:
    """Migration state must come only from central scene registries."""
    failures = [f'{task_id}: remove task-level scene_package_migrated; use central scene registries' for task_id, cls in sorted(dict.items(_task_registry())) if hasattr(cls, 'scene_package_migrated')]
    assert not failures, '\n'.join(failures[:120])

def test_review_candidate_scenes_have_only_public_task_files_outside_shared() -> None:
    """Outside shared/, a scene package may contain public task files and approved private scene files."""
    failures: list[str] = []
    for (domain, scene_id), files in _review_candidate_task_files_by_scene().items():
        scene_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id)
        expected = {'__init__.py'}
        policy = scene_package_file_policy(str(domain))
        if policy is not None:
            expected.update(policy.allowed_private_scene_files)
        for task_ids in files.values():
            for task_id in task_ids:
                expected.add(f'{parse_public_task_id(str(task_id)).objective_contract}.py')
        for source_path in sorted(scene_dir.glob('*.py')):
            if source_path.name not in expected:
                failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} is outside shared/ but is neither an active public task file nor an approved private scene file')
        for source_path, task_ids in sorted(files.items()):
            if source_path.parent != scene_dir:
                failures.append(f'{domain}/{scene_id}: registered task(s) {task_ids} live outside the scene root public-file layer')
    assert not failures, '\n'.join(failures[:120])

def test_review_candidate_scenes_follow_domain_shared_file_policies() -> None:
    """Domains with a file policy must use only the agreed shared filenames."""
    failures: list[str] = []
    for (domain, scene_id), _files in _review_candidate_task_files_by_scene().items():
        policy = scene_package_file_policy(str(domain))
        if policy is None:
            continue
        shared_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id) / 'shared'
        if not shared_dir.exists():
            continue
        if not policy.allow_shared_subdirectories:
            for child in sorted(shared_dir.iterdir()):
                if child.name in IGNORED_GENERATED_DIR_NAMES:
                    continue
                if child.is_dir() and child.name != '__pycache__':
                    failures.append(f'{domain}/{scene_id}: {child.relative_to(REPO_ROOT)} is a shared subdirectory, but this domain policy allows only direct role files')
        for source_path in sorted(shared_dir.rglob('*.py')):
            if any((part in IGNORED_GENERATED_DIR_NAMES for part in source_path.parts)):
                continue
            if source_path.parent != shared_dir and (not policy.allow_shared_subdirectories):
                failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} is nested under shared/, but this domain policy allows only direct role files')
                continue
            if source_path.name not in policy.allowed_shared_files:
                failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} is not an allowed shared filename for {domain}; allowed={sorted(policy.allowed_shared_files)}')
    assert not failures, 'Review-candidate scenes must follow their domain file policy; do not invent shared filenames.\n' + '\n'.join(failures[:120])

def test_review_target_scene_large_functions_have_orientation_comments() -> None:
    """Large pending/complete scene functions need a role/invariant note at the top."""
    failures: list[str] = []
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        for scene_id in sorted(scenes):
            for source_path in _scene_source_files(str(domain), str(scene_id)):
                source = source_path.read_text(encoding='utf-8')
                source_lines = source.splitlines()
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    loc = _source_function_loc(source_lines, node)
                    if int(loc) < LARGE_FUNCTION_DOCUMENTATION_MIN_LOC:
                        continue
                    if _has_orientation_docstring_or_comment(source_lines, node):
                        continue
                    failures.append(f'{source_path.relative_to(REPO_ROOT)}:{node.lineno} function {node.name!r} has {loc} non-comment LOC and needs a docstring or leading comment explaining its scene role and key invariant')
    assert not failures, '\n'.join(failures[:120])

def test_review_candidate_scene_generation_shared_config_is_not_task_or_query_owned() -> None:
    forbidden_fragments = ('query_id', 'query_variant', 'task_id', 'task_variant')
    failures: list[str] = []
    task_files_by_scene = _review_candidate_task_files_by_scene()
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        for scene_id in sorted(scenes):
            config_path = REPO_ROOT / 'configs' / 'domains' / str(domain) / f'{scene_id}.yaml'
            if not config_path.exists():
                failures.append(f'{domain}/{scene_id}: missing scene config {config_path.relative_to(REPO_ROOT)}')
                continue
            config = yaml.safe_load(config_path.read_text(encoding='utf-8')) or {}
            if not isinstance(config, dict):
                failures.append(f'{domain}/{scene_id}: scene config must be a mapping')
                continue
            generation = config.get('generation') or {}
            if not isinstance(generation, dict):
                continue
            shared = generation.get('shared') or {}
            if not isinstance(shared, dict):
                continue
            scene_task_ids = {task_id for task_ids in task_files_by_scene.get((str(domain), str(scene_id)), {}).values() for task_id in task_ids}
            objective_contracts = {parse_public_task_id(task_id).objective_contract for task_id in scene_task_ids}
            for key_path, key_text in _walk_mapping_keys(shared):
                lower_key = key_text.lower()
                if any((fragment in lower_key for fragment in forbidden_fragments)):
                    failures.append(f"{domain}/{scene_id}: generation.shared.{'.'.join(key_path)} is task/query-owned")
                if key_text in scene_task_ids or key_text in objective_contracts:
                    failures.append(f"{domain}/{scene_id}: generation.shared.{'.'.join(key_path)} references public task identity")
    assert not failures, '\n'.join(failures[:100])

def test_review_candidate_public_task_files_are_not_duplicate_scene_bodies() -> None:
    failures: list[str] = []
    for (domain, scene_id), files in _review_candidate_task_files_by_scene().items():
        public_files = sorted(files)
        token_cache = {path: _normalized_public_task_tokens(path) for path in public_files}
        structure_cache = {path: _top_level_structure_signature(path) for path in public_files}
        for index, left in enumerate(public_files):
            for right in public_files[index + 1:]:
                left_tokens = token_cache[left]
                right_tokens = token_cache[right]
                min_tokens = min(len(left_tokens), len(right_tokens))
                if min_tokens < 400:
                    continue
                token_similarity = _sequence_similarity(left_tokens, right_tokens)
                structure_similarity = _sequence_similarity(structure_cache[left], structure_cache[right])
                copied_body = token_similarity >= 0.75
                copied_structure = structure_similarity >= 0.95 and token_similarity >= 0.65
                if copied_body or copied_structure:
                    failures.append(f'{domain}/{scene_id}: {left.name} and {right.name} look like duplicated task bodies (tokens={min_tokens}, token_similarity={token_similarity:.3f}, structure_similarity={structure_similarity:.3f})')
    assert not failures, '\n'.join(failures[:80])

def test_review_candidate_scene_source_files_are_not_duplicate_within_scene() -> None:
    """Detect copied code across public files, shared files, and public/shared boundaries."""
    failures: list[str] = []
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        for scene_id in sorted(scenes):
            source_files = _scene_source_files(str(domain), str(scene_id))
            file_tokens = {path: _normalized_source_tokens(path.read_text(encoding='utf-8')) for path in source_files}
            file_fingerprints = {path: _token_fingerprint(tokens) for path, tokens in file_tokens.items() if len(tokens) >= 800}
            for index, left in enumerate(source_files):
                for right in source_files[index + 1:]:
                    left_fingerprint = file_fingerprints.get(left, frozenset())
                    right_fingerprint = file_fingerprints.get(right, frozenset())
                    if not left_fingerprint or not right_fingerprint:
                        continue
                    if not _similar_length(len(file_tokens[left]), len(file_tokens[right]), min_ratio=0.6):
                        continue
                    overlap = _fingerprint_overlap(left_fingerprint, right_fingerprint)
                    if overlap >= 0.75:
                        failures.append(f'{domain}/{scene_id}: {left.relative_to(REPO_ROOT)} and {right.relative_to(REPO_ROOT)} look duplicated (tokens={min(len(file_tokens[left]), len(file_tokens[right]))}, fingerprint_overlap={overlap:.3f})')
            units: list[tuple[Path, str, tuple[str, ...]]] = []
            for source_path in source_files:
                for unit_name, tokens in _normalized_source_units(source_path):
                    if len(tokens) >= 250:
                        units.append((source_path, unit_name, tokens))
            unit_fingerprints = [_token_fingerprint(tokens, window=10, max_size=160) for _source_path, _unit_name, tokens in units]
            for index, (left_path, left_name, left_tokens) in enumerate(units):
                for right_index in range(index + 1, len(units)):
                    right_path, right_name, right_tokens = units[right_index]
                    if left_path == right_path:
                        continue
                    left_fingerprint = unit_fingerprints[index]
                    right_fingerprint = unit_fingerprints[right_index]
                    if not left_fingerprint or not right_fingerprint:
                        continue
                    if not _similar_length(len(left_tokens), len(right_tokens), min_ratio=0.75):
                        continue
                    overlap = _fingerprint_overlap(left_fingerprint, right_fingerprint)
                    if overlap >= 0.82:
                        failures.append(f'{domain}/{scene_id}: {left_path.relative_to(REPO_ROOT)}::{left_name} and {right_path.relative_to(REPO_ROOT)}::{right_name} look duplicated (tokens={min(len(left_tokens), len(right_tokens))}, fingerprint_overlap={overlap:.3f})')
    assert not failures, '\n'.join(failures[:120])

def test_review_candidate_shared_module_names_are_not_public_task_or_query_names() -> None:
    failures: list[str] = []
    for (domain, scene_id), files in _review_candidate_task_files_by_scene().items():
        identities = _scene_public_identities(domain, scene_id, files)
        shared_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id) / 'shared'
        if not shared_dir.exists():
            continue
        for source_path in sorted(shared_dir.rglob('*.py')):
            if source_path.name == '__init__.py':
                continue
            stem = source_path.stem
            for identity in sorted(identities, key=len, reverse=True):
                if _shared_filename_matches_public_identity(stem, identity):
                    failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} is named after public identity {identity!r}; shared filenames must describe reusable roles')
                    break
    assert not failures, '\n'.join(failures[:120])

def test_review_candidate_scene_shared_modules_do_not_define_generate_methods() -> None:
    failures: list[str] = []
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        for scene_id in sorted(scenes):
            shared_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id) / 'shared'
            if not shared_dir.exists():
                continue
            for source_path in sorted(shared_dir.rglob('*.py')):
                if source_path.name == '__init__.py':
                    continue
                tree = ast.parse(source_path.read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'generate':
                        failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} defines generate() inside shared; public task files must own task generation')
    assert not failures, '\n'.join(failures[:120])

def test_review_candidate_scene_shared_modules_are_identity_free() -> None:
    failures: list[str] = []
    tasks_by_scene = _review_candidate_task_files_by_scene()
    for (domain, scene_id), files in tasks_by_scene.items():
        shared_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id) / 'shared'
        if not shared_dir.exists():
            continue
        task_ids = sorted((task_id for task_ids in files.values() for task_id in task_ids))
        task_class_names: list[str] = []
        for task_id in task_ids:
            cls = _task_registry()[task_id]
            task_class_names.append(str(cls.__name__))
        public_identities = _scene_public_identities(domain, scene_id, files)
        forbidden_literals = set(task_ids) | set(task_class_names) | {'supported_query_ids', 'register_task'}
        for source_path in sorted(shared_dir.rglob('*.py')):
            if source_path.name == '__init__.py':
                continue
            source = source_path.read_text(encoding='utf-8')
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    bad_targets = sorted(TASK_IDENTITY_CONSTANT_NAMES & _assignment_target_names(node))
                    if bad_targets:
                        failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} defines task/query identity constants {bad_targets}; public task files own those constants')
                    value_node = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
                    static_value = _static_string_value(value_node) if value_node is not None else None
                    if static_value in public_identities:
                        failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} assigns public identity string {static_value!r} inside shared')
                elif isinstance(node, ast.keyword) and node.arg == 'task_id':
                    static_value = _static_string_value(node.value)
                    if static_value in public_identities or (isinstance(node.value, ast.Name) and node.value.id in TASK_IDENTITY_CONSTANT_NAMES):
                        failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} passes public task identity through task_id= inside shared')
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and (node.value in forbidden_literals):
                    failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} contains identity string {node.value!r}')
                elif _static_string_value(node) in public_identities:
                    failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} contains public identity string expression {_static_string_value(node)!r}')
                elif isinstance(node, ast.Name) and node.id in forbidden_literals:
                    failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} references identity name {node.id!r}')
                elif isinstance(node, ast.Name) and node.id in TASK_IDENTITY_CONSTANT_NAMES:
                    failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} references task/query identity constant {node.id!r}')
                elif isinstance(node, ast.Attribute) and node.attr in forbidden_literals:
                    failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} references identity attribute {node.attr!r}')
    assert not failures, '\n'.join(failures[:100])

def test_review_candidate_private_scene_files_do_not_register_or_route_tasks() -> None:
    failures: list[str] = []
    identity_branch_names = {'task_id', 'public_task_id', 'query_id', 'objective_contract', 'task_name'}
    tasks_by_scene = _review_candidate_task_files_by_scene()
    for (domain, scene_id), files in tasks_by_scene.items():
        policy = scene_package_file_policy(str(domain))
        if policy is None:
            continue
        scene_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id)
        task_ids = sorted((task_id for task_ids in files.values() for task_id in task_ids))
        task_class_names = [str(_task_registry()[task_id].__name__) for task_id in task_ids]
        public_identities = _scene_public_identities(domain, scene_id, files)
        forbidden_literals = set(task_ids) | set(task_class_names)
        for filename in sorted(policy.allowed_private_scene_files):
            source_path = scene_dir / str(filename)
            if not source_path.exists():
                continue
            source = source_path.read_text(encoding='utf-8')
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name == 'register_task':
                            failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} imports register_task')
                elif isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, (ast.Assign, ast.AnnAssign)):
                            if 'task_id' in _assignment_target_names(item):
                                failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} defines task_id inside private scene class {node.name}')
                elif isinstance(node, ast.If):
                    for child in ast.walk(node.test):
                        if isinstance(child, ast.Name) and child.id in identity_branch_names:
                            failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} branches on identity variable {child.id!r}; private scene files may receive metadata but must not route objective behavior by identity')
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if node.value in forbidden_literals or node.value in public_identities:
                        failures.append(f'{domain}/{scene_id}: {source_path.relative_to(REPO_ROOT)} contains public identity literal {node.value!r}')
    assert not failures, '\n'.join(failures[:100])

def test_review_candidate_shared_modules_do_not_build_task_outputs() -> None:
    failures: list[str] = []
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        for scene_id in sorted(scenes):
            shared_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id) / 'shared'
            if not shared_dir.exists():
                continue
            for source_path in sorted(shared_dir.rglob('*.py')):
                if source_path.name == '__init__.py':
                    continue
                tree = ast.parse(source_path.read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name == 'TaskOutput':
                                failures.append(f'{source_path}: shared module imports TaskOutput')
                    elif isinstance(node, ast.Name) and node.id == 'TaskOutput':
                        failures.append(f'{source_path}:{node.lineno}: shared module references TaskOutput')
    assert not failures, '\n'.join(failures[:80])

def test_review_candidate_public_task_generators_are_not_thin_shared_wrappers() -> None:
    failures: list[str] = []
    identity_keywords = {'task_id', 'public_task_id', 'task_name', 'objective_contract', 'namespace_prefix'}
    for task_id, cls in _review_candidate_task_entries():
        parts = parse_public_task_id(task_id)
        source_path = Path(inspect.getsourcefile(cls) or '').resolve()
        source = source_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        shared_names = _shared_imported_names(source_path, tree, domain=parts.domain, scene_id=parts.scene_id)
        private_scene_names = _private_scene_imported_names(source_path, tree, domain=parts.domain, scene_id=parts.scene_id)
        shared_modules = _shared_import_modules(source_path, tree, domain=parts.domain, scene_id=parts.scene_id)
        suspicious_shared_import = any((any((fragment in module_name.rsplit('.', 1)[-1].lower() for fragment in ('runtime', 'builder', 'generator'))) for module_name in shared_modules))
        has_local_objective_hooks = _has_local_objective_hooks(tree, class_name=cls.__name__)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name != cls.__name__:
                continue
            generate = next((item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == 'generate'), None)
            if generate is None:
                failures.append(f'{task_id}: registered task class has no generate method')
                continue
            body = _meaningful_function_body(generate)
            shared_builder_vars: set[str] = set()
            for child in ast.walk(generate):
                if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                    continue
                value = child.value if isinstance(child, (ast.Assign, ast.AnnAssign)) else None
                if not isinstance(value, ast.Call):
                    continue
                call_name = _call_name(value.func)
                call_root = call_name.split('.', 1)[0]
                if call_root not in shared_names:
                    continue
                if not any((fragment in call_name.lower() for fragment in ('builder', 'runtime', 'generator'))):
                    continue
                for target_name in _assignment_target_names(child):
                    shared_builder_vars.add(str(target_name))
                    failures.append(f'{task_id}: generate() instantiates scene-shared task pipeline {call_name}; shared code may provide primitives, not task/runtime builders')
            for call in (item for item in ast.walk(generate) if isinstance(item, ast.Call)):
                call_name = _call_name(call.func)
                if '.' in call_name:
                    call_root, method_name = call_name.split('.', 1)
                    if call_root in shared_builder_vars and method_name == 'generate':
                        failures.append(f'{task_id}: generate() delegates to {call_name}; public task files must own sampling, answer binding, annotation binding, and TaskOutput construction')
                call_root = call_name.split('.', 1)[0]
                if call_root in shared_names and any((fragment in call_name.lower() for fragment in ('generate', 'runtime', 'builder'))):
                    failures.append(f'{task_id}: generate() calls scene-shared task pipeline {call_name}; shared helpers must be role primitives')
            if suspicious_shared_import and len(body) <= 8:
                failures.append(f'{task_id}: imports a runtime/builder/generator shared module and has a compact wrapper-like generate(); move objective logic into the public task file and split shared code by role')
            delegates_to_private_scene_lifecycle = len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Call) and (_call_name(body[0].value.func).split('.', 1)[0] in private_scene_names) and has_local_objective_hooks
            if len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Call) and (not delegates_to_private_scene_lifecycle):
                failures.append(f'{task_id}: generate() is a single return-call wrapper')
            if len(body) <= 3 and body and isinstance(body[-1], ast.Return) and isinstance(body[-1].value, ast.Call):
                call_name = _call_name(body[-1].value.func).lower()
                if any((fragment in call_name for fragment in ('generate', 'task_output', 'output'))):
                    failures.append(f'{task_id}: generate() delegates to {call_name} with almost no local ownership')
            for call in (item for item in ast.walk(generate) if isinstance(item, ast.Call)):
                call_root = _call_name(call.func).split('.', 1)[0]
                if call_root not in shared_names:
                    continue
                bad_keywords = sorted((str(keyword.arg) for keyword in call.keywords if keyword.arg is not None and str(keyword.arg) in identity_keywords))
                if bad_keywords:
                    failures.append(f'{task_id}: generate() passes identity/routing keywords {bad_keywords} to scene shared helper {_call_name(call.func)}')
    assert not failures, '\n'.join(failures[:80])

def test_review_candidate_scene_packages_do_not_define_local_prompt_query_spec_helpers() -> None:
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        for scene_id in sorted(scenes):
            scene_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id)
            assert scene_dir.exists()
            for source_path in sorted(scene_dir.rglob('*.py')):
                tree = ast.parse(source_path.read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == '_prompt_query_spec':
                        raise AssertionError(f'{source_path} defines local _prompt_query_spec; use trace.tasks.shared.prompt_variants.build_prompt_query_spec')

def test_review_candidate_scene_packages_delegate_query_selection_policy() -> None:
    low_level_query_selection_names = {'explicit_query_id_param', 'probability_map', 'resolve_task_query_id_param', 'strip_query_id_params', 'spawn_rng'}
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        for scene_id in sorted(scenes):
            scene_dir = REPO_ROOT / 'trace' / 'tasks' / str(domain) / str(scene_id)
            assert scene_dir.exists()
            for source_path in sorted(scene_dir.rglob('*.py')):
                source = source_path.read_text(encoding='utf-8')
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    lowered_name = str(node.name).lower()
                    if 'select' not in lowered_name or 'query' not in lowered_name:
                        continue
                    segment = ast.get_source_segment(source, node) or ''
                    assert 'select_task_query_id' in segment, f'{source_path}:{node.lineno} defines query selection policy locally; delegate to trace.tasks.shared.fixed_query.select_task_query_id'
                    called_names = {call.func.id for call in ast.walk(node) if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)}
                    forbidden = sorted(low_level_query_selection_names & called_names)
                    assert not forbidden, f'{source_path}:{node.lineno} reimplements query selection with {forbidden}; delegate to trace.tasks.shared.fixed_query.select_task_query_id'
                    referenced_names = {name.id for name in ast.walk(node) if isinstance(name, ast.Name)}
                    assert '_sample_cursor' not in segment and 'sample_cursor' not in referenced_names, f'{source_path}:{node.lineno} handles query cursor cycling locally; delegate to trace.tasks.shared.fixed_query.select_task_query_id'

@pytest.mark.parametrize(('task_id', 'cls', 'query_id', 'instance_seed'), _review_candidate_task_query_entries())
def test_review_candidate_scene_packages_smoke_generate_each_supported_query(task_id: str, cls: type[Any], query_id: str, instance_seed: int) -> None:
    assert query_id, f'{task_id} must declare non-empty supported_query_ids'
    task = cls()
    output = task.generate(int(instance_seed), params={'query_id': str(query_id)}, max_attempts=512)
    assert output.query_id == str(query_id)
    assert output.answer_gt is not None
    assert output.annotation_gt is not None
    trace_payload = output.trace_payload if isinstance(output.trace_payload, dict) else {}
    query_spec = trace_payload.get('query_spec')
    assert isinstance(query_spec, dict)
    assert query_spec.get('query_id') == str(query_id)
    params = query_spec.get('params')
    assert isinstance(params, dict)
    assert params.get('query_id') == str(query_id)

def test_review_candidate_scenes_are_structurally_routed() -> None:
    pilot_scenes = {(parts.domain, parts.scene_id) for task_id in SCENE_PACKAGE_PILOT_TASK_IDS for parts in (parse_public_task_id(task_id),)}
    for domain, scenes in sorted(_scene_package_review_target_scenes().items()):
        for scene_id in sorted(scenes):
            assert is_scene_package_migrated_scene(domain, scene_id) or (domain, scene_id) in pilot_scenes

def test_scene_package_task_detects_no_scene_allowlist_after_reset() -> None:
    assert scene_package_migration.is_scene_package_task('task_charts__hexbin_density__threshold_bin_count', domain='charts')
    assert scene_package_migration.is_scene_package_task('task_icons__pair_grid__reference_color_pair_match_label', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__pair_grid__reference_transform_match_label', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__single_transform_options__geometric_transform_result_label', domain='icons')
    assert scene_package_migration.is_scene_package_task('task_icons__paired_canvas__panel_attribute_change_count', domain='icons')
