"""Public transit-terminal scene interface.

Rendering implementation lives in `transit_terminal_rendering.py`; this module
is intentionally a drawing-free scene boundary.
"""

from __future__ import annotations

from . import transit_terminal_rendering as _rendering
from .scene_interface import export_scene_interface

export_scene_interface(globals(), _rendering)
