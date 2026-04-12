#!/usr/bin/env python3
"""Upload a local dataset artifact to a private Hugging Face dataset repo."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Local file to upload.")
    parser.add_argument("--repo-id", required=True, help="Target Hugging Face repo id.")
    parser.add_argument(
        "--path-in-repo",
        default="train.parquet",
        help="Target file path inside the dataset repo.",
    )
    parser.add_argument(
        "--repo-type",
        default="dataset",
        choices=("dataset", "model", "space"),
        help="Hugging Face repo type.",
    )
    parser.add_argument(
        "--private",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create the repo as private if it does not already exist.",
    )
    parser.add_argument(
        "--clean-repo",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Delete existing remote files before upload.",
    )
    parser.add_argument(
        "--commit-message",
        default="Upload dataset artifact",
        help="Commit message for the upload.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source).resolve()
    if not source.is_file():
        raise SystemExit(f"Source file not found: {source}")

    api = HfApi()
    api.create_repo(repo_id=args.repo_id, repo_type=args.repo_type, private=args.private, exist_ok=True)

    if args.clean_repo:
        repo_files = api.list_repo_files(repo_id=args.repo_id, repo_type=args.repo_type)
        if repo_files:
            api.delete_files(
                delete_patterns=repo_files,
                repo_id=args.repo_id,
                repo_type=args.repo_type,
                commit_message="Clean repo before upload",
            )

    result = api.upload_file(
        path_or_fileobj=str(source),
        path_in_repo=args.path_in_repo,
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        commit_message=args.commit_message,
    )
    print(
        "Uploaded dataset artifact:",
        f"source={source}",
        f"repo={args.repo_id}",
        f"path_in_repo={args.path_in_repo}",
        f"url={result}",
    )


if __name__ == "__main__":
    main()
