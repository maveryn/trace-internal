#!/usr/bin/env python3
"""Upload TRACE external eval subset manifests to Hugging Face Hub."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from huggingface_hub import HfApi


DEFAULT_REPO_ID = "maveryn/trace-external-eval-subsets"
DEFAULT_TOKEN_FILE = "hf-token.txt"
DEFAULT_SUBSET_ROOT = Path("benchmark/subsets/external_eval_v1")
EXPECTED_BENCHMARKS = {
    "chartqapro",
    "charxivreason",
    "mathvista",
    "mmmu_pro_vision",
    "countqa",
    "game_qa_lite",
    "blink",
    "screenspotpro",
}


def _read_token(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError(f"HF token file is empty: {path}")
    if not token.startswith("hf_"):
        raise RuntimeError(f"HF token file does not look like an HF token: {path}")
    return token


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _validate_subset_root(root: Path) -> dict:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("subset_version") != "external_eval_v1":
        raise RuntimeError(f"Unexpected subset version in {manifest_path}: {manifest.get('subset_version')}")
    keys = {item.get("benchmark_key") for item in manifest.get("benchmarks", [])}
    if keys != EXPECTED_BENCHMARKS:
        raise RuntimeError(f"Unexpected benchmark keys: {sorted(keys)}")
    total = 0
    for item in manifest["benchmarks"]:
        path = root / item["manifest"]
        rows = _read_jsonl(path)
        selected = int(item["selected_rows"])
        if len(rows) != selected:
            raise RuntimeError(f"{path} has {len(rows)} rows, expected {selected}")
        if selected != 1000:
            raise RuntimeError(f"{path} has {selected} selected rows, expected 1000")
        unique_keys = {
            (str(row.get("subset_key") or item["benchmark_key"]), str(row["source_index"]))
            for row in rows
        }
        if len(unique_keys) != selected:
            raise RuntimeError(f"{path} has duplicate source row identifiers")
        total += selected
    if int(manifest.get("total_selected_rows", -1)) != total:
        raise RuntimeError(f"Manifest total mismatch: {manifest.get('total_selected_rows')} vs {total}")
    print(f"[check] {root}: benchmarks={len(keys)} rows={total}")
    return manifest


def _write_dataset_card(path: Path, manifest: dict) -> None:
    path.write_text(
        f"""---
pretty_name: TRACE External Eval Subsets
language:
- en
license: other
tags:
- trace
- external-eval
- benchmark-subsets
---

# TRACE External Eval Subsets

Private manifest-only benchmark subsets for TRACE RLVR checkpoint comparison.

This repository stores source indices and hashes only. It does not redistribute
benchmark images or media.

## external_eval_v1

- Seed: `{manifest['sample_seed']}`
- Rows per benchmark: `{manifest['sample_count_per_benchmark']}`
- Total rows: `{manifest['total_selected_rows']}`

Benchmarks:

`chartqapro`, `charxivreason`, `mathvista`, `mmmu_pro_vision`, `countqa`,
`game_qa_lite`, `blink`, and pooled `screenspotpro`.

The TRACE repo documents the run workflow in
`docs/workflows/EXTERNAL_BENCHMARK_EVAL.md`.
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--token-file", default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--subset-root", type=Path, default=DEFAULT_SUBSET_ROOT)
    parser.add_argument("--revision", default="main")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-readme", action="store_true")
    parser.add_argument("--commit-message", default="Upload TRACE external eval subset v1 manifests")
    args = parser.parse_args()

    token = _read_token(Path(args.token_file))
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
    manifest = _validate_subset_root(args.subset_root)

    card_path = Path(".tmp/hf_trace_external_eval_subsets_readme.md")
    card_path.parent.mkdir(parents=True, exist_ok=True)
    _write_dataset_card(card_path, manifest)

    print(f"[repo] dataset {args.repo_id} private=True revision={args.revision}")
    if args.dry_run:
        print(f"[dry-run] would upload {args.subset_root} -> subsets/external_eval_v1")
        if not args.skip_readme:
            print(f"[dry-run] would upload {card_path} -> README.md")
        return 0

    api = HfApi(token=token)
    whoami = api.whoami()
    print(f"[auth] user={whoami.get('name')}")
    api.create_repo(
        repo_id=args.repo_id,
        repo_type="dataset",
        private=True,
        exist_ok=True,
        token=token,
    )
    if not args.skip_readme:
        print(f"[upload] {card_path} -> {args.repo_id}/README.md")
        api.upload_file(
            path_or_fileobj=card_path,
            path_in_repo="README.md",
            repo_id=args.repo_id,
            repo_type="dataset",
            revision=args.revision,
            token=token,
            commit_message=args.commit_message,
        )
    print(f"[upload] {args.subset_root} -> {args.repo_id}/subsets/external_eval_v1")
    api.upload_folder(
        folder_path=args.subset_root,
        path_in_repo="subsets/external_eval_v1",
        repo_id=args.repo_id,
        repo_type="dataset",
        revision=args.revision,
        token=token,
        commit_message=args.commit_message,
    )
    print("[done]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
