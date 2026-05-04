"""Deprecated — kept for back-compat with the earlier scaffold.

The earlier docs pointed at
``chaos_cars_seller.register:register``. The Hermes-shaped
plugin contract puts ``register(ctx)`` in the package's
``__init__.py`` (``hermes-agent/hermes_cli/plugins.py:953``), so
that's where the real implementation now lives.

This module just re-exports the function so any external code that
imported it from the old path keeps working.
"""
from __future__ import annotations

from chaos_cars_seller import register  # noqa: F401

__all__ = ["register"]
