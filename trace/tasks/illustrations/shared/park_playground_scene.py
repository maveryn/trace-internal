"""Public park/playground scene interface.

Rendering implementation lives in `park_playground_rendering.py`; this module
is intentionally a drawing-free scene boundary.
"""

from __future__ import annotations

from . import park_playground_rendering as _rendering
from .scene_interface import export_scene_interface

export_scene_interface(globals(), _rendering)
