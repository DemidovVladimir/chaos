"""Hermes plugin entry point for the chaos buyer agent.

Exports ``register(ctx)`` per the build-a-plugin contract:

    hermes-agent/website/docs/guides/build-a-hermes-plugin.md

Mirrors the seller plugin's shape but wires the buyer-side tool
surface (subscribe, inquire, negotiate) and ships the buyer-cars
skill.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


def register(ctx) -> None:
    """Register tools, skill, and CLI subcommand with Hermes.

    Args:
        ctx: PluginContext provided by Hermes.

    Returns:
        None.

    Raises:
        Never. Errors propagate as plugin-disable signals to Hermes
        but are otherwise non-fatal.
    """
    raise NotImplementedError(
        "chaos-buyer register(ctx) not implemented yet — "
        "see buyer/IMPLEMENTATION_PLAN.md."
    )
