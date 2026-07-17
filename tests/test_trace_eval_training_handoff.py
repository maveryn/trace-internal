from __future__ import annotations

import json
import shutil
import stat
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.run_trace_eval_after_training as handoff
import scripts.run_trace_eval_publish_worker as publish_worker


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_REVISION = "sha256set:" + "a" * 64
BASE_REPOSITORY_REVISION = "b" * 40
FINAL_REPOSITORY_REVISION = "c" * 40


def _config(tmp_path: Path) -> handoff.Config:
    experiment = "trace_synthetic_3b_run"
    return handoff.Config(
        experiment_name=experiment,
        training_status=tmp_path / f"{experiment}.status",
        training_pid_file=tmp_path / f"{experiment}.pid",
        training_script_name="run_training_job.sh",
        checkpoint_root=tmp_path / "checkpoints" / experiment,
        checkpoint_step=500,
        world_size=8,
        temporary_repo="example/trace-qwen25vl3b-temporary",
        canonical_repo="example/trace-qwen2.5-vl-3b",
        source_model_slug="trace-qwen25vl3b-step500",
        public_model_id="trace-qwen2.5-vl-3b",
        display_name="TRACE Qwen2.5-VL 3B",
        run_tag="trace_eval_v1_temp06_seed42_43_44_trace-qwen25vl3b-step500",
        public_run_id="trace-qwen2.5-vl-3b-eval-v1",
        paper_repo="example/trace-eval-runs",
        token_file=tmp_path / "hf-token.txt",
        state_root=tmp_path / "state",
        dataset_manifest=tmp_path / "dataset-manifest.json",
        judge_model=tmp_path / "qwen3-32b-judge",
        judge_revision="d" * 40,
        python_bin=Path("/usr/bin/python3"),
        eval_deps_root=tmp_path / "eval-deps",
        vlmeval_root=tmp_path / "VLMEvalKit",
        seeds=(42, 43, 44),
        gpu_groups=("0", "1", "2", "3", "4", "5", "6", "7"),
        generation_port_start=18000,
        judge_port_start=18100,
        poll_seconds=30.0,
        hf_attempts=8,
        hf_retry_base_seconds=5.0,
        hf_retry_cap_seconds=300.0,
        publisher_timeout_seconds=172800.0,
        training_source_commit="e" * 40,
        base_model_id="Qwen/Qwen2.5-VL-3B-Instruct",
        base_model_revision="f" * 40,
        dataset_id="example/trace",
        dataset_revision="1" * 40,
        wandb_url="https://wandb.ai/example/project/runs/run-id",
    )


def _cli_args(config: handoff.Config) -> list[str]:
    result = [
        "--experiment-name",
        config.experiment_name,
        "--training-status",
        str(config.training_status),
        "--training-pid-file",
        str(config.training_pid_file),
        "--training-script-name",
        config.training_script_name,
        "--checkpoint-root",
        str(config.checkpoint_root),
        "--temporary-repo",
        config.temporary_repo,
        "--canonical-repo",
        config.canonical_repo,
        "--source-model-slug",
        config.source_model_slug,
        "--public-model-id",
        config.public_model_id,
        "--display-name",
        config.display_name,
        "--run-tag",
        config.run_tag,
        "--public-run-id",
        config.public_run_id,
        "--paper-repo",
        config.paper_repo,
        "--token-file",
        str(config.token_file),
        "--state-root",
        str(config.state_root),
        "--dataset-manifest",
        str(config.dataset_manifest),
        "--judge-model",
        str(config.judge_model),
        "--judge-revision",
        config.judge_revision,
        "--python-bin",
        str(config.python_bin),
        "--eval-deps-root",
        str(config.eval_deps_root),
        "--vlmeval-root",
        str(config.vlmeval_root),
        "--training-source-commit",
        config.training_source_commit,
        "--base-model-id",
        config.base_model_id,
        "--base-model-revision",
        config.base_model_revision,
        "--dataset-id",
        config.dataset_id,
        "--dataset-revision",
        config.dataset_revision,
        "--wandb-url",
        config.wandb_url,
    ]
    for seed in config.seeds:
        result.extend(("--seed", str(seed)))
    for group in config.gpu_groups:
        result.extend(("--gpu-group", group))
    return result


def _write_small_model(config: handoff.Config) -> dict[str, dict[str, object]]:
    config.model_path.mkdir(parents=True)
    (config.model_path / "config.json").write_text("{}\n", encoding="utf-8")
    (config.model_path / "model.safetensors").write_bytes(b"synthetic-weights")
    return handoff._snapshot_manifest(config.model_path, include_marker=False)


def _local_revision(manifest: dict[str, dict[str, object]]) -> str:
    hashes = {key: value["sha256"] for key, value in manifest.items()}
    return "sha256set:" + handoff.hashlib.sha256(
        handoff._canonical_json(hashes).encode("utf-8")
    ).hexdigest()


def _write_registered_marker(
    config: handoff.Config,
    manifest: dict[str, dict[str, object]],
    base_revision: str,
) -> str:
    revision = _local_revision(manifest)
    marker = {
        "schema_version": "trace-model-revision-v1",
        "slug": config.source_model_slug,
        "immutable_revision": revision,
        "source": f"{config.canonical_repo}@{base_revision}",
        "model_origin": "local_registration",
        "file_count": len(manifest),
        "file_sha256": {key: value["sha256"] for key, value in manifest.items()},
    }
    (config.model_path / handoff.MODEL_MARKER).write_text(
        json.dumps(marker), encoding="utf-8"
    )
    return revision


def test_print_config_is_side_effect_free_and_renders_exact_gpu_plan(tmp_path: Path) -> None:
    config = _config(tmp_path)
    token = "hf_synthetic_secret_that_must_not_be_read"
    config.token_file.write_text(token, encoding="utf-8")
    config.token_file.chmod(0)

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_trace_eval_after_training.py"),
            *_cli_args(config),
            "--assume-local-revision",
            LOCAL_REVISION,
            "--assume-repository-revision",
            FINAL_REPOSITORY_REVISION,
            "--print-config",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    document = json.loads(completed.stdout)

    assert not config.state_root.exists()
    assert token not in completed.stdout
    assert document["seeds"] == [42, 43, 44]
    assert document["gpu_groups"] == [str(index) for index in range(8)]
    assert document["eval_environment"]["GPU_GROUPS"] == "0 1 2 3 4 5 6 7"
    assert document["eval_command"].count("--model") == 1
    assert document["eval_command"][document["eval_command"].index("--seeds") + 1 : -2] == [
        "42",
        "43",
        "44",
    ]
    assert document["publisher_command"][:3] == ["nice", "-n", "10"]
    assert (
        document["publisher_command"][-1]
        == "UPLOAD example/trace-eval-runs/trace-qwen2.5-vl-3b-eval-v1"
    )


def test_eval_and_publisher_commands_share_exact_model_identity(tmp_path: Path) -> None:
    config = _config(tmp_path)
    identity = handoff.ModelIdentity(
        local_revision=LOCAL_REVISION,
        repository_revision=FINAL_REPOSITORY_REVISION,
        base_repository_revision=BASE_REPOSITORY_REVISION,
    )

    evaluation = handoff._eval_command(config, identity)
    publisher = handoff._publisher_command(config, identity)

    assert evaluation[2:8] == [
        "--model",
        config.source_model_slug,
        str(config.model_path),
        LOCAL_REVISION,
        f"{config.canonical_repo}@{FINAL_REPOSITORY_REVISION}",
        config.display_name,
    ]
    model_offset = publisher.index("--model")
    assert publisher[model_offset + 1 : model_offset + 9] == [
        config.source_model_slug,
        str(config.model_path),
        LOCAL_REVISION,
        config.public_model_id,
        FINAL_REPOSITORY_REVISION,
        config.display_name,
        config.canonical_repo,
        FINAL_REPOSITORY_REVISION,
    ]
    environment = handoff._eval_environment(config)
    assert environment["GPU_GROUPS"] == "0 1 2 3 4 5 6 7"
    assert environment["GEN_PORT_START"] == "18000"
    assert environment["JUDGE_PORT_START"] == "18100"
    worker_args = publish_worker._parser().parse_args(publisher[5:])
    worker_config = publish_worker._config_from_args(worker_args)
    assert handoff._publisher_config_sha256(config, identity) == worker_config.config_sha256
    handoff._write_evaluation_receipt(config, identity)
    assert handoff._evaluation_complete(config, identity)
    manifest_sha = "9" * 64
    handoff._atomic_json(
        config.publish_root / "status.json",
        {
            "schema_version": "trace-eval-publish-worker-status-v1",
            "config_sha256": worker_config.config_sha256,
            "phase": "complete",
            "source_run_id": config.run_tag,
            "public_run_id": config.public_run_id,
            "models": [config.source_model_slug],
            "seeds": list(config.seeds),
            "expected_slices": 216,
            "public_export_manifest_sha256": manifest_sha,
            "upload_report": {
                "run_id": config.public_run_id,
                "public_export_manifest_sha256": manifest_sha,
            },
        },
    )
    assert handoff._publisher_complete(config, identity)


def test_marker_validation_rejects_conflicting_snapshot(tmp_path: Path) -> None:
    config = _config(tmp_path)
    base_manifest = _write_small_model(config)
    hashes = {key: value["sha256"] for key, value in base_manifest.items()}
    marker = {
        "schema_version": "trace-model-revision-v1",
        "slug": config.source_model_slug,
        "immutable_revision": _local_revision(base_manifest),
        "source": f"{config.canonical_repo}@{BASE_REPOSITORY_REVISION}",
        "model_origin": "local_registration",
        "file_count": len(hashes),
        "file_sha256": hashes,
    }

    assert handoff._validate_marker_document(config, marker, base_manifest) == marker
    (config.model_path / handoff.MODEL_MARKER).write_text(
        json.dumps(marker), encoding="utf-8"
    )
    assert handoff.MODEL_MARKER not in handoff._snapshot_manifest(
        config.model_path, include_marker=False
    )
    assert handoff.MODEL_MARKER in handoff._snapshot_manifest(
        config.model_path, include_marker=True
    )
    marker["immutable_revision"] = LOCAL_REVISION
    with pytest.raises(handoff.HandoffError, match="content revision"):
        handoff._validate_marker_document(config, marker, base_manifest)
    marker["immutable_revision"] = _local_revision(base_manifest)
    marker["file_sha256"] = {**hashes, "unexpected": "0" * 64}
    with pytest.raises(handoff.HandoffError, match="does not bind"):
        handoff._validate_marker_document(config, marker, base_manifest)


def test_marker_upload_binds_final_revision_only_after_remote_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    base_manifest = _write_small_model(config)
    initial = SimpleNamespace(sha=BASE_REPOSITORY_REVISION, private=True, siblings=[])
    final = SimpleNamespace(
        sha=FINAL_REPOSITORY_REVISION,
        private=True,
        siblings=[SimpleNamespace(rfilename=handoff.MODEL_MARKER)],
    )
    calls: list[tuple[str, str]] = []

    def register(_config: handoff.Config, base_revision: str) -> str:
        calls.append(("register", base_revision))
        local_revision = _local_revision(base_manifest)
        marker = {
            "schema_version": "trace-model-revision-v1",
            "slug": config.source_model_slug,
            "immutable_revision": local_revision,
            "source": f"{config.canonical_repo}@{base_revision}",
            "model_origin": "local_registration",
            "file_count": len(base_manifest),
            "file_sha256": {
                key: value["sha256"] for key, value in base_manifest.items()
            },
        }
        (config.model_path / handoff.MODEL_MARKER).write_text(
            json.dumps(marker), encoding="utf-8"
        )
        return local_revision

    class Api:
        def upload_file(self, **kwargs: object) -> None:
            calls.append(("upload", str(kwargs["parent_commit"])))

        def model_info(self, *_args: object, **kwargs: object) -> object:
            return initial if kwargs.get("revision") == BASE_REPOSITORY_REVISION else final

    monkeypatch.setattr(handoff, "_register_local", register)
    monkeypatch.setattr(handoff, "_verify_remote_snapshot", lambda *args, **kwargs: None)

    identity = handoff._complete_marker_handoff(
        config,
        Api(),
        initial,
        base_manifest,
        token="synthetic-token",
    )

    assert calls == [
        ("register", BASE_REPOSITORY_REVISION),
        ("upload", BASE_REPOSITORY_REVISION),
    ]
    assert identity == handoff.ModelIdentity(
        _local_revision(base_manifest),
        FINAL_REPOSITORY_REVISION,
        BASE_REPOSITORY_REVISION,
    )


@pytest.mark.parametrize("mode", ["move", "direct"])
def test_canonical_handoff_moves_complete_temp_or_recovers_with_direct_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    config = _config(tmp_path)
    base_manifest = _write_small_model(config)
    config.token_file.write_text("hf_synthetic\n", encoding="utf-8")
    config.token_file.chmod(0o600)
    temporary_info = SimpleNamespace(
        sha="1" * 40,
        private=True,
        siblings=[],
    )
    base_info = SimpleNamespace(
        sha=BASE_REPOSITORY_REVISION,
        private=True,
        siblings=[],
    )
    final_info = SimpleNamespace(
        sha=FINAL_REPOSITORY_REVISION,
        private=True,
        siblings=[SimpleNamespace(rfilename=handoff.MODEL_MARKER)],
    )
    state: dict[str, object | None] = {
        config.temporary_repo: temporary_info if mode == "move" else None,
        config.canonical_repo: None,
    }
    events: list[tuple[str, object]] = []

    class Api:
        def move_repo(self, **_kwargs: object) -> None:
            events.append(("move", state[config.temporary_repo]))
            state[config.temporary_repo] = None
            state[config.canonical_repo] = base_info

        def create_repo(self, **_kwargs: object) -> None:
            events.append(("create", None))
            state[config.canonical_repo] = SimpleNamespace(
                sha=None, private=True, siblings=[]
            )

        def upload_folder(self, **kwargs: object) -> None:
            events.append(("upload_folder", kwargs.get("parent_commit")))
            state[config.canonical_repo] = base_info

        def upload_file(self, **kwargs: object) -> None:
            events.append(("upload_marker", kwargs.get("parent_commit")))
            state[config.canonical_repo] = final_info

    def repo_info(
        _config: handoff.Config,
        _api: object,
        repo_id: str,
        *,
        token: str,
        revision: str | None = None,
    ) -> object | None:
        del token
        if revision == BASE_REPOSITORY_REVISION:
            return base_info
        if revision == FINAL_REPOSITORY_REVISION:
            return final_info
        return state[repo_id]

    def register(_config: handoff.Config, base_revision: str) -> str:
        events.append(("register", base_revision))
        return _write_registered_marker(config, base_manifest, base_revision)

    monkeypatch.setattr(handoff, "_repo_info_optional", repo_info)
    monkeypatch.setattr(handoff, "_verify_remote_snapshot", lambda *args, **kwargs: None)
    monkeypatch.setattr(handoff, "_register_local", register)
    status = SimpleNamespace(write=lambda phase, **_details: events.append(("status", phase)))

    identity = handoff._canonicalize_model(
        config,
        status,
        api_factory=lambda **_kwargs: Api(),
    )

    assert identity == handoff.ModelIdentity(
        _local_revision(base_manifest),
        FINAL_REPOSITORY_REVISION,
        BASE_REPOSITORY_REVISION,
    )
    assert config.receipt_path.is_file()
    assert ("upload_marker", BASE_REPOSITORY_REVISION) in events
    if mode == "move":
        assert any(event[0] == "move" for event in events)
        assert not any(event[0] == "upload_folder" for event in events)
    else:
        assert ("create", None) in events
        assert ("upload_folder", None) in events


def test_unrelated_canonical_repository_is_never_mutated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    _write_small_model(config)
    config.token_file.write_text("hf_synthetic\n", encoding="utf-8")
    config.token_file.chmod(0o600)
    unrelated = SimpleNamespace(
        sha="7" * 40,
        private=True,
        siblings=[SimpleNamespace(rfilename="config.json")],
    )
    mutations: list[str] = []

    class Api:
        def upload_folder(self, **_kwargs: object) -> None:
            mutations.append("upload")

        def upload_file(self, **_kwargs: object) -> None:
            mutations.append("marker")

        def move_repo(self, **_kwargs: object) -> None:
            mutations.append("move")

    monkeypatch.setattr(
        handoff,
        "_repo_info_optional",
        lambda *_args, **_kwargs: unrelated,
    )
    monkeypatch.setattr(
        handoff,
        "_verify_remote_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            handoff.HandoffError("snapshot mismatch")
        ),
    )

    with pytest.raises(handoff.HandoffError, match="refusing to overwrite"):
        handoff._canonicalize_model(
            config,
            SimpleNamespace(write=lambda *_args, **_kwargs: None),
            api_factory=lambda **_kwargs: Api(),
        )
    assert mutations == []


def test_process_receipt_requires_pid_start_time_and_command_tokens(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    process = proc_root / "123"
    process.mkdir(parents=True)
    (process / "cmdline").write_bytes(b"bash\0scripts/run_trace_eval.sh\0--run-tag\0campaign\0")
    fields = ["123", "(bash)", "S", *(["0"] * 18), "777"]
    (process / "stat").write_text(" ".join(fields), encoding="utf-8")

    assert handoff._process_matches(
        123,
        start_ticks=777,
        expected_tokens=("run_trace_eval.sh", "campaign"),
        proc_root=proc_root,
    )
    assert not handoff._process_matches(
        123,
        start_ticks=778,
        expected_tokens=("run_trace_eval.sh",),
        proc_root=proc_root,
    )
    assert not handoff._process_matches(
        123,
        start_ticks=777,
        expected_tokens=("different-campaign",),
        proc_root=proc_root,
    )


def test_child_receipt_is_bound_to_the_exact_launch_command(tmp_path: Path) -> None:
    config = _config(tmp_path)
    command = ["bash", "/repo/scripts/run_trace_eval.sh", "--run-tag", config.run_tag]
    expected_tokens = ("run_trace_eval.sh", config.run_tag)
    handoff._atomic_json(
        handoff._child_receipt_path(config, "evaluator"),
        {
            "schema_version": handoff.CHILD_SCHEMA,
            "config_sha256": config.config_sha256,
            "role": "evaluator",
            "pid": None,
            "start_ticks": None,
            "expected_tokens": list(expected_tokens),
            "command_sha256": "0" * 64,
        },
    )

    with pytest.raises(handoff.HandoffError, match="does not match"):
        handoff._load_live_child(
            config,
            "evaluator",
            command=command,
            expected_tokens=expected_tokens,
        )


def test_launch_intent_discovers_child_started_before_pid_receipt(tmp_path: Path) -> None:
    config = _config(tmp_path)
    unique = f"trace-handoff-{tmp_path.name}"
    command = [sys.executable, "-c", "import time; time.sleep(30)", unique]
    expected_tokens = ("time.sleep(30)", unique)
    receipt_path = handoff._child_receipt_path(config, "evaluator")
    handoff._atomic_json(
        receipt_path,
        {
            "schema_version": handoff.CHILD_SCHEMA,
            "config_sha256": config.config_sha256,
            "role": "evaluator",
            "pid": None,
            "start_ticks": None,
            "expected_tokens": list(expected_tokens),
            "command_sha256": handoff._command_sha256(command),
            "launch_intent_at": handoff._utc_now(),
        },
    )
    process = subprocess.Popen(command, start_new_session=True)
    try:
        child = handoff._load_live_child(
            config,
            "evaluator",
            command=command,
            expected_tokens=expected_tokens,
        )
        assert child is not None
        assert child.pid == process.pid
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["pid"] == process.pid
        assert receipt["start_ticks"] == child.start_ticks
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_private_token_and_receipt_modes_are_enforced(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.token_file.write_text("hf_synthetic\n", encoding="utf-8")
    config.token_file.chmod(0o644)
    with pytest.raises(handoff.HandoffError, match="mode 600"):
        handoff._read_token(config.token_file)

    config.token_file.chmod(0o600)
    assert handoff._read_token(config.token_file) == "hf_synthetic"
    handoff._atomic_json(config.receipt_path, {"schema_version": "synthetic"})
    assert stat.S_IMODE(config.state_root.stat().st_mode) == 0o700
    assert stat.S_IMODE(config.receipt_path.stat().st_mode) == 0o600


def test_child_environments_remove_ambient_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    monkeypatch.setenv("HF_TOKEN", "hf_secret")
    monkeypatch.setenv("WANDB_API_KEY", "wandb_secret")
    monkeypatch.setenv("GITHUB_TOKEN", "github_secret")
    monkeypatch.setenv("SAFE_NONSECRET_VALUE", "kept")

    environment = handoff._eval_environment(config)

    assert "HF_TOKEN" not in environment
    assert "WANDB_API_KEY" not in environment
    assert "GITHUB_TOKEN" not in environment
    assert environment["SAFE_NONSECRET_VALUE"] == "kept"


def test_checkpoint_validation_requires_all_eight_rank_shards(tmp_path: Path) -> None:
    checkpoint_root = Path("/dev/shm") / f"trace-handoff-test-{tmp_path.name}"
    shutil.rmtree(checkpoint_root, ignore_errors=True)
    config = replace(_config(tmp_path), checkpoint_root=checkpoint_root)
    try:
        step_root = config.checkpoint_root / "global_step_500"
        actor = step_root / "actor"
        actor.mkdir(parents=True)
        (config.checkpoint_root / "checkpoint_tracker.json").write_text(
            json.dumps({"last_global_step": 500}), encoding="utf-8"
        )
        (step_root / "dataloader.pt").write_bytes(b"state")
        for prefix in ("model", "optim", "extra_state"):
            for rank in range(8):
                (actor / f"{prefix}_world_size_8_rank_{rank}.pt").write_bytes(b"state")

        handoff._validate_final_checkpoint(config)
        (actor / "model_world_size_8_rank_7.pt").unlink()
        with pytest.raises(handoff.HandoffError, match="model shard set"):
            handoff._validate_final_checkpoint(config)
    finally:
        shutil.rmtree(checkpoint_root, ignore_errors=True)


def test_pinned_job_wrapper_has_valid_shell_and_exact_three_seed_contract() -> None:
    wrapper = REPO_ROOT / "scripts" / "run_trace_qwen25vl3b_post_training_eval_job.sh"
    subprocess.run(["bash", "-n", str(wrapper)], check=True)
    source = wrapper.read_text(encoding="utf-8")

    assert "--seed 42 --seed 43 --seed 44" in source
    assert "--gpu-group 0 --gpu-group 1 --gpu-group 2 --gpu-group 3" in source
    assert "--gpu-group 4 --gpu-group 5 --gpu-group 6 --gpu-group 7" in source
    assert "maveryn/trace-qwen2.5-vl-3b" in source
    assert "trace-qwen2.5-vl-3b-eval-v1" in source
