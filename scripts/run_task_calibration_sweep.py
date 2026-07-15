#!/usr/bin/env python3
"""CLI wrapper for the Trace task calibration sweep."""

from __future__ import annotations

from trace.core import task_calibration_sweep as _impl


__all__ = [name for name in dir(_impl) if not name.startswith("__")]
globals().update({name: getattr(_impl, name) for name in __all__})


if __name__ == "__main__":
    raise SystemExit(_impl.main())
