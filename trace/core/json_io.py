"""Shared JSON file writing helpers with deterministic formatting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_file(path: Path, payload: Any) -> None:
    """Write one JSON file with stable formatting and key ordering."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
