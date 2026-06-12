"""Public indoor-room scene interface.

Rendering implementation lives in `rendering.py`; this module is
intentionally a drawing-free scene boundary.
"""

from __future__ import annotations

from . import rendering as _rendering
from ...shared.scene_interface import export_scene_interface

export_scene_interface(globals(), _rendering)
