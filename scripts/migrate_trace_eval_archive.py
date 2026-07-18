#!/usr/bin/env python3
"""Safely split and migrate the pinned TRACE evaluation archive.

No command deletes data or changes visibility unless its dedicated allow flag
and exact typed confirmation are both present.  Run ``inventory``, ``adopt``
(or ``backup``), ``plan``, the two uploads, and ``verify`` before considering
either destructive command.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

try:
    from scripts.trace_eval_archive_migration_lib import (
        DEFAULT_INTERNAL_REPO,
        DEFAULT_PAPER_REPO,
        DEFAULT_SOURCE_REPO,
        DEFAULT_SOURCE_REVISION,
        adopt_snapshot,
        build_selection_plan,
        capture_source_inventory,
        create_or_resume_backup,
        delete_old_repository,
        load_selection_plan,
        load_verified_public_export,
        promote_paper_repository,
        read_token_file,
        upload_internal_archive,
        upload_paper_export,
        upload_paper_run,
        verify_backup,
        verify_migration,
    )
except ModuleNotFoundError:  # Supports direct ``python scripts/...`` invocation.
    from trace_eval_archive_migration_lib import (
        DEFAULT_INTERNAL_REPO,
        DEFAULT_PAPER_REPO,
        DEFAULT_SOURCE_REPO,
        DEFAULT_SOURCE_REVISION,
        adopt_snapshot,
        build_selection_plan,
        capture_source_inventory,
        create_or_resume_backup,
        delete_old_repository,
        load_selection_plan,
        load_verified_public_export,
        promote_paper_repository,
        read_token_file,
        upload_internal_archive,
        upload_paper_export,
        upload_paper_run,
        verify_backup,
        verify_migration,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_ROOT = Path(
    os.environ.get(
        "TRACE_EVAL_MIGRATION_STATE_ROOT",
        Path.home() / ".local" / "share" / "trace" / "eval-migration",
    )
)
DEFAULT_TOKEN_FILE = Path(os.environ.get("HF_TOKEN_FILE", REPO_ROOT / "hf-token.txt"))
DEFAULT_SUITE = REPO_ROOT / "evaluation" / "trace_eval" / "suite.v1.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--source-repo", default=DEFAULT_SOURCE_REPO)
    parser.add_argument("--source-revision", default=DEFAULT_SOURCE_REVISION)
    parser.add_argument("--paper-repo", default=DEFAULT_PAPER_REPO)
    parser.add_argument("--internal-repo", default=DEFAULT_INTERNAL_REPO)
    parser.add_argument("--revision", default="main")
    parser.add_argument("--batch-size", type=int, default=48)
    parser.add_argument(
        "--verbose-json",
        action="store_true",
        help="Print full sealed documents; by default large manifests are summarized.",
    )
    parser.add_argument(
        "--public-export-plan",
        type=Path,
        help="Private exporter plan/crosswalk; uploaded only to the internal repository.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("inventory", help="Pin the old private repository tree and refs.")
    commands.add_parser("backup", help="Download or resume the complete source backup.")
    adopt = commands.add_parser(
        "adopt", help="Hash and seal an existing snapshot_download tree without copying it."
    )
    adopt.add_argument("--snapshot-root", type=Path, required=True)
    commands.add_parser("verify-backup", help="Rehash and verify the complete local backup.")
    plan = commands.add_parser("plan", help="Select the canonical 648/189 stage identities.")
    plan.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    public = commands.add_parser(
        "validate-public", help="Validate a prepared neutral 648-artifact public export."
    )
    public.add_argument("--public-export-root", type=Path, required=True)
    commands.add_parser(
        "upload-internal", help="Idempotently upload the 189 lossless supplementary slices."
    )
    upload_public = commands.add_parser(
        "upload-paper", help="Idempotently upload the neutral paper export to a private repo."
    )
    upload_public.add_argument("--public-export-root", type=Path, required=True)
    upload_run = commands.add_parser(
        "upload-paper-run",
        help=(
            "Guardedly append one verified, explicitly allowlisted canonical or "
            "TRACE IID run to the paper repository."
        ),
    )
    upload_run.add_argument("--public-export-root", type=Path, required=True)
    upload_run.add_argument("--allow-paper-run-upload", action="store_true")
    upload_run.add_argument("--confirm-paper-run")
    migrate = commands.add_parser(
        "migrate", help="Upload both private destinations and write a verification receipt."
    )
    migrate.add_argument("--public-export-root", type=Path, required=True)
    verify = commands.add_parser(
        "verify", help="Verify source, backup, coverage, disjointness, and remote hashes."
    )
    verify.add_argument("--public-export-root", type=Path, required=True)

    delete = commands.add_parser(
        "delete-old", help="Delete the old repo only after a fresh complete verification."
    )
    delete.add_argument("--public-export-root", type=Path, required=True)
    delete.add_argument("--allow-delete-old-repo", action="store_true")
    delete.add_argument("--confirm-delete")

    promote = commands.add_parser(
        "promote-paper-public",
        help="Make the neutral paper repo public only after a fresh complete verification.",
    )
    promote.add_argument("--public-export-root", type=Path, required=True)
    promote.add_argument("--allow-public", action="store_true")
    promote.add_argument("--confirm-public")
    return parser


def _paths(args: argparse.Namespace) -> dict[str, Path]:
    root = args.state_root
    return {
        "inventory": root / "source-inventory.json",
        "backup": root,
        "plan": root / "selection-plan.json",
        "receipt": root / "verification-receipt.json",
    }


def _api(args: argparse.Namespace) -> tuple[HfApi, str]:
    token = read_token_file(args.token_file)
    return HfApi(token=token), token


def _required_public_export_plan(args: argparse.Namespace) -> Path:
    if args.public_export_plan is None:
        raise ValueError("--public-export-plan is required for this command")
    return args.public_export_plan


def _summary(value: object) -> object:
    if not isinstance(value, dict):
        return value
    schema = value.get("schema_version")
    if schema == "trace-eval-archive-inventory-v1":
        return {
            "schema_version": schema,
            "inventory_sha256": value.get("inventory_sha256"),
            "source": value.get("source"),
            "file_count": value.get("file_count"),
            "refs": {key: len(items) for key, items in value.get("refs", {}).items()},
        }
    if schema == "trace-eval-archive-backup-v1":
        return {
            "schema_version": schema,
            "backup_manifest_sha256": value.get("backup_manifest_sha256"),
            "inventory_sha256": value.get("inventory_sha256"),
            "complete": value.get("complete"),
            "file_count": value.get("file_count"),
            "storage": value.get("storage"),
        }
    if schema == "trace-eval-archive-selection-v1":
        return {
            "schema_version": schema,
            "selection_sha256": value.get("selection_sha256"),
            "source": value.get("source"),
            "suite": value.get("suite"),
            "paper": {
                "repo_id": value.get("paper", {}).get("repo_id"),
                "benchmarks": len(value.get("paper", {}).get("benchmarks", [])),
                "stage_slices": value.get("paper", {}).get("stage_slice_count"),
                "source_slice_set_sha256": value.get("paper", {}).get(
                    "source_slice_set_sha256"
                ),
            },
            "internal": {
                "repo_id": value.get("internal", {}).get("repo_id"),
                "benchmarks": len(value.get("internal", {}).get("benchmarks", [])),
                "stage_slices": value.get("internal", {}).get("stage_slice_count"),
            },
        }
    if schema == "trace-eval-archive-verification-v1":
        return {
            "schema_version": schema,
            "verification_sha256": value.get("verification_sha256"),
            "source_repo_id": value.get("source_repo_id"),
            "source_commit": value.get("source_commit"),
            "paper": value.get("paper"),
            "internal": value.get("internal"),
            "coverage": value.get("coverage"),
        }
    return value


def _print(value: object, *, verbose: bool) -> None:
    print(json.dumps(value if verbose else _summary(value), indent=2, sort_keys=True, default=str))


def _verify(args: argparse.Namespace, *, api: HfApi, token: str) -> dict:
    paths = _paths(args)
    return verify_migration(
        api=api,
        inventory_path=paths["inventory"],
        backup_root=paths["backup"],
        plan_path=paths["plan"],
        public_export_root=args.public_export_root,
        state_root=args.state_root,
        output=paths["receipt"],
        token=token,
        revision=args.revision,
        public_export_plan=args.public_export_plan,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    paths = _paths(args)
    token: str | None = None
    try:
        if args.command == "inventory":
            api, token = _api(args)
            result = capture_source_inventory(
                api=api,
                source_repo_id=args.source_repo,
                source_revision=args.source_revision,
                output=paths["inventory"],
                token=token,
            )
        elif args.command == "backup":
            api, token = _api(args)
            result = create_or_resume_backup(
                api=api,
                inventory_path=paths["inventory"],
                backup_root=paths["backup"],
                token=token,
            )
        elif args.command == "adopt":
            result = adopt_snapshot(
                inventory_path=paths["inventory"],
                snapshot_root=args.snapshot_root,
                backup_root=paths["backup"],
            )
        elif args.command == "verify-backup":
            result = verify_backup(
                inventory_path=paths["inventory"], backup_root=paths["backup"]
            )
        elif args.command == "plan":
            result = build_selection_plan(
                inventory_path=paths["inventory"],
                backup_root=paths["backup"],
                suite_path=args.suite,
                output=paths["plan"],
                public_export_plan=_required_public_export_plan(args),
                paper_repo_id=args.paper_repo,
                internal_repo_id=args.internal_repo,
            )
        elif args.command == "validate-public":
            plan = load_selection_plan(paths["plan"])
            verified, files = load_verified_public_export(
                root=args.public_export_root,
                plan=plan,
                public_export_plan=_required_public_export_plan(args),
            )
            result = {
                "manifest_sha256": verified.manifest_sha256,
                "stage_slices": len(verified.manifest["artifacts"]),
                "files": len(files),
                "neutralized": True,
            }
        elif args.command == "upload-internal":
            api, token = _api(args)
            result = upload_internal_archive(
                api=api,
                plan_path=paths["plan"],
                backup_root=paths["backup"],
                state_root=args.state_root,
                token=token,
                revision=args.revision,
                batch_size=args.batch_size,
                public_export_plan=args.public_export_plan,
            )
        elif args.command == "upload-paper":
            api, token = _api(args)
            result = upload_paper_export(
                api=api,
                plan_path=paths["plan"],
                public_export_root=args.public_export_root,
                public_export_plan=_required_public_export_plan(args),
                state_root=args.state_root,
                token=token,
                revision=args.revision,
                batch_size=args.batch_size,
            )
        elif args.command == "upload-paper-run":
            api, token = _api(args)
            result = upload_paper_run(
                api=api,
                repo_id=args.paper_repo,
                public_export_root=args.public_export_root,
                public_export_plan=_required_public_export_plan(args),
                state_root=args.state_root,
                token=token,
                allow_upload=args.allow_paper_run_upload,
                confirmation=args.confirm_paper_run,
                revision=args.revision,
                batch_size=args.batch_size,
            )
        elif args.command == "migrate":
            public_export_plan = _required_public_export_plan(args)
            api, token = _api(args)
            internal = upload_internal_archive(
                api=api,
                plan_path=paths["plan"],
                backup_root=paths["backup"],
                state_root=args.state_root,
                token=token,
                revision=args.revision,
                batch_size=args.batch_size,
                public_export_plan=public_export_plan,
            )
            paper = upload_paper_export(
                api=api,
                plan_path=paths["plan"],
                public_export_root=args.public_export_root,
                public_export_plan=public_export_plan,
                state_root=args.state_root,
                token=token,
                revision=args.revision,
                batch_size=args.batch_size,
            )
            receipt = _verify(args, api=api, token=token)
            result = {"internal_upload": internal, "paper_upload": paper, "receipt": receipt}
        elif args.command == "verify":
            api, token = _api(args)
            result = _verify(args, api=api, token=token)
        elif args.command == "delete-old":
            api, token = _api(args)
            receipt = _verify(args, api=api, token=token)
            delete_old_repository(
                api=api,
                source_repo_id=args.source_repo,
                token=token,
                allow_delete=args.allow_delete_old_repo,
                confirmation=args.confirm_delete,
                verified_source_repo_id=receipt["source_repo_id"],
                verified_source_commit=receipt["source_commit"],
                verified_source_refs=receipt["source_refs"],
                verified_paper_repo_id=receipt["paper"]["repo_id"],
                verified_paper_revision=receipt["paper"]["revision"],
                verified_internal_repo_id=receipt["internal"]["repo_id"],
                verified_internal_revision=receipt["internal"]["revision"],
            )
            result = {
                "deleted": args.source_repo,
                "verification_sha256": receipt["verification_sha256"],
            }
        elif args.command == "promote-paper-public":
            api, token = _api(args)
            receipt = _verify(args, api=api, token=token)
            plan = load_selection_plan(paths["plan"])
            promote_paper_repository(
                api=api,
                repo_id=args.paper_repo,
                plan=plan,
                token=token,
                allow_public=args.allow_public,
                confirmation=args.confirm_public,
                verified_revision=receipt["paper"]["revision"],
                verified_other_runs=receipt["paper"].get("other_runs", []),
            )
            result = {
                "public": args.paper_repo,
                "verification_sha256": receipt["verification_sha256"],
            }
        else:  # pragma: no cover - argparse enforces a known command.
            raise AssertionError(args.command)
        _print(result, verbose=args.verbose_json)
        return 0
    except Exception as error:
        message = str(error)
        if token:
            message = message.replace(token, "<redacted>")
        print(f"migration error: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
