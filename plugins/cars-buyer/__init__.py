"""chaos cars-buyer — Hermes plugin shim.

See `plugins/cars-seller/__init__.py` for the rationale; this is the
buyer-side mirror. The real implementation lives under
`src/chaos_cars_buyer/__init__.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent
_SRC_DIR = _PLUGIN_DIR / "src"
if _SRC_DIR.is_dir() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from chaos_cars_buyer import register  # noqa: E402

__all__ = ["register"]
