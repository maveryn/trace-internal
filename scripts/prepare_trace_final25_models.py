#!/usr/bin/env python3
"""Download pinned public Final25 models and register immutable local merges."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from huggingface_hub import HfApi, snapshot_download


MARKER_NAME = ".trace_model_revision.json"


@dataclass(frozen=True)
class PublicModel:
    slug: str
    repo_id: str
    revision: str
    target_name: str


PUBLIC_MODELS = (
    PublicModel(
        "qwen25vl3b-base",
        "Qwen/Qwen2.5-VL-3B-Instruct",
        "66285546d2b821cf421d4f5eb2576359d3770cd3",
        "qwen25vl3b-base",
    ),
    PublicModel(
        "qwen25vl7b-base",
        "Qwen/Qwen2.5-VL-7B-Instruct",
        "cc594898137f460bfe9f0759e9844b3ce807cfb5",
        "qwen25vl7b-base",
    ),
    PublicModel(
        "game-rl-qwen25vl7b",
        "OpenMOSS-Team/Game-RL-Qwen2.5-VL-7B",
        "205b5934ce70504cfd6ae26b16f705d0b98b9306",
        "game-rl-qwen25vl7b",
    ),
    PublicModel(
        "sphinx-qwen7b-500",
        "xashru/sphinx_qwen7b_500",
        "6ffefb03d5cb0767683bfb42a084ea86b707ef9a",
        "sphinx-qwen7b-500",
    ),
    PublicModel(
        "pcgrpo-qwen25vl7b-jigsaw-care",
        "armenjeddi/PCGRPO-Qwen2.5-VL-7B-Jigsaw-with-curriculum-with-grpo-care",
        "921bbced4176f5d362e98c843a57656c5d78dad7",
        "pcgrpo-qwen25vl7b-jigsaw-care",
    ),
    PublicModel(
        "vero-qwen25-7b",
        "zlab-princeton/Vero-Qwen25-7B",
        "180e84be5acb2aa887cf51015b84b6a6e453ee90",
        "vero-qwen25-7b",
    ),
    PublicModel(
        "qwen3-32b-judge",
        "Qwen/Qwen3-32B",
        "9216db5781bf21249d130ec9da846c4624c16137",
        "qwen3-32b-judge",
    ),
)


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _model_files(path: Path) -> list[Path]:
    files = set(path.glob("*.safetensors"))
    files.update(path.glob("*.bin"))
    for name in (
        "config.json",
        "generation_config.json",
        "model.safetensors.index.json",
        "preprocessor_config.json",
        "processor_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
    ):
        candidate = path / name
        if candidate.is_file():
            files.add(candidate)
    return sorted(files, key=lambda item: item.name)


def _validate_model_shape(path: Path) -> None:
    if not (path / "config.json").is_file():
        raise RuntimeError(f"missing model config: {path / 'config.json'}")
    weights = list(path.glob("*.safetensors")) + list(path.glob("*.bin"))
    if not weights or any(item.stat().st_size == 0 for item in weights):
        raise RuntimeError(f"missing or empty model weights under {path}")


def _write_marker(path: Path, marker: dict[str, object]) -> None:
    target = path / MARKER_NAME
    temporary = target.with_suffix(f".tmp.{os.getpid()}")
    temporary.write_text(_canonical_json(marker) + "\n", encoding="utf-8")
    os.replace(temporary, target)


def _read_marker(path: Path) -> dict[str, object]:
    marker_path = path / MARKER_NAME
    if not marker_path.is_file():
        raise RuntimeError(
            f"missing model provenance marker: {marker_path}; download or register the model first"
        )
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if not isinstance(marker, dict):
        raise RuntimeError(f"invalid model provenance marker: {marker_path}")
    return marker


def _token(token_file: Path) -> str | None:
    if not token_file.exists():
        return None
    if stat.S_IMODE(token_file.stat().st_mode) & 0o077:
        raise RuntimeError(f"token file must have mode 600 or stricter: {token_file}")
    token = token_file.read_text(encoding="utf-8").strip()
    return token or None


def download_public(
    models: Iterable[PublicModel], model_root: Path, token_file: Path
) -> None:
    token = _token(token_file)
    api = HfApi(token=token)
    model_root.mkdir(parents=True, exist_ok=True)
    for model in models:
        info = api.model_info(model.repo_id, revision=model.revision, token=token)
        if str(info.sha) != model.revision:
            raise RuntimeError(
                f"{model.repo_id}@{model.revision} resolved to unexpected commit {info.sha}"
            )
        target = model_root / model.target_name
        print(f"[model:download] {model.repo_id}@{model.revision} -> {target}")
        snapshot_download(
            repo_id=model.repo_id,
            revision=model.revision,
            local_dir=target,
            token=token,
        )
        _validate_model_shape(target)
        _write_marker(
            target,
            {
                "schema_version": "trace-model-revision-v1",
                "slug": model.slug,
                "source": model.repo_id,
                "immutable_revision": model.revision,
                "resolved_commit": str(info.sha),
                "registered_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            },
        )


def register_local(slug: str, path: Path, source: str) -> str:
    _validate_model_shape(path)
    hashes = {item.name: _sha256_file(item) for item in _model_files(path)}
    fingerprint = hashlib.sha256(_canonical_json(hashes).encode("utf-8")).hexdigest()
    revision = f"sha256set:{fingerprint}"
    _write_marker(
        path,
        {
            "schema_version": "trace-model-revision-v1",
            "slug": slug,
            "source": source,
            "immutable_revision": revision,
            "file_sha256": hashes,
            "registered_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        },
    )
    print(f"[model:registered] slug={slug} revision={revision} path={path}")
    return revision


def parse_entry(value: str) -> tuple[str, Path, str]:
    parts = value.split("=", 2)
    if len(parts) != 3 or not all(part.strip() for part in parts):
        raise argparse.ArgumentTypeError("--entry must be slug=path=immutable_revision")
    return parts[0].strip(), Path(parts[1]).expanduser(), parts[2].strip()


def verify(entries: Iterable[tuple[str, Path, str]], deep: bool) -> None:
    for slug, path, expected_revision in entries:
        _validate_model_shape(path)
        marker = _read_marker(path)
        if marker.get("slug") != slug:
            raise RuntimeError(f"model marker slug mismatch for {path}: {marker.get('slug')} != {slug}")
        actual_revision = str(marker.get("immutable_revision") or "")
        if actual_revision != expected_revision:
            raise RuntimeError(
                f"model revision mismatch for {slug}: {actual_revision} != {expected_revision}"
            )
        if deep and isinstance(marker.get("file_sha256"), dict):
            for relative, expected_hash in marker["file_sha256"].items():
                candidate = path / str(relative)
                if not candidate.is_file() or _sha256_file(candidate) != expected_hash:
                    raise RuntimeError(f"model content hash mismatch: {candidate}")
        print(f"[model:ok] slug={slug} revision={actual_revision} path={path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download-public")
    download.add_argument("--model-root", type=Path, required=True)
    download.add_argument("--token-file", type=Path, default=Path("hf-token.txt"))
    download.add_argument("--only", action="append", default=[])
    register = commands.add_parser("register-local")
    register.add_argument("--slug", required=True)
    register.add_argument("--path", type=Path, required=True)
    register.add_argument("--source", required=True)
    check = commands.add_parser("verify")
    check.add_argument("--entry", action="append", type=parse_entry, required=True)
    check.add_argument("--deep", action="store_true")
    args = parser.parse_args()

    if args.command == "download-public":
        selected = set(args.only)
        models = [model for model in PUBLIC_MODELS if not selected or model.slug in selected]
        unknown = selected - {model.slug for model in PUBLIC_MODELS}
        if unknown:
            raise SystemExit(f"unknown public model slugs: {sorted(unknown)}")
        download_public(models, args.model_root, args.token_file)
    elif args.command == "register-local":
        register_local(args.slug, args.path, args.source)
    else:
        verify(args.entry, args.deep)


if __name__ == "__main__":
    main()
