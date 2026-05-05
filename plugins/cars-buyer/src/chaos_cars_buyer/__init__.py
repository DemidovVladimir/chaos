"""chaos-cars-buyer — Hermes plugin entry point.

Hermes' plugin loader (`hermes-agent/hermes_cli/plugins.py:614`)
imports this module and calls `register(ctx)` once at startup.
`ctx` is a `PluginContext` (plugins.py:230).

This file replaces the earlier scaffold which called
`ctx.resolve_dependency` / `ctx.register_pack_contract` /
`ctx.install_capability_mcp` — none of those exist on Hermes'
PluginContext. See `hermes_integration_notes.md` for the real API.

Wiring (modest scope):

1. Skill: `verticals/cars-pack/skills/buyer-cars/SKILL.md` →
   resolvable as `cars-buyer:main`.
2. Slash command: `/cars-buyer status`.
3. CLI subcommand: `hermes cars-buyer {watch,inquire,status,keygen}`
   delegating to `mvp/buyer.py`.

AGENTS.md rules touched: Rule 11 (no `mcp_serve`-shaped tools here;
this plugin is buyer-side only), Rule 2 (binary content stays
inside MCP responses, not stored long-term), Rule 7 (NIP-17 in
production paths once mvp/buyer.py upgrades).
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent.parent  # chaos/
_SKILL_PATH = _REPO_ROOT / "verticals" / "cars-pack" / "skills" / "buyer-cars" / "SKILL.md"
_MVP_BUYER = _REPO_ROOT / "mvp" / "buyer.py"


# ---------------------------------------------------------------------------
# Slash command
# ---------------------------------------------------------------------------


def _slash_status(_raw_args: str) -> str:
    relays = os.getenv("CHAOS_RELAYS", "<unset>")
    keyfile = Path("~/.chaos/buyer.key").expanduser()
    skill = "OK" if _SKILL_PATH.exists() else f"MISSING ({_SKILL_PATH})"
    mvp = "OK" if _MVP_BUYER.exists() else f"MISSING ({_MVP_BUYER})"
    return (
        f"chaos cars-buyer v{__version__}\n"
        f"  relays: {relays}\n"
        f"  keyfile: {keyfile} ({'present' if keyfile.exists() else 'absent'})\n"
        f"  skill: {skill}\n"
        f"  mvp buyer.py: {mvp}\n"
        "\n"
        "Run `hermes cars-buyer watch` to subscribe to new car listings.\n"
        "Run `hermes cars-buyer inquire ITEM_ID` to ask a seller for photos / inspection."
    )


# ---------------------------------------------------------------------------
# CLI — `hermes cars-buyer …`
# ---------------------------------------------------------------------------


def _cli_setup(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="cars_buyer_cmd")

    p_keygen = subs.add_parser("keygen", help="Show / generate the buyer keypair")
    p_keygen.set_defaults(func=_cli_dispatch)

    p_watch = subs.add_parser("watch", help="Keep the REQ subscription open and surface matches")
    p_watch.set_defaults(func=_cli_dispatch)

    p_inquire = subs.add_parser("inquire", help="Send an inquiry for a known item id")
    p_inquire.add_argument("item_id", help="The seller's d-tag value")
    p_inquire.set_defaults(func=_cli_dispatch)

    p_status = subs.add_parser("status", help="Show plugin status")
    p_status.set_defaults(func=_cli_dispatch)

    subparser.set_defaults(func=_cli_dispatch)


def _cli_dispatch(args: argparse.Namespace) -> None:
    cmd = getattr(args, "cars_buyer_cmd", None)
    if not cmd:
        print(
            "Usage: hermes cars-buyer {keygen,watch,inquire,status}",
            file=sys.stderr,
        )
        return

    if not _MVP_BUYER.exists():
        print(
            f"[cars-buyer] cannot find mvp/buyer.py at {_MVP_BUYER}.\n"
            f"            ensure the chaos repo is checked out and "
            f"the plugin is installed by symlinking into ~/.hermes/plugins/.",
            file=sys.stderr,
        )
        return

    if cmd == "status":
        print(_slash_status(""))
        return

    argv = ["python3", str(_MVP_BUYER), cmd]
    if cmd == "inquire":
        argv.append(args.item_id)

    try:
        rc = subprocess.call(argv, cwd=_MVP_BUYER.parent)
    except FileNotFoundError:
        print("[cars-buyer] python3 not found on PATH", file=sys.stderr)
        return
    if rc != 0:
        sys.exit(rc)


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


def register(ctx: Any) -> None:
    """Wire the cars-buyer plugin into Hermes."""
    if _SKILL_PATH.exists():
        try:
            ctx.register_skill(
                name="main",
                path=_SKILL_PATH,
                description="Buyer-cars role skill (cars-pack@1).",
            )
            logger.info("cars-buyer: registered skill %s", _SKILL_PATH)
        except Exception as exc:
            logger.warning("cars-buyer: register_skill failed: %s", exc)
    else:
        logger.warning(
            "cars-buyer: SKILL.md not found at %s — skipping register_skill",
            _SKILL_PATH,
        )

    try:
        ctx.register_command(
            "cars-buyer",
            handler=_slash_status,
            description="chaos cars-buyer status and shortcuts.",
        )
    except Exception as exc:
        logger.warning("cars-buyer: register_command failed: %s", exc)

    try:
        ctx.register_cli_command(
            name="cars-buyer",
            help="chaos cars-buyer — watch listings, inquire over MCP",
            setup_fn=_cli_setup,
            handler_fn=_cli_dispatch,
            description=(
                "Subscribe to NIP-99 car listings, send NIP-17 inquiries, "
                "and pull photos / inspection PDFs from sellers' MCP servers."
            ),
        )
    except Exception as exc:
        logger.warning("cars-buyer: register_cli_command failed: %s", exc)

    logger.info("cars-buyer plugin loaded (v%s)", __version__)
