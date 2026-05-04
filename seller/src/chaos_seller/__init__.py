"""Hermes plugin entry point for the chaos seller agent.

This module exports ``register(ctx)``, the function Hermes' plugin
loader calls exactly once at startup. The function wires our tool
schemas to their handlers, ships the seller-cars skill, and registers
the ``hermes chaos-seller`` CLI subcommand.

If ``register()`` raises, Hermes logs the error and disables the
plugin without crashing the host. See the build-a-plugin guide for
the contract:

    hermes-agent/website/docs/guides/build-a-hermes-plugin.md

CLAUDE.md rules enforced here:
    - Rule 1: discovery is Nostr-only (no central registry).
    - Rule 2: binary content via MCP only.
    - Rule 3: identity stays in ``~/.chaos/keys/seller.key``.
    - Rule 7: NIP-17 in production paths; NIP-04 only in mvp/.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


def register(ctx) -> None:
    """Register tools, skill, and CLI subcommand with Hermes.

    This function is called by the Hermes plugin loader (see
    ``hermes_cli/plugins.py``). ``ctx`` is a ``PluginContext``
    instance exposing ``register_tool``, ``register_hook``,
    ``register_cli_command``, ``register_command``, and
    ``register_skill``.

    The wiring imports ``mcp_server`` (the FastMCP scaffold) so the
    seller's tool surface (cars-pack@1) is bootable from the same
    process that registers Hermes tools.

    Args:
        ctx: PluginContext provided by Hermes.

    Returns:
        None.

    Raises:
        Never. Any internal error is logged; Hermes treats a raising
        ``register()`` as a disable-this-plugin signal but the host
        keeps running.
    """
    # TODO(week-1, day-1): import schemas + handlers and wire them.
    # The full register() body lives in IMPLEMENTATION_PLAN.md §
    # "Hermes plugin entry-point shape". This stub keeps the import
    # path resolvable so Hermes can probe the entry point without
    # crashing on every wiring TODO.
    #
    # Day-2/3 wiring imports: mcp_server (FastMCP cars-pack@1 surface),
    # inquiry_listener, grant_policy, tools_inquire, tools_publish,
    # tools_negotiate.
    raise NotImplementedError(
        "chaos-seller register(ctx) not implemented yet — "
        "see seller/IMPLEMENTATION_PLAN.md."
    )
