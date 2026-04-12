#!/usr/bin/env bash
set -euo pipefail

###############################################
# CONFIG – change these if your paths differ
###############################################
IMAGE="hiyouga/verl:ngc-th2.8.0-cu12.9-vllm0.11.0"
HOST_HOME="/home/shadeform"          # your home dir on the VM
WORKSPACE="${HOST_HOME}"             # what we mount into /workspace in the container
CODE_DIR="${WORKSPACE}/trace"       # your trace repo
HF_CACHE="${HOST_HOME}/.cache/huggingface"

###############################################
# 0. Basic sanity checks
###############################################
echo "[*] Checking nvidia-smi on host..."
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "[!] nvidia-smi not found on host. GPU driver may be missing. Abort."
  exit 1
fi

nvidia-smi || {
  echo "[!] nvidia-smi failed on host. Something is wrong with GPU/driver. Abort."
  exit 1
}

if [ ! -d "${CODE_DIR}" ]; then
  echo "[!] CODE_DIR does not exist: ${CODE_DIR}"
  echo "    Make sure your trace repo is at that path or edit CODE_DIR in this script."
  exit 1
fi

mkdir -p "${HF_CACHE}"

###############################################
# 1. Install NVIDIA Container Toolkit
###############################################
echo "[*] Installing NVIDIA Container Toolkit..."

sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg

# Add NVIDIA repo + key
if [ ! -f /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg ]; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
fi

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y nvidia-container-toolkit

###############################################
# 2. Configure Docker to use NVIDIA runtime
###############################################
echo "[*] Configuring Docker to use NVIDIA runtime..."

sudo nvidia-ctk runtime configure --runtime=docker

echo "[*] Restarting Docker..."
sudo systemctl restart docker || sudo systemctl start docker

###############################################
# 3. Test GPU inside a simple CUDA container
###############################################
echo "[*] Testing GPU access inside Docker..."

docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi || {
  echo "[!] Docker still cannot use GPU. Check Docker + NVIDIA setup."
  exit 1
}

echo "[+] GPU is visible inside Docker."

###############################################
# 4. Pull verl image
###############################################
echo "[*] Pulling verl image: ${IMAGE}"
docker pull "${IMAGE}"

###############################################
# 5. Run verl container (interactive shell)
###############################################
echo "[*] Launching verl container with:"
echo "    Image: ${IMAGE}"
echo "    Host mount: ${WORKSPACE} -> /workspace"
echo "    Working dir: /workspace/trace"
echo
echo "When the container starts, you can run:"
echo "    cd /workspace/trace"
echo "    bash examples/qwen3_4b_math_grpo.sh"
echo

docker run --gpus all -it --rm \
  --ipc=host \
  --shm-size=16g \
  -v "${WORKSPACE}":/workspace \
  -v "${HF_CACHE}":/root/.cache/huggingface \
  -w /workspace/trace \
  "${IMAGE}" \
  bash
