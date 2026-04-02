#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKERFILE_PATH="${SCRIPT_DIR}/Dockerfile.qwen3_5"

IMAGE_TAG="${IMAGE_TAG:-trace-rlvr:qwen3_5}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-${REPO_ROOT}}"
HF_CACHE="${HF_CACHE:-${HOME}/.cache/huggingface}"
BUILD_IMAGE="${BUILD_IMAGE:-1}"

echo "[*] Checking host prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "[!] docker not found"; exit 1; }
command -v nvidia-smi >/dev/null 2>&1 || { echo "[!] nvidia-smi not found"; exit 1; }
nvidia-smi >/dev/null || { echo "[!] nvidia-smi failed"; exit 1; }

if [[ ! -f "${DOCKERFILE_PATH}" ]]; then
  echo "[!] Dockerfile not found: ${DOCKERFILE_PATH}"
  exit 1
fi

mkdir -p "${HF_CACHE}"

if [[ "${BUILD_IMAGE}" == "1" ]]; then
  echo "[*] Building ${IMAGE_TAG} from ${DOCKERFILE_PATH}"
  docker build -t "${IMAGE_TAG}" -f "${DOCKERFILE_PATH}" "${SCRIPT_DIR}"
fi

echo "[*] Launching ${IMAGE_TAG}"
echo "    Workspace mount: ${WORKSPACE_ROOT} -> /workspace/trace"
echo "    HF cache: ${HF_CACHE} -> /root/.cache/huggingface"
echo "    Suggested first checks inside the container:"
echo "      cd /workspace/trace/rlvr"
echo "      python scripts/check_qwen3_5_runtime.py"
echo "      bash trace-scripts/trace_qwen3_5_0p8b_base_answer_evidence.sh"

docker run --gpus all -it --rm \
  --ipc=host \
  --shm-size=16g \
  -v "${WORKSPACE_ROOT}":/workspace/trace \
  -v "${HF_CACHE}":/root/.cache/huggingface \
  -w /workspace/trace/rlvr \
  "${IMAGE_TAG}" \
  bash
