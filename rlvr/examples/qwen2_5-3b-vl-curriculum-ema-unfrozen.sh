#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FREEZE_VISION_TOWER=false bash "${SCRIPT_DIR}/qwen2_5-3b-vl-curriculum-ema.sh"
