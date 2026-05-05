"""chaos-pro — cross-vertical seeking agent upgrade.

Pure configuration-flip plugin. At install time it enumerates the
installed seeking agent plugins (any plugin whose name matches
`chaos-*-seeking agent`) and overrides each one's capability-MCP
tier from `fast` to `thorough`. The same subscription / x402 entry
covers every vertical the user has installed.
"""

from __future__ import annotations

from typing import Any

MCP_OVERRIDES = {
    "reverse-image-mcp": {"tier": "thorough"},
    "market-comp-mcp": {"tier": "thorough", "window_days": 180},
    "reputation-mcp": {"tier": "thorough", "wot_depth": 4, "onchain_stake": True},
}


def register(ctx: Any) -> None:
    """Install the cross-vertical pro upgrade."""
    # 1. Validate subscription / x402 entitlement (delegated to the
    #    engine layer; no money flows through this plugin).
    ctx.validate_entitlement(plugin="chaos-pro")

    # 2. Find every installed seeking agent plugin and flip pro_mode on.
    for buyer_plugin in ctx.list_installed(matching="chaos-*-seeking agent"):
        ctx.update_plugin_config(buyer_plugin, {"pro_mode": True})

    # 3. Apply per-MCP overrides globally.
    for mcp_name, overrides in MCP_OVERRIDES.items():
        ctx.set_capability_mcp_overrides(mcp_name, overrides)
