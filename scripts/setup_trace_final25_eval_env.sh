#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-/home/shadeform/venv/bin/python}"
TARGET="${EVAL_DEPS_ROOT:-${REPO_ROOT}/.tmp/eval_deps}"
REQUIREMENTS="${REPO_ROOT}/evaluation/final25/requirements-eval.txt"
VLMEVALKIT_ROOT="${REPO_ROOT}/external/VLMEvalKit"
VLMEVALKIT_COMMIT="a8b12bf1c3737a33fc1de967c202f9c592b22e86"
VERIFY_ONLY=0

if [[ "${1:-}" == "--verify-only" ]]; then
  VERIFY_ONLY=1
elif [[ $# -gt 0 ]]; then
  echo "usage: $0 [--verify-only]" >&2
  exit 2
fi

if [[ "${VERIFY_ONLY}" == "0" ]]; then
  if [[ ! -d "${VLMEVALKIT_ROOT}/.git" ]]; then
    git clone https://github.com/open-compass/VLMEvalKit.git "${VLMEVALKIT_ROOT}"
  fi
  if [[ "$(git -C "${VLMEVALKIT_ROOT}" rev-parse HEAD)" != "${VLMEVALKIT_COMMIT}" ]]; then
    if [[ -n "$(git -C "${VLMEVALKIT_ROOT}" status --porcelain)" ]]; then
      echo "[fatal] VLMEvalKit has local changes at the wrong commit: ${VLMEVALKIT_ROOT}" >&2
      exit 1
    fi
    git -C "${VLMEVALKIT_ROOT}" fetch origin "${VLMEVALKIT_COMMIT}"
    git -C "${VLMEVALKIT_ROOT}" checkout --detach "${VLMEVALKIT_COMMIT}"
  fi
  mkdir -p "${TARGET}"
  "${PYTHON_BIN}" -m pip install --disable-pip-version-check --target "${TARGET}" \
    --no-deps --requirement "${REQUIREMENTS}"
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/apply_vlmevalkit_trace_extensions.py"
fi

if [[ ! -d "${TARGET}" ]]; then
  echo "[fatal] missing evaluation dependency target: ${TARGET}" >&2
  echo "run: ${REPO_ROOT}/scripts/setup_trace_final25_eval_env.sh" >&2
  exit 1
fi
if [[ ! -d "${VLMEVALKIT_ROOT}/.git" ]]; then
  echo "[fatal] missing official VLMEvalKit checkout: ${VLMEVALKIT_ROOT}" >&2
  exit 1
fi
if [[ "$(git -C "${VLMEVALKIT_ROOT}" rev-parse HEAD)" != "${VLMEVALKIT_COMMIT}" ]]; then
  echo "[fatal] VLMEvalKit HEAD is not pinned to ${VLMEVALKIT_COMMIT}" >&2
  exit 1
fi

export PYTHONPATH="${TARGET}:${REPO_ROOT}:${REPO_ROOT}/scripts:${VLMEVALKIT_ROOT}:${VLMEVALKIT_ROOT}/scripts:${PYTHONPATH:-}"
"${PYTHON_BIN}" - <<'PY'
import importlib
from importlib.metadata import version

for module in (
    "vlmeval",
    "pyarrow",
    "huggingface_hub",
    "json_repair",
    "math_verify",
    "openpyxl",
    "pandas",
    "requests",
    "torch",
    "transformers",
    "vllm",
    "xlsxwriter",
):
    importlib.import_module(module)
expected = {
    "antlr4-python3-runtime": "4.11.1",
    "huggingface-hub": "0.36.2",
    "openpyxl": "3.1.5",
    "pandas": "2.3.3",
    "pyarrow": "24.0.0",
    "requests": "2.34.2",
    "torch": "2.8.0",
    "transformers": "4.57.6",
    "vllm": "0.10.2",
    "XlsxWriter": "3.2.9",
}
for distribution, wanted in expected.items():
    actual = version(distribution).split("+", 1)[0]
    if actual != wanted:
        raise RuntimeError(f"{distribution}=={wanted} is required, found {actual}")
from sympy import Rational, simplify
from sympy.parsing.latex import parse_latex

if simplify(parse_latex(r"\frac{1}{2}") - Rational(1, 2)) != 0:
    raise RuntimeError("SymPy LaTeX parsing preflight failed")
print("[eval-env:ok] pinned VLMEvalKit and Final25 imports are available")
PY
