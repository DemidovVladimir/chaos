"""Template register() for a role-vertical plugin.

Copy this file alongside the rest of the plugin scaffold and rename
the package to `chaos_<vertical>_<role>`.
"""
from __future__ import annotations

from typing import Any


def register(ctx: Any) -> None:
    """Wire engine + skill + pack contract + capability MCPs.

    Args:
        ctx: Hermes plugin install context. The exact shape is
            defined in the upstream Hermes plugin contract; here we
            just sketch the four calls every role-vertical plugin
            makes.
    """
    # 1. Pull in the universal engine.
    #    e.g. from chaos_buyer import register as engine_register
    #    engine_register(ctx)
    engine_register = ctx.resolve_dependency("<PLACEHOLDER_UNIVERSAL_ENGINE>")
    engine_register(ctx)

    # 2. Register this role-vertical's skill.
    ctx.register_skill(path="<PLACEHOLDER_SKILL_PATH>")

    # 3. Bind the pack contract — pins NIP-99 tag schema and MCP
    #    tool surface for the vertical.
    ctx.register_pack_contract(
        pack="<PLACEHOLDER_PACK>",
        version="<PLACEHOLDER_PACK_VERSION>",
        schema_path="<PLACEHOLDER_PACK_SCHEMA_PATH>",
    )

    # 4. Install capability MCPs. Each entry is resolved against
    #    shared-mcp/ first, then verticals/<vertical>-pack/mcp/.
    for mcp_ref in []:  # type: ignore[var-annotated]
        ctx.install_capability_mcp(mcp_ref)
