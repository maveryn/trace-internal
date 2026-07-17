from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from huggingface_hub.errors import RepositoryNotFoundError

from scripts.trace_eval_archive_migration_lib import (
    BACKUP_SCHEMA,
    CANONICAL_MODELS,
    CANONICAL_RUN,
    CANONICAL_SEEDS,
    CANONICAL_STAGES,
    DEFAULT_INTERNAL_REPO,
    DEFAULT_PAPER_REPO,
    DEFAULT_SOURCE_REPO,
    EXPECTED_INTERNAL_STAGE_SLICES,
    EXPECTED_PAPER_STAGE_SLICES,
    INVENTORY_SCHEMA,
    MigrationIntegrityError,
    MigrationSafetyError,
    SUPPLEMENTARY_BENCHMARKS,
    _seal_document,
    adopt_snapshot,
    build_selection_plan,
    capture_source_inventory,
    delete_old_repository,
    internal_upload_files,
    load_verified_public_export,
    load_selection_plan,
    promote_paper_repository,
    sha256_bytes,
    upload_internal_archive,
    upload_paper_export,
    upload_paper_run,
    verify_backup,
    verify_migration,
)


SOURCE_COMMIT = "1" * 40
SOURCE_REFS = {
    "branches": [
        {"name": "main", "ref": "refs/heads/main", "target_commit": SOURCE_COMMIT}
    ],
    "converts": [],
    "tags": [],
    "pull_requests": [],
}


def _git_blob(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest()


class FakeApi:
    def __init__(self) -> None:
        self.repos: dict[str, dict] = {}
        self.created: list[str] = []
        self.deleted: list[str] = []
        self.publicized: list[str] = []
        self.head_override: str | None = None
        self.extra_branches: list[SimpleNamespace] = []

    def add_repo(self, repo_id: str, files: dict[str, bytes], *, private: bool, sha: str) -> None:
        self.repos[repo_id] = {
            "files": dict(files),
            "private": private,
            "sha": sha,
        }

    def repo_info(self, *, repo_id, revision, files_metadata, **_kwargs):
        if repo_id not in self.repos:
            raise RepositoryNotFoundError("synthetic missing repository")
        repo = self.repos[repo_id]
        sha = self.head_override if revision == "main" and self.head_override else repo["sha"]
        siblings = []
        if files_metadata:
            for path, content in sorted(repo["files"].items()):
                is_parquet = path.endswith(".parquet")
                siblings.append(
                    SimpleNamespace(
                        rfilename=path,
                        size=len(content),
                        lfs=(
                            SimpleNamespace(sha256=sha256_bytes(content))
                            if is_parquet
                            else None
                        ),
                        blob_id=None if is_parquet else _git_blob(content),
                    )
                )
        return SimpleNamespace(
            id=repo_id,
            private=repo["private"],
            sha=sha,
            siblings=siblings,
        )

    def list_repo_refs(self, **_kwargs):
        return SimpleNamespace(
            branches=[
                SimpleNamespace(
                    name="main", ref="refs/heads/main", target_commit=SOURCE_COMMIT
                )
            ]
            + self.extra_branches,
            converts=[],
            tags=[],
            pull_requests=[],
        )

    def hf_hub_download(self, *, repo_id, filename, local_dir, **_kwargs):
        destination = Path(local_dir) / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.repos[repo_id]["files"][filename])
        return str(destination)

    def create_repo(self, *, repo_id, private, **_kwargs):
        assert private is True
        self.add_repo(repo_id, {}, private=True, sha="0" * 40)
        self.created.append(repo_id)

    def create_commit(self, *, repo_id, operations, **_kwargs):
        repo = self.repos[repo_id]
        for operation in operations:
            repo["files"][operation.path_in_repo] = Path(operation.path_or_fileobj).read_bytes()
        repo["sha"] = hashlib.sha1(
            (repo["sha"] + "|" + "|".join(sorted(repo["files"]))).encode()
        ).hexdigest()
        return SimpleNamespace(oid=repo["sha"])

    def delete_repo(self, *, repo_id, **_kwargs):
        self.deleted.append(repo_id)
        del self.repos[repo_id]

    def update_repo_settings(self, *, repo_id, private, **_kwargs):
        self.repos[repo_id]["private"] = private
        self.publicized.append(repo_id)


def test_inventory_pins_private_source_and_detects_a_head_race(tmp_path: Path) -> None:
    api = FakeApi()
    api.add_repo(
        DEFAULT_SOURCE_REPO,
        {"README.md": b"private\n", "data/example.parquet": b"parquet"},
        private=True,
        sha=SOURCE_COMMIT,
    )
    output = tmp_path / "inventory.json"
    inventory = capture_source_inventory(
        api=api,
        source_repo_id=DEFAULT_SOURCE_REPO,
        source_revision="main",
        output=output,
        token="secret",
    )
    assert inventory["source"]["resolved_commit"] == SOURCE_COMMIT
    assert inventory["file_count"] == 2
    assert inventory["refs"]["branches"][0]["target_commit"] == SOURCE_COMMIT
    assert output.stat().st_mode & 0o777 == 0o600

    api.head_override = "2" * 40
    with pytest.raises(MigrationIntegrityError, match="different commit|changed while"):
        capture_source_inventory(
            api=api,
            source_repo_id=DEFAULT_SOURCE_REPO,
            source_revision="main",
            output=output,
            token="secret",
        )


def test_adopt_snapshot_hashes_in_place_and_detects_corruption(tmp_path: Path) -> None:
    api = FakeApi()
    files = {"README.md": b"private\n", "data/example.parquet": b"parquet"}
    api.add_repo(DEFAULT_SOURCE_REPO, files, private=True, sha=SOURCE_COMMIT)
    inventory_path = tmp_path / "source-inventory.json"
    capture_source_inventory(
        api=api,
        source_repo_id=DEFAULT_SOURCE_REPO,
        source_revision="main",
        output=inventory_path,
        token="secret",
    )
    snapshot = tmp_path / SOURCE_COMMIT / "snapshot"
    for name, content in files.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    cache = snapshot / ".cache" / "huggingface" / "download" / "README.metadata"
    cache.parent.mkdir(parents=True)
    cache.write_text("ignored")

    manifest = adopt_snapshot(
        inventory_path=inventory_path,
        snapshot_root=snapshot,
        backup_root=tmp_path,
    )
    assert manifest["complete"] is True
    assert manifest["storage"] == {
        "files_root": f"{SOURCE_COMMIT}/snapshot",
        "mode": "adopted_snapshot",
    }
    assert manifest["file_count"] == 2
    verify_backup(inventory_path=inventory_path, backup_root=tmp_path)
    repeated = adopt_snapshot(
        inventory_path=inventory_path,
        snapshot_root=snapshot,
        backup_root=tmp_path,
    )
    assert repeated["backup_manifest_sha256"] == manifest["backup_manifest_sha256"]

    (snapshot / "README.md").write_text("corrupt")
    with pytest.raises(MigrationIntegrityError, match="digest mismatch"):
        verify_backup(inventory_path=inventory_path, backup_root=tmp_path)


def _full_backup(tmp_path: Path) -> tuple[Path, Path, Path, tuple[str, ...]]:
    suite_source = Path("evaluation/trace_eval/suite.v1.json")
    suite = json.loads(suite_source.read_text())
    paper_benchmarks = tuple(item["key"] for item in suite["benchmarks"])
    all_benchmarks = paper_benchmarks + SUPPLEMENTARY_BENCHMARKS
    snapshot = tmp_path / "snapshot"
    source_files: list[dict] = []
    backup_files: list[dict] = []

    for stage in CANONICAL_STAGES:
        for model in CANONICAL_MODELS:
            for seed in CANONICAL_SEEDS:
                for benchmark in all_benchmarks:
                    identity = f"{stage}|{model}|{seed}|{benchmark}".encode()
                    parquet_content = b"PAR1" + identity
                    digest = sha256_bytes(parquet_content)
                    parquet = (
                        f"data/{stage}/run={CANONICAL_RUN}/model={model}/seed={seed}/"
                        f"benchmark={benchmark}/part-{digest}.parquet"
                    )
                    manifest = (
                        f"metadata/slices/{stage}/run={CANONICAL_RUN}/model={model}/seed={seed}/"
                        f"benchmark={benchmark}/part-{digest}.manifest.json"
                    )
                    manifest_content = json.dumps({"identity": identity.decode()}).encode()
                    for path, content in ((parquet, parquet_content), (manifest, manifest_content)):
                        local = snapshot / path
                        local.parent.mkdir(parents=True, exist_ok=True)
                        local.write_bytes(content)
                        content_sha = sha256_bytes(content)
                        source_files.append(
                            {
                                "path": path,
                                "size": len(content),
                                "lfs_sha256": content_sha,
                                "blob_id": None,
                            }
                        )
                        backup_files.append(
                            {"path": path, "size": len(content), "sha256": content_sha}
                        )

    # Historical content is backed up but must not enter either destination.
    historical_content = b"historical"
    historical_sha = sha256_bytes(historical_content)
    historical = (
        "data/generation/run=historical/model=old/seed=42/benchmark=chartqapro/"
        f"part-{historical_sha}.parquet"
    )
    local = snapshot / historical
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(historical_content)
    source_files.append(
        {
            "path": historical,
            "size": len(historical_content),
            "lfs_sha256": historical_sha,
            "blob_id": None,
        }
    )
    backup_files.append(
        {"path": historical, "size": len(historical_content), "sha256": historical_sha}
    )

    inventory = _seal_document(
        {
            "schema_version": INVENTORY_SCHEMA,
            "captured_at": "2026-07-16T00:00:00+00:00",
            "source": {
                "repo_id": DEFAULT_SOURCE_REPO,
                "repo_type": "dataset",
                "requested_revision": "main",
                "resolved_commit": SOURCE_COMMIT,
                "private": True,
            },
            "refs": {
                "branches": [
                    {"name": "main", "ref": "refs/heads/main", "target_commit": SOURCE_COMMIT}
                ],
                "converts": [],
                "tags": [],
                "pull_requests": [],
            },
            "file_count": len(source_files),
            "files": sorted(source_files, key=lambda item: item["path"]),
        },
        "inventory_sha256",
    )
    inventory_path = tmp_path / "source-inventory.json"
    inventory_path.write_text(json.dumps(inventory))
    backup = _seal_document(
        {
            "schema_version": BACKUP_SCHEMA,
            "updated_at": "2026-07-16T00:00:00+00:00",
            "complete": True,
            "inventory_sha256": inventory["inventory_sha256"],
            "source": inventory["source"],
            "refs": inventory["refs"],
            "storage": {"files_root": "snapshot", "mode": "adopted_snapshot"},
            "file_count": len(backup_files),
            "files": sorted(backup_files, key=lambda item: item["path"]),
        },
        "backup_manifest_sha256",
    )
    (tmp_path / "backup-manifest.json").write_text(json.dumps(backup))
    suite_path = tmp_path / "suite.json"
    suite_path.write_bytes(suite_source.read_bytes())
    return inventory_path, tmp_path, suite_path, paper_benchmarks


def test_plan_selects_only_canonical_648_and_189_stage_slices(tmp_path: Path) -> None:
    inventory, backup_root, suite, paper_benchmarks = _full_backup(tmp_path)
    plan_path = tmp_path / "selection-plan.json"
    plan, export_plan = _build_plan(
        inventory=inventory,
        backup_root=backup_root,
        suite=suite,
        output=plan_path,
    )
    assert plan["paper"]["stage_slice_count"] == EXPECTED_PAPER_STAGE_SLICES
    assert len(plan["paper"]["source_slice_set_sha256"]) == 64
    assert plan["internal"]["stage_slice_count"] == EXPECTED_INTERNAL_STAGE_SLICES
    assert set(plan["paper"]["benchmarks"]) == set(paper_benchmarks)
    assert set(plan["internal"]["benchmarks"]) == set(SUPPLEMENTARY_BENCHMARKS)
    assert all(
        item["identity"]["run"] == CANONICAL_RUN
        for group in (plan["paper"]["source_slices"], plan["internal"]["source_slices"])
        for item in group
    )
    assert "historical" not in plan_path.read_text()
    assert load_selection_plan(plan_path)["selection_sha256"] == plan["selection_sha256"]
    repeated = build_selection_plan(
        inventory_path=inventory,
        backup_root=backup_root,
        suite_path=suite,
        output=tmp_path / "selection-plan-repeated.json",
        public_export_plan=export_plan,
    )
    assert repeated["selection_sha256"] == plan["selection_sha256"]


def test_plan_rejects_an_alternate_24_benchmark_suite(tmp_path: Path) -> None:
    inventory, backup_root, suite, _ = _full_backup(tmp_path)
    altered = json.loads(suite.read_text())
    old_key = altered["benchmarks"][-1]["key"]
    altered["benchmarks"][-1]["key"] = "alternate_benchmark"
    for members in altered["categories"].values():
        if old_key in members:
            members[members.index(old_key)] = "alternate_benchmark"
    altered_suite = tmp_path / "alternate-suite.json"
    altered_suite.write_text(json.dumps(altered))
    export_plan = _private_export_plan(tmp_path, None, altered_suite)
    with pytest.raises(MigrationIntegrityError, match="differs from canonical"):
        build_selection_plan(
            inventory_path=inventory,
            backup_root=backup_root,
            suite_path=altered_suite,
            output=tmp_path / "alternate-selection.json",
            public_export_plan=export_plan,
        )


def test_internal_upload_is_lossless_private_and_idempotent(tmp_path: Path) -> None:
    inventory, backup_root, suite, _ = _full_backup(tmp_path)
    plan_path = tmp_path / "selection-plan.json"
    plan, _ = _build_plan(
        inventory=inventory,
        backup_root=backup_root,
        suite=suite,
        output=plan_path,
    )
    api = FakeApi()
    first = upload_internal_archive(
        api=api,
        plan_path=plan_path,
        backup_root=backup_root,
        state_root=tmp_path,
        token="secret",
        batch_size=64,
    )
    assert first["uploaded"] == EXPECTED_INTERNAL_STAGE_SLICES * 2 + 2
    assert api.repos[DEFAULT_INTERNAL_REPO]["private"] is True
    assert "README.md" in api.repos[DEFAULT_INTERNAL_REPO]["files"]
    assert "metadata/archive-migration.json" in api.repos[DEFAULT_INTERNAL_REPO]["files"]
    assert all("run=historical" not in path for path in api.repos[DEFAULT_INTERNAL_REPO]["files"])
    expected = internal_upload_files(
        plan=plan, backup_root=backup_root, state_root=tmp_path
    )
    for item in expected:
        assert sha256_bytes(api.repos[DEFAULT_INTERNAL_REPO]["files"][item.path]) == item.sha256

    second = upload_internal_archive(
        api=api,
        plan_path=plan_path,
        backup_root=backup_root,
        state_root=tmp_path,
        token="secret",
        batch_size=64,
    )
    assert second["uploaded"] == 0
    assert second["already_verified"] == len(expected)


def _mock_public_export(
    monkeypatch,
    root: Path,
    plan: dict,
    *,
    run_id: str = "qwen2.5-vl-7b-comparison-temp06-seeds42-44-v1",
):
    import scripts.trace_eval_public_export as public_export

    artifacts = []
    source_slices = {
        (
            item["identity"]["stage"],
            item["identity"]["model"],
            item["identity"]["seed"],
            item["identity"]["benchmark"],
        ): item
        for item in plan["paper"]["source_slices"]
    }
    public_to_source = dict(
        zip(("baseline", "trace", "reference"), CANONICAL_MODELS)
    )
    config_to_stage = {
        "responses": "generation",
        "extractions": "extraction",
        "scores": "score",
    }
    files = []
    readme_content = b"neutral public export\n"
    readme = root / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_bytes(readme_content)
    files.append(
        SimpleNamespace(
            path="README.md",
            sha256=sha256_bytes(readme_content),
            size=len(readme_content),
        )
    )
    for config in ("responses", "extractions", "scores"):
        for model in ("baseline", "trace", "reference"):
            for seed in CANONICAL_SEEDS:
                for benchmark in plan["paper"]["benchmarks"]:
                    source = source_slices[
                        (config_to_stage[config], public_to_source[model], seed, benchmark)
                    ]
                    manifest_path = (
                        f"metadata/parts/{config}/model={model}/seed={seed}/"
                        f"benchmark={benchmark}/part.manifest.json"
                    )
                    part_content = json.dumps(
                        {
                            "provenance": {
                                "source_archive_manifest_sha256": source["manifest"][
                                    "sha256"
                                ],
                                "source_archive_manifest_size": source["manifest"]["size"],
                                "source_archive_part_sha256": source["parquet"]["sha256"],
                                "source_archive_part_size": source["parquet"]["size"],
                            }
                        },
                        sort_keys=True,
                    ).encode()
                    part = root / manifest_path
                    part.parent.mkdir(parents=True, exist_ok=True)
                    part.write_bytes(part_content)
                    files.append(
                        SimpleNamespace(
                            path=manifest_path,
                            sha256=sha256_bytes(part_content),
                            size=len(part_content),
                        )
                    )
                    artifacts.append(
                        {
                            "config_name": config,
                            "run_id": run_id,
                            "model_id": model,
                            "seed": seed,
                            "benchmark_id": benchmark,
                            "manifest_path": manifest_path,
                        }
                    )
    suite_contract = json.loads(Path("evaluation/trace_eval/suite.v1.json").read_text())
    metadata_files = []

    def add_metadata(path: str, value: dict) -> None:
        content = json.dumps(value, sort_keys=True).encode()
        local = root / path
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(content)
        digest = sha256_bytes(content)
        files.append(SimpleNamespace(path=path, sha256=digest, size=len(content)))
        metadata_files.append({"path": path, "sha256": digest, "size": len(content)})

    add_metadata(
        "metadata/suites/trace_eval_v1.json",
        {
            "suite_id": "trace_eval_v1",
            "benchmark_ids": list(plan["paper"]["benchmarks"]),
            "categories": [
                {
                    "category_id": name.lower().replace(" & ", "-").replace(" ", "-"),
                    "category_name": name,
                    "benchmark_ids": list(members),
                }
                for name, members in suite_contract["categories"].items()
            ],
        },
    )
    add_metadata(
        f"metadata/runs/{run_id}.json",
        {
            "run_id": run_id,
            "suite_id": "trace_eval_v1",
            "model_ids": ["baseline", "trace", "reference"],
            "seeds": list(CANONICAL_SEEDS),
            "judge_model": {
                "model_id": "Qwen/Qwen3-32B",
                "model_revision": "9" * 40,
            },
            "source_selection_sha256": plan["selection_sha256"],
            "source_slice_set_sha256": plan["paper"]["source_slice_set_sha256"],
        },
    )
    for ordinal, model in enumerate(("baseline", "trace", "reference")):
        add_metadata(
            f"metadata/models/{model}.json",
            {
                "model_id": model,
                "model_revision": "sha256set:" + f"{ordinal + 4}" * 64,
                "display_name": model.title(),
                "repository_id": f"example/{model}",
                "repository_revision": f"{ordinal + 7}" * 40,
            },
        )
    manifest = {
        "schema_version": "trace_eval_export_manifest_v1",
        "neutralized": True,
        "source_selection_sha256": plan["selection_sha256"],
        "source_slice_set_sha256": plan["paper"]["source_slice_set_sha256"],
        "suite_id": "trace_eval_v1",
        "run_ids": [run_id],
        "artifacts": artifacts,
        "metadata_files": metadata_files,
    }
    manifest_content = json.dumps(manifest, sort_keys=True).encode()
    manifest_path = root / "metadata" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_content)
    files.append(
        SimpleNamespace(
            path="metadata/manifest.json",
            sha256=sha256_bytes(manifest_content),
            size=len(manifest_content),
        )
    )
    verified = SimpleNamespace(
        manifest=manifest,
        manifest_sha256=sha256_bytes(manifest_content),
        files=tuple(files),
    )
    monkeypatch.setattr(
        public_export,
        "load_and_verify_public_export",
        lambda _root, expected_artifacts, dynamic_markers=(): (
            verified
            if expected_artifacts == EXPECTED_PAPER_STAGE_SLICES
            and dynamic_markers == (CANONICAL_RUN,)
            else (_ for _ in ()).throw(
                AssertionError((expected_artifacts, dynamic_markers))
            )
        ),
        raising=False,
    )
    return verified


def _private_export_plan(
    root: Path,
    plan: dict | None,
    suite_path: Path,
    *,
    run_id: str = "qwen2.5-vl-7b-comparison-temp06-seeds42-44-v1",
    filename: str = "public-export-plan.json",
) -> Path:
    suite = json.loads(suite_path.read_text())
    categories = {
        name: list(members) for name, members in suite["categories"].items()
    }
    public_models = ("baseline", "trace", "reference")
    export_plan = {
        "schema_version": "trace_eval_export_plan_v1",
        "source": {
            "run_id": CANONICAL_RUN,
            "selection_sha256": plan["selection_sha256"] if plan else "0" * 64,
            **(
                {"slice_set_sha256": plan["paper"]["source_slice_set_sha256"]}
                if plan
                else {}
            ),
        },
        "public": {
            "run_id": run_id,
            "suite_id": "trace_eval_v1",
            "benchmarks": [item["key"] for item in suite["benchmarks"]],
            "categories": categories,
            "seeds": list(CANONICAL_SEEDS),
        },
        "models": [
            {
                "source_model_id": source,
                "source_revision": f"{ordinal + 1}" * 40,
                "model_id": public,
                "model_revision": "sha256set:" + f"{ordinal + 4}" * 64,
                "display_name": public.title(),
                "repository_id": f"example/{public}",
                "repository_revision": f"{ordinal + 7}" * 40,
            }
            for ordinal, (source, public) in enumerate(zip(CANONICAL_MODELS, public_models))
        ],
        "judge": {
            "source_model_id": "qwen3-32b-judge",
            "model_id": "Qwen/Qwen3-32B",
            "model_revision": "9" * 40,
        },
    }
    path = root / filename
    path.write_text(json.dumps(export_plan))
    return path


def _build_plan(
    *, inventory: Path, backup_root: Path, suite: Path, output: Path
) -> tuple[dict, Path]:
    export_plan = _private_export_plan(output.parent, None, suite)
    plan = build_selection_plan(
        inventory_path=inventory,
        backup_root=backup_root,
        suite_path=suite,
        output=output,
        public_export_plan=export_plan,
    )
    _private_export_plan(output.parent, plan, suite)
    return plan, export_plan


def test_private_paper_upload_and_full_verification_are_idempotent(
    tmp_path: Path, monkeypatch
) -> None:
    inventory, backup_root, suite, _ = _full_backup(tmp_path)
    plan_path = tmp_path / "selection-plan.json"
    plan, export_plan = _build_plan(
        inventory=inventory,
        backup_root=backup_root,
        suite=suite,
        output=plan_path,
    )
    public_root = tmp_path / "public"
    _mock_public_export(monkeypatch, public_root, plan)
    api = FakeApi()
    api.add_repo(DEFAULT_SOURCE_REPO, {}, private=True, sha=SOURCE_COMMIT)

    internal = upload_internal_archive(
        api=api,
        plan_path=plan_path,
        backup_root=backup_root,
        state_root=tmp_path,
        token="secret",
        public_export_plan=export_plan,
    )
    paper = upload_paper_export(
        api=api,
        plan_path=plan_path,
        public_export_root=public_root,
        public_export_plan=export_plan,
        state_root=tmp_path,
        token="secret",
    )
    assert internal["uploaded"] == EXPECTED_INTERNAL_STAGE_SLICES * 2 + 3
    assert paper["uploaded"] == EXPECTED_PAPER_STAGE_SLICES + 7
    assert api.repos[DEFAULT_PAPER_REPO]["private"] is True
    root_readme = api.repos[DEFAULT_PAPER_REPO]["files"]["README.md"].decode()
    assert root_readme.count("split: test") == 3
    assert "split: train" not in root_readme
    assert not any(
        path.startswith(("data/generation/", "data/extraction/", "data/score/", "metadata/slices/"))
        for path in api.repos[DEFAULT_PAPER_REPO]["files"]
    )

    receipt = verify_migration(
        api=api,
        inventory_path=inventory,
        backup_root=backup_root,
        plan_path=plan_path,
        public_export_root=public_root,
        state_root=tmp_path,
        output=tmp_path / "verification.json",
        token="secret",
        public_export_plan=export_plan,
    )
    assert receipt["coverage"] == {
        "paper_stage_slices": 648,
        "internal_stage_slices": 189,
        "paper_benchmarks": sorted(plan["paper"]["benchmarks"]),
        "internal_benchmarks": sorted(SUPPLEMENTARY_BENCHMARKS),
        "disjoint": True,
    }
    assert receipt["paper"]["private"] is True
    assert receipt["internal"]["private"] is True
    assert receipt["source_refs"] == SOURCE_REFS

    api.extra_branches.append(
        SimpleNamespace(
            name="late", ref="refs/heads/late", target_commit="6" * 40
        )
    )
    with pytest.raises(MigrationIntegrityError, match="source repository refs changed"):
        verify_migration(
            api=api,
            inventory_path=inventory,
            backup_root=backup_root,
            plan_path=plan_path,
            public_export_root=public_root,
            state_root=tmp_path,
            output=tmp_path / "verification-ref-race.json",
            token="secret",
            public_export_plan=export_plan,
        )
    api.extra_branches.clear()

    second = upload_paper_export(
        api=api,
        plan_path=plan_path,
        public_export_root=public_root,
        public_export_plan=export_plan,
        state_root=tmp_path,
        token="secret",
    )
    assert second["uploaded"] == 0
    assert second["already_verified"] == EXPECTED_PAPER_STAGE_SLICES + 7


def test_paper_repository_appends_a_second_immutable_run(
    tmp_path: Path, monkeypatch
) -> None:
    inventory, backup_root, suite, _ = _full_backup(tmp_path)
    plan_path = tmp_path / "selection-plan.json"
    plan, first_export_plan = _build_plan(
        inventory=inventory,
        backup_root=backup_root,
        suite=suite,
        output=plan_path,
    )
    first_root = tmp_path / "public-first"
    first = _mock_public_export(monkeypatch, first_root, plan)
    api = FakeApi()
    upload_paper_export(
        api=api,
        plan_path=plan_path,
        public_export_root=first_root,
        public_export_plan=first_export_plan,
        state_root=tmp_path,
        token="secret",
    )

    second_run = "qwen2.5-vl-7b-comparison-temp06-seeds42-44-v2"
    second_root = tmp_path / "public-second"
    _mock_public_export(monkeypatch, second_root, plan, run_id=second_run)
    second_export_plan = _private_export_plan(
        tmp_path,
        plan,
        suite,
        run_id=second_run,
        filename="public-export-plan-second.json",
    )
    report = upload_paper_run(
        api=api,
        repo_id=DEFAULT_PAPER_REPO,
        public_export_root=second_root,
        public_export_plan=second_export_plan,
        state_root=tmp_path,
        token="secret",
        allow_upload=True,
        confirmation=f"UPLOAD {DEFAULT_PAPER_REPO}/{second_run}",
    )
    first_run = first.manifest["run_ids"][0]
    assert report["uploaded"] == EXPECTED_PAPER_STAGE_SLICES + 6
    assert report["already_verified"] == 1
    assert report["other_runs"] == [first_run]
    remote = api.repos[DEFAULT_PAPER_REPO]["files"]
    assert any(path.startswith(f"runs/{first_run}/") for path in remote)
    assert any(path.startswith(f"runs/{second_run}/") for path in remote)

    repeated = upload_paper_run(
        api=api,
        repo_id=DEFAULT_PAPER_REPO,
        public_export_root=second_root,
        public_export_plan=second_export_plan,
        state_root=tmp_path,
        token="secret",
        allow_upload=True,
        confirmation=f"UPLOAD {DEFAULT_PAPER_REPO}/{second_run}",
    )
    assert repeated["uploaded"] == 0
    assert repeated["already_verified"] == EXPECTED_PAPER_STAGE_SLICES + 7


def test_paper_repository_rejects_same_run_content_and_layout_collisions(
    tmp_path: Path, monkeypatch
) -> None:
    inventory, backup_root, suite, _ = _full_backup(tmp_path)
    plan_path = tmp_path / "selection-plan.json"
    plan, export_plan = _build_plan(
        inventory=inventory,
        backup_root=backup_root,
        suite=suite,
        output=plan_path,
    )
    public_root = tmp_path / "public"
    verified = _mock_public_export(monkeypatch, public_root, plan)
    api = FakeApi()
    upload_paper_export(
        api=api,
        plan_path=plan_path,
        public_export_root=public_root,
        public_export_plan=export_plan,
        state_root=tmp_path,
        token="secret",
    )
    run_id = verified.manifest["run_ids"][0]
    remote = api.repos[DEFAULT_PAPER_REPO]["files"]
    collision_path = next(
        path for path in remote if path.startswith(f"runs/{run_id}/metadata/parts/")
    )
    remote[collision_path] = b"changed"
    with pytest.raises(MigrationIntegrityError, match="immutable paper run path differs"):
        upload_paper_export(
            api=api,
            plan_path=plan_path,
            public_export_root=public_root,
            public_export_plan=export_plan,
            state_root=tmp_path,
            token="secret",
        )

    remote[collision_path] = (
        public_root / collision_path.split(f"runs/{run_id}/", 1)[1]
    ).read_bytes()
    remote[f"runs/{run_id}/unexpected.json"] = b"{}"
    with pytest.raises(MigrationSafetyError, match="unexpected immutable file"):
        upload_paper_export(
            api=api,
            plan_path=plan_path,
            public_export_root=public_root,
            public_export_plan=export_plan,
            state_root=tmp_path,
            token="secret",
        )
    del remote[f"runs/{run_id}/unexpected.json"]
    remote["runs/legacy/data/generation/raw.parquet"] = b"raw"
    with pytest.raises(MigrationSafetyError, match="forbidden raw path"):
        upload_paper_export(
            api=api,
            plan_path=plan_path,
            public_export_root=public_root,
            public_export_plan=export_plan,
            state_root=tmp_path,
            token="secret",
        )


def test_public_part_provenance_is_recomputed_independently(
    tmp_path: Path, monkeypatch
) -> None:
    inventory, backup_root, suite, _ = _full_backup(tmp_path)
    plan_path = tmp_path / "selection-plan.json"
    plan, export_plan = _build_plan(
        inventory=inventory,
        backup_root=backup_root,
        suite=suite,
        output=plan_path,
    )
    public_root = tmp_path / "public"
    verified = _mock_public_export(monkeypatch, public_root, plan)
    part_path = public_root / verified.manifest["artifacts"][0]["manifest_path"]
    part = json.loads(part_path.read_text())
    part["provenance"]["source_archive_part_sha256"] = "f" * 64
    part_path.write_text(json.dumps(part))
    with pytest.raises(MigrationIntegrityError, match="part provenance differs"):
        load_verified_public_export(
            root=public_root,
            plan=plan,
            public_export_plan=export_plan,
        )


def test_public_attribution_metadata_must_match_private_crosswalk(
    tmp_path: Path, monkeypatch
) -> None:
    inventory, backup_root, suite, _ = _full_backup(tmp_path)
    plan_path = tmp_path / "selection-plan.json"
    plan, export_plan = _build_plan(
        inventory=inventory,
        backup_root=backup_root,
        suite=suite,
        output=plan_path,
    )
    public_root = tmp_path / "public"
    verified = _mock_public_export(monkeypatch, public_root, plan)

    model_path = public_root / "metadata/models/baseline.json"
    original_model = model_path.read_text()
    model = json.loads(original_model)
    model["repository_revision"] = "a" * 40
    model_path.write_text(json.dumps(model))
    with pytest.raises(MigrationIntegrityError, match="public model metadata differs"):
        load_verified_public_export(
            root=public_root, plan=plan, public_export_plan=export_plan
        )
    model_path.write_text(original_model)

    run_id = verified.manifest["run_ids"][0]
    run_path = public_root / "metadata" / "runs" / f"{run_id}.json"
    original_run = run_path.read_text()
    run = json.loads(original_run)
    run["judge_model"]["model_revision"] = "a" * 40
    run_path.write_text(json.dumps(run))
    with pytest.raises(MigrationIntegrityError, match="judge metadata differs"):
        load_verified_public_export(
            root=public_root, plan=plan, public_export_plan=export_plan
        )
    run_path.write_text(original_run)

    run = json.loads(original_run)
    run["seeds"] = list(reversed(run["seeds"]))
    run_path.write_text(json.dumps(run))
    with pytest.raises(MigrationIntegrityError, match="seed ordering differs"):
        load_verified_public_export(
            root=public_root, plan=plan, public_export_plan=export_plan
        )
    run_path.write_text(original_run)

    suite_path = public_root / "metadata/suites/trace_eval_v1.json"
    suite_metadata = json.loads(suite_path.read_text())
    suite_metadata["categories"] = list(reversed(suite_metadata["categories"]))
    suite_path.write_text(json.dumps(suite_metadata))
    with pytest.raises(MigrationIntegrityError, match="suite categories differ"):
        load_verified_public_export(
            root=public_root, plan=plan, public_export_plan=export_plan
        )


def test_generic_paper_append_rejects_noncanonical_benchmark_set(
    tmp_path: Path, monkeypatch
) -> None:
    inventory, backup_root, suite, _ = _full_backup(tmp_path)
    plan_path = tmp_path / "selection-plan.json"
    plan, export_plan = _build_plan(
        inventory=inventory,
        backup_root=backup_root,
        suite=suite,
        output=plan_path,
    )
    public_root = tmp_path / "public"
    _mock_public_export(monkeypatch, public_root, plan)
    altered = json.loads(export_plan.read_text())
    removed = altered["public"]["benchmarks"].pop()
    for members in altered["public"]["categories"].values():
        if removed in members:
            members.remove(removed)
    altered_plan = tmp_path / "public-export-plan-23.json"
    altered_plan.write_text(json.dumps(altered))
    with pytest.raises(MigrationIntegrityError, match="canonical trace_eval_v1"):
        upload_paper_run(
            api=FakeApi(),
            repo_id=DEFAULT_PAPER_REPO,
            public_export_root=public_root,
            public_export_plan=altered_plan,
            state_root=tmp_path,
            token="secret",
            allow_upload=True,
            confirmation=(
                "UPLOAD maveryn/trace-eval-runs/"
                "qwen2.5-vl-7b-comparison-temp06-seeds42-44-v1"
            ),
        )


def test_paper_export_rejects_a_raw_source_artifact(tmp_path: Path, monkeypatch) -> None:
    inventory, backup_root, suite, _ = _full_backup(tmp_path)
    plan_path = tmp_path / "selection-plan.json"
    plan, export_plan = _build_plan(
        inventory=inventory,
        backup_root=backup_root,
        suite=suite,
        output=plan_path,
    )
    public_root = tmp_path / "public"
    verified = _mock_public_export(monkeypatch, public_root, plan)
    raw = plan["paper"]["source_slices"][0]["parquet"]
    raw_path = backup_root / "snapshot" / raw["path"]
    destination = public_root / "README.md"
    destination.write_bytes(raw_path.read_bytes())
    verified.files[0].sha256 = raw["sha256"]
    verified.files[0].size = destination.stat().st_size
    with pytest.raises(MigrationSafetyError, match="raw source artifact"):
        load_verified_public_export(
            root=public_root, plan=plan, public_export_plan=export_plan
        )


def test_delete_and_public_promotion_have_separate_exact_gates() -> None:
    api = FakeApi()
    api.add_repo(DEFAULT_SOURCE_REPO, {}, private=True, sha=SOURCE_COMMIT)
    api.add_repo(DEFAULT_PAPER_REPO, {}, private=True, sha="3" * 40)
    api.add_repo(DEFAULT_INTERNAL_REPO, {}, private=True, sha="5" * 40)
    plan = {
        "source": {"repo_id": DEFAULT_SOURCE_REPO},
        "internal": {"repo_id": DEFAULT_INTERNAL_REPO},
        "paper": {"repo_id": DEFAULT_PAPER_REPO},
    }
    with pytest.raises(MigrationSafetyError, match="allow flag"):
        delete_old_repository(
            api=api,
            source_repo_id=DEFAULT_SOURCE_REPO,
            token="secret",
            allow_delete=False,
            confirmation=None,
            verified_source_repo_id=DEFAULT_SOURCE_REPO,
            verified_source_commit=SOURCE_COMMIT,
            verified_source_refs=SOURCE_REFS,
            verified_paper_repo_id=DEFAULT_PAPER_REPO,
            verified_paper_revision="3" * 40,
            verified_internal_repo_id=DEFAULT_INTERNAL_REPO,
            verified_internal_revision="5" * 40,
        )
    assert api.deleted == []
    with pytest.raises(MigrationSafetyError, match="verification receipt"):
        delete_old_repository(
            api=api,
            source_repo_id=DEFAULT_SOURCE_REPO,
            token="secret",
            allow_delete=True,
            confirmation=f"DELETE {DEFAULT_SOURCE_REPO}",
            verified_source_repo_id="maveryn/different-source",
            verified_source_commit=SOURCE_COMMIT,
            verified_source_refs=SOURCE_REFS,
            verified_paper_repo_id=DEFAULT_PAPER_REPO,
            verified_paper_revision="3" * 40,
            verified_internal_repo_id=DEFAULT_INTERNAL_REPO,
            verified_internal_revision="5" * 40,
        )
    assert api.deleted == []
    with pytest.raises(MigrationSafetyError, match="allow flag"):
        promote_paper_repository(
            api=api,
            repo_id=DEFAULT_PAPER_REPO,
            plan=plan,
            token="secret",
            allow_public=False,
            confirmation=None,
            verified_revision="3" * 40,
            verified_other_runs=[],
        )
    assert api.publicized == []

    delete_old_repository(
        api=api,
        source_repo_id=DEFAULT_SOURCE_REPO,
        token="secret",
        allow_delete=True,
        confirmation=f"DELETE {DEFAULT_SOURCE_REPO}",
        verified_source_repo_id=DEFAULT_SOURCE_REPO,
        verified_source_commit=SOURCE_COMMIT,
        verified_source_refs=SOURCE_REFS,
        verified_paper_repo_id=DEFAULT_PAPER_REPO,
        verified_paper_revision="3" * 40,
        verified_internal_repo_id=DEFAULT_INTERNAL_REPO,
        verified_internal_revision="5" * 40,
    )
    assert api.deleted == [DEFAULT_SOURCE_REPO]
    promote_paper_repository(
        api=api,
        repo_id=DEFAULT_PAPER_REPO,
        plan=plan,
        token="secret",
        allow_public=True,
        confirmation=f"PUBLIC {DEFAULT_PAPER_REPO}",
        verified_revision="3" * 40,
        verified_other_runs=[],
    )
    assert api.publicized == [DEFAULT_PAPER_REPO]


def test_non_neutral_paper_target_is_never_promoted() -> None:
    api = FakeApi()
    repo_id = "maveryn/trace-final24-results"
    api.add_repo(repo_id, {}, private=True, sha="4" * 40)
    plan = {
        "source": {"repo_id": DEFAULT_SOURCE_REPO},
        "internal": {"repo_id": DEFAULT_INTERNAL_REPO},
        "paper": {"repo_id": repo_id},
    }
    with pytest.raises(MigrationSafetyError, match="suite state"):
        promote_paper_repository(
            api=api,
            repo_id=repo_id,
            plan=plan,
            token="secret",
            allow_public=True,
            confirmation=f"PUBLIC {repo_id}",
            verified_revision="4" * 40,
            verified_other_runs=[],
        )
    assert api.publicized == []


def test_delete_rechecks_source_refs_and_both_destination_heads() -> None:
    def prepared_api() -> FakeApi:
        api = FakeApi()
        api.add_repo(DEFAULT_SOURCE_REPO, {}, private=True, sha=SOURCE_COMMIT)
        api.add_repo(DEFAULT_PAPER_REPO, {}, private=True, sha="3" * 40)
        api.add_repo(DEFAULT_INTERNAL_REPO, {}, private=True, sha="5" * 40)
        return api

    def attempt(api: FakeApi) -> None:
        delete_old_repository(
            api=api,
            source_repo_id=DEFAULT_SOURCE_REPO,
            token="secret",
            allow_delete=True,
            confirmation=f"DELETE {DEFAULT_SOURCE_REPO}",
            verified_source_repo_id=DEFAULT_SOURCE_REPO,
            verified_source_commit=SOURCE_COMMIT,
            verified_source_refs=SOURCE_REFS,
            verified_paper_repo_id=DEFAULT_PAPER_REPO,
            verified_paper_revision="3" * 40,
            verified_internal_repo_id=DEFAULT_INTERNAL_REPO,
            verified_internal_revision="5" * 40,
        )

    refs_changed = prepared_api()
    refs_changed.extra_branches.append(
        SimpleNamespace(
            name="late", ref="refs/heads/late", target_commit="6" * 40
        )
    )
    with pytest.raises(MigrationSafetyError, match="refs changed"):
        attempt(refs_changed)
    assert refs_changed.deleted == []

    paper_changed = prepared_api()
    paper_changed.repos[DEFAULT_PAPER_REPO]["sha"] = "7" * 40
    with pytest.raises(MigrationSafetyError, match="paper repository changed"):
        attempt(paper_changed)
    assert paper_changed.deleted == []

    internal_public = prepared_api()
    internal_public.repos[DEFAULT_INTERNAL_REPO]["private"] = False
    with pytest.raises(MigrationSafetyError, match="internal repository is not private"):
        attempt(internal_public)
    assert internal_public.deleted == []


def test_public_promotion_rejects_unverified_additional_runs() -> None:
    api = FakeApi()
    api.add_repo(DEFAULT_PAPER_REPO, {}, private=True, sha="3" * 40)
    plan = {
        "source": {"repo_id": DEFAULT_SOURCE_REPO},
        "internal": {"repo_id": DEFAULT_INTERNAL_REPO},
        "paper": {"repo_id": DEFAULT_PAPER_REPO},
    }
    with pytest.raises(MigrationSafetyError, match="additional runs"):
        promote_paper_repository(
            api=api,
            repo_id=DEFAULT_PAPER_REPO,
            plan=plan,
            token="secret",
            allow_public=True,
            confirmation=f"PUBLIC {DEFAULT_PAPER_REPO}",
            verified_revision="3" * 40,
            verified_other_runs=["future-run"],
        )
    assert api.publicized == []
