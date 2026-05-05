"""chaos-cars-admin — Hermes plugin register hook.

Operator-deployed admin-signal agent for cars-pack@1. Skeleton; the
admin-engine and admin-cars skill are being authored in parallel. This
plugin does not operate the relay or issue NIP-58 badges.
"""

from __future__ import annotations

from typing import Any


def register(ctx: Any) -> None:
    """Install the cars-admin plugin into a Hermes runtime.

    Constraints (AGENTS.md rule 1, 5, and the admin-scope policy):
      * publishes only to the configured relay set
      * does NOT call seller/buyer MCP servers
      * does NOT operate strfry or issue/revoke NIP-58 badges
      * does NOT decrypt or store DM content
    """
    # 1. Admin engine (placeholder dep).
    engine_register = ctx.resolve_dependency("chaos-admin-engine")
    engine_register(ctx)

    # 2. Admin × cars skill.
    ctx.register_skill(
        path="verticals/cars-pack/skills/admin-cars/SKILL.md",
    )

    # 3. Pack contract.
    ctx.register_pack_contract(
        pack="cars-pack",
        version="1",
        schema_path="verticals/cars-pack/tag_schema.md",
    )

    # 4. Reputation MCP — admin reads attestations / publishes
    #    decisions through it.
    ctx.install_capability_mcp("reputation-mcp@1", tier="thorough")
