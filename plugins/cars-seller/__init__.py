"""chaos cars-seller — Hermes plugin shim.

This file is what Hermes' plugin loader actually imports
(`hermes-agent/hermes_cli/plugins.py:992`). Hermes expects an
`__init__.py` next to `plugin.yaml`. The real implementation lives
under `src/chaos_cars_seller/__init__.py` so the plugin can
also be packaged as a wheel via this directory's `pyproject.toml`.
This shim just re-exports `register` from the nested package.

When Hermes discovers a directory plugin, it injects the directory
into ``sys.path`` via ``submodule_search_locations`` so relative
imports of subpackages work — but only when the package layout is
flat. Our layout has the package under ``src/``, so we add ``src``
to ``sys.path`` ourselves before importing.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent
_SRC_DIR = _PLUGIN_DIR / "src"
if _SRC_DIR.is_dir() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Import the real plugin module after sys.path is fixed.
from chaos_cars_seller import register  # noqa: E402

__all__ = ["register"]
