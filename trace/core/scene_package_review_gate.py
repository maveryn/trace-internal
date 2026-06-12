"""Pre-review source checks for scene-package candidates.

These checks run before task-review artifacts are written. They are intentionally
stricter than a manual status flag: a scene can be listed for review only after
the source has no obvious wrapper/copy-split public task files.
"""

from __future__ import annotations

import ast
from collections import defaultdict
import difflib
import inspect
import io
from pathlib import Path
import re
import token
import tokenize
from typing import Any

from trace.core.scene_package_migration import (
    is_scene_package_review_target_scene,
    parse_public_task_id,
)


PUBLIC_TASK_DUPLICATION_MIN_TOKENS = 400
PUBLIC_TASK_DUPLICATION_TOKEN_SIMILARITY = 0.75
PUBLIC_TASK_DUPLICATION_STRUCTURE_SIMILARITY = 0.95
PUBLIC_TASK_DUPLICATION_STRUCTURE_TOKEN_SIMILARITY = 0.65
_PUBLIC_TASK_ID_RE = re.compile(r"^task_[a-z0-9_]+__[a-z0-9_]+__[a-z0-9_]+$")
_FORBIDDEN_SHARED_IDENTIFIER_NAMES = {
    "task_id",
    "query_id",
    "supported_query_ids",
    "objective_contract",
    "namespace_prefix",
    "runtime_key",
    "selected_query",
    "query_params",
}
_FORBIDDEN_SHARED_STRING_CONSTANTS = {
    "query_id",
    "task_id",
    "supported_query_ids",
    "objective_contract",
}


def _task_registry(*, domain: str | None = None, scene_id: str | None = None) -> dict[str, type[Any]]:
    from trace.tasks.registry import TASK_REGISTRY, ensure_all_tasks_registered, ensure_scene_tasks_registered

    if domain is not None and scene_id is not None:
        ensure_scene_tasks_registered(str(domain), str(scene_id))
        return TASK_REGISTRY
    ensure_all_tasks_registered()
    return TASK_REGISTRY


def review_candidate_task_files_by_scene(domain: str, scene_id: str) -> dict[Path, list[str]]:
    """Return active public task files for one scene-package review candidate."""

    grouped: dict[Path, list[str]] = defaultdict(list)
    for task_id, cls in sorted(dict.items(_task_registry(domain=domain, scene_id=scene_id))):
        try:
            parts = parse_public_task_id(str(task_id))
        except ValueError:
            continue
        if parts.domain != str(domain) or parts.scene_id != str(scene_id):
            continue
        source_path = Path(inspect.getsourcefile(cls) or "").resolve()
        grouped[source_path].append(str(task_id))
    return {path: sorted(task_ids) for path, task_ids in sorted(grouped.items())}


def _normalized_source_tokens(source: str) -> tuple[str, ...]:
    normalized: list[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in {
            token.ENCODING,
            token.ENDMARKER,
            token.INDENT,
            token.DEDENT,
            token.NEWLINE,
            token.NL,
            token.COMMENT,
        }:
            continue
        if tok.type == token.STRING:
            normalized.append("STR")
        elif tok.type == token.NUMBER:
            normalized.append("NUM")
        else:
            normalized.append(tok.string)
    return tuple(normalized)


def _normalized_public_task_tokens(source_path: Path) -> tuple[str, ...]:
    return _normalized_source_tokens(source_path.read_text(encoding="utf-8"))


def _top_level_structure_signature(source_path: Path) -> tuple[str, ...]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    signature: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            method_names = [
                item.name
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            signature.append(
                "class:"
                f"bases={len(node.bases)}:"
                f"decorators={len(node.decorator_list)}:"
                f"methods={','.join(method_names)}"
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            signature.append(f"function:{node.name}:args={len(node.args.args)}:body={len(node.body)}")
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            signature.append(type(node).__name__)
        elif isinstance(node, ast.ImportFrom):
            signature.append(f"importfrom:{node.level}:{node.module or ''}")
        elif isinstance(node, ast.Import):
            signature.append("import")
        else:
            signature.append(type(node).__name__)
    return tuple(signature)


def _scene_dir(domain: str, scene_id: str) -> Path:
    return Path("trace") / "tasks" / str(domain) / str(scene_id)


def _sequence_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    return difflib.SequenceMatcher(a=left, b=right, autojunk=False).ratio()


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


def _shared_identity_failures(*, domain: str, scene_id: str, task_ids: set[str]) -> list[str]:
    shared_dir = _scene_dir(domain, scene_id) / "shared"
    if not shared_dir.exists():
        return []

    failures: list[str] = []
    for path in sorted(shared_dir.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if "for_query" in node.name or "for_objective" in node.name:
                    failures.append(f"{domain}/{scene_id}: {path}:{node.lineno} routes by identity in {node.name!r}")
                for arg in list(node.args.args) + list(node.args.kwonlyargs):
                    if arg.arg in _FORBIDDEN_SHARED_IDENTIFIER_NAMES:
                        failures.append(
                            f"{domain}/{scene_id}: {path}:{arg.lineno} argument {arg.arg!r} is public identity"
                        )
            elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_SHARED_IDENTIFIER_NAMES:
                failures.append(f"{domain}/{scene_id}: {path}:{node.lineno} identifier {node.id!r} is public identity")
            elif isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_SHARED_IDENTIFIER_NAMES:
                failures.append(
                    f"{domain}/{scene_id}: {path}:{node.lineno} attribute {node.attr!r} is public identity"
                )
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for target_name in _assignment_target_names(node):
                    if "QUERY" in target_name and "ID" in target_name:
                        failures.append(
                            f"{domain}/{scene_id}: {path}:{node.lineno} query-id table {target_name!r} "
                            "is not shared code"
                        )
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = str(node.value)
                if value in task_ids or _PUBLIC_TASK_ID_RE.match(value):
                    failures.append(f"{domain}/{scene_id}: {path}:{node.lineno} public task id string in shared code")
                if value in _FORBIDDEN_SHARED_STRING_CONSTANTS:
                    failures.append(
                        f"{domain}/{scene_id}: {path}:{node.lineno} public identity string {value!r} in shared code"
                    )
    return failures


def audit_scene_package_review_candidate(domain: str, scene_id: str) -> dict[str, Any]:
    """Return a fail-closed structural audit for one review-candidate scene."""

    domain = str(domain)
    scene_id = str(scene_id)
    failures: list[str] = []
    metrics: list[dict[str, Any]] = []

    if not is_scene_package_review_target_scene(domain, scene_id):
        failures.append(f"{domain}/{scene_id}: scene is not registered as a review candidate")
        return {
            "passed": False,
            "domain": domain,
            "scene_id": scene_id,
            "failures": failures,
            "metrics": metrics,
        }

    files = review_candidate_task_files_by_scene(domain, scene_id)
    if not files:
        failures.append(f"{domain}/{scene_id}: no active public task files found")
        return {
            "passed": False,
            "domain": domain,
            "scene_id": scene_id,
            "failures": failures,
            "metrics": metrics,
        }

    task_ids = {task_id for task_ids in files.values() for task_id in task_ids}
    failures.extend(_shared_identity_failures(domain=domain, scene_id=scene_id, task_ids=task_ids))

    public_files = sorted(files)
    token_cache = {path: _normalized_public_task_tokens(path) for path in public_files}
    structure_cache = {path: _top_level_structure_signature(path) for path in public_files}
    for index, left in enumerate(public_files):
        for right in public_files[index + 1 :]:
            left_tokens = token_cache[left]
            right_tokens = token_cache[right]
            min_tokens = min(len(left_tokens), len(right_tokens))
            if min_tokens < PUBLIC_TASK_DUPLICATION_MIN_TOKENS:
                continue
            token_similarity = _sequence_similarity(left_tokens, right_tokens)
            structure_similarity = _sequence_similarity(structure_cache[left], structure_cache[right])
            copied_body = token_similarity >= PUBLIC_TASK_DUPLICATION_TOKEN_SIMILARITY
            copied_structure = (
                structure_similarity >= PUBLIC_TASK_DUPLICATION_STRUCTURE_SIMILARITY
                and token_similarity >= PUBLIC_TASK_DUPLICATION_STRUCTURE_TOKEN_SIMILARITY
            )
            metric = {
                "left": left.name,
                "right": right.name,
                "min_tokens": min_tokens,
                "token_similarity": round(float(token_similarity), 6),
                "structure_similarity": round(float(structure_similarity), 6),
                "failed": bool(copied_body or copied_structure),
            }
            metrics.append(metric)
            if copied_body or copied_structure:
                failures.append(
                    f"{domain}/{scene_id}: {left.name} and {right.name} look like duplicated "
                    "public task bodies "
                    f"(tokens={min_tokens}, token_similarity={token_similarity:.3f}, "
                    f"structure_similarity={structure_similarity:.3f})"
                )

    return {
        "passed": not failures,
        "domain": domain,
        "scene_id": scene_id,
        "failures": failures,
        "metrics": metrics,
    }
