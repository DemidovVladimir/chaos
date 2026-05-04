"""Deprecated — see plugins/cars-seller/src/.../register.py for rationale.

The Hermes-shaped contract puts ``register(ctx)`` in the package's
``__init__.py``. This module keeps the legacy import path working.
"""
from __future__ import annotations

from chaos_cars_buyer import register  # noqa: F401

__all__ = ["register"]
