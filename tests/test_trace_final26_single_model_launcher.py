from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "scripts" / "run_trace_final25_temp06_3seed_8models.sh"
WRAPPER = REPO_ROOT / "scripts" / "run_trace_final26_temp06_seed42_trained_model.sh"
POOL_STARTER = REPO_ROOT / "scripts" / "start_vllm_endpoint_pool.sh"
VLLM_SITECUSTOMIZE = (
    REPO_ROOT / "scripts" / "vllm_sitecustomize" / "sitecustomize.py"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_shell_launchers_are_syntactically_valid() -> None:
    for path in (CANONICAL, WRAPPER, POOL_STARTER):
        subprocess.run(["bash", "-n", str(path)], check=True)


def test_wrapper_pins_one_trained_model_seed_and_all_gpus() -> None:
    script = _text(WRAPPER)

    assert "export SUITE=all26" in script
    assert "export SEEDS=42" in script
    assert 'export GPU_GROUPS="0 1 2 3 4 5 6 7"' in script
    assert 'export SINGLE_MODEL_SLUG="trace-qwen25vl7b-answer-step500-rerun-20260715"' in script
    assert (
        'export SINGLE_MODEL_REVISION="sha256set:'
        '8396b0be6a760ff7cbbdff02b3017b6b5bc352c87291480aba18fd3e3b6a13b5"'
        in script
    )
    assert "global_step_500/actor/huggingface" in script
    assert "export GEN_TEMPERATURE=0.6" in script
    assert "export GEN_TOP_P=1.0" in script
    assert "export GEN_TOP_K=-1" in script
    assert "export GEN_MAX_TOKENS=4096" in script
    assert 'export HF_ARCHIVE_LOCAL_ONLY="${HF_ARCHIVE_LOCAL_ONLY:-1}"' in script
    assert 'TMP_ROOT="/dev/shm/trace_rlvr"' in script
    assert "MODEL_SLUGS" not in script
    assert "MODEL_PATHS" not in script
    assert script.count("exec bash") == 1


def test_canonical_defaults_remain_frozen_multi_model() -> None:
    script = _text(CANONICAL)

    assert 'SUITE="${SUITE:-frozen}"' in script
    assert 'SEEDS=(${SEEDS:-42 43 44})' in script
    assert "qwen25vl3b-base" in script
    assert "vero-qwen25-7b" in script
    assert 'MODEL_SLUGS=("${SINGLE_MODEL_SLUG}")' in script
    assert 'MODEL_PATHS=("${SINGLE_MODEL_PATH}")' in script
    assert 'MODEL_REVISIONS=("${SINGLE_MODEL_REVISION}")' in script
    assert 'MODEL_SOURCES=("${SINGLE_MODEL_SOURCE}")' in script
    assert 'MODEL_LABELS=("${SINGLE_MODEL_LABEL}")' in script


def test_all26_mode_routes_generation_scoring_verification_and_archive() -> None:
    script = _text(CANONICAL)

    assert 'SUITE_RUN_SET="trace_final26"' in script
    assert 'SUITE_DATASET_VIEW="all26"' in script
    assert script.count('--dataset-manifest-view "${SUITE_DATASET_VIEW}"') == 2
    assert script.count('--run-set "${SUITE_RUN_SET}"') == 2
    assert script.count('--suite "${SUITE}"') >= 6
    assert 'if [[ "${SUITE}" == "all26" ]]; then' in script
    assert "--run-set trace_final26" in script
    assert "--only mmvp" in script
    assert "--exact-only" in script
    assert "--expect-benchmark mmvp" in script
    assert 'tee "${LOG_ROOT}/hf_archive_verify_mmvp.log"' in script
    assert '[archive:local-only] remote init/upload disabled' in script
    assert 'remote_flush=deferred' in script


def test_endpoint_pool_disables_shared_compile_cache_by_default() -> None:
    script = _text(POOL_STARTER)

    assert 'VLLM_DISABLE_COMPILE_CACHE="${VLLM_DISABLE_COMPILE_CACHE:-1}"' in script
    assert 'VLLM_DISABLE_COMPILE_CACHE="${VLLM_DISABLE_COMPILE_CACHE}" \\' in script


def test_endpoint_pool_forwards_multimodal_generation_and_sitecustomize_settings() -> None:
    script = _text(POOL_STARTER)

    assert 'MM_PROCESSOR_KWARGS="${MM_PROCESSOR_KWARGS:-}"' in script
    assert 'server_args+=(--mm-processor-kwargs "${MM_PROCESSOR_KWARGS}")' in script
    assert 'GENERATION_CONFIG="${GENERATION_CONFIG:-}"' in script
    assert 'server_args+=(--generation-config "${GENERATION_CONFIG}")' in script
    assert 'VLLM_SITECUSTOMIZE_DIR="${VLLM_SITECUSTOMIZE_DIR:-' in script
    assert 'PYTHONPATH="${VLLM_SITECUSTOMIZE_DIR}:${PYTHONPATH:-}" \\' in script
    assert "ImageFile.LOAD_TRUNCATED_IMAGES = True" in _text(VLLM_SITECUSTOMIZE)
