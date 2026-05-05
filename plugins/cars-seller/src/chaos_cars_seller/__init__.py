"""chaos-cars-seller — Hermes plugin entry point.

Hermes' plugin loader (`hermes-agent/hermes_cli/plugins.py:614`)
imports this module as `hermes_plugins.cars_seller` and calls
`register(ctx)` exactly once at startup, after parsing
`plugin.yaml`. `ctx` is a `PluginContext` instance defined at
`hermes-agent/hermes_cli/plugins.py:230`.

This file is the *real* `register()` — earlier scaffolds expected
a `register.py` and methods like `ctx.resolve_dependency` /
`ctx.register_pack_contract` / `ctx.install_capability_mcp` that
do **not** exist on Hermes' PluginContext (see
`hermes_integration_notes.md`). Don't reintroduce them here.

What we actually wire:

1. **Skill**: registers `verticals/cars-pack/skills/seller-cars/SKILL.md`
   so `cars-seller:main` is resolvable inside Hermes
   (`PluginContext.register_skill`, plugins.py:544).
2. **Slash command**: `/cars-seller status` for in-session presence
   (`PluginContext.register_command`, plugins.py:323).
3. **CLI subcommand**: `hermes cars-seller {publish,listen,serve,status}`
   delegating to the working `mvp/seller.py` until the universal
   `chaos-seller` engine is implemented
   (`PluginContext.register_cli_command`, plugins.py:298).

AGENTS.md rules touched: Rule 1 (Nostr-only discovery), Rule 2
(MCP-only binary), Rule 3 (sovereign keys at `~/.chaos/`),
Rule 11 (toolset isolation: this plugin registers zero `register_tool`
calls — no buyer-side capability MCPs leak in).
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

# ---------------------------------------------------------------------------
# Path resolution — find the chaos repo root from this file.
#
# When installed as a symlink to ~/.hermes/plugins/cars-seller, the
# symlink's resolved location lives at
# <repo>/plugins/cars-seller/src/chaos_cars_seller/__init__.py,
# so the repo root is four parents up.
# ---------------------------------------------------------------------------

_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent.parent  # chaos/
_SKILL_PATH = _REPO_ROOT / "verticals" / "cars-pack" / "skills" / "seller-cars" / "SKILL.md"
_MVP_SELLER = _REPO_ROOT / "mvp" / "seller.py"


# ---------------------------------------------------------------------------
# Slash command — visible inside a Hermes session
# ---------------------------------------------------------------------------


def _slash_status(_raw_args: str) -> str:
    """`/cars-seller` slash handler. Reports plugin + env status."""
    relays = os.getenv("CHAOS_RELAYS", "<unset>")
    mcp_url = os.getenv("CHAOS_MCP_URL", "<unset>")
    keyfile = Path("~/.chaos/seller.key").expanduser()
    skill = "OK" if _SKILL_PATH.exists() else f"MISSING ({_SKILL_PATH})"
    mvp = "OK" if _MVP_SELLER.exists() else f"MISSING ({_MVP_SELLER})"
    return (
        f"chaos cars-seller v{__version__}\n"
        f"  relays: {relays}\n"
        f"  mcp_url: {mcp_url}\n"
        f"  keyfile: {keyfile} ({'present' if keyfile.exists() else 'absent'})\n"
        f"  skill: {skill}\n"
        f"  mvp seller.py: {mvp}\n"
        "\n"
        "Run `hermes cars-seller publish FILE.toml` to publish a listing.\n"
        "Run `hermes cars-seller serve FILE.toml` to publish + listen + serve MCP."
    )


# ---------------------------------------------------------------------------
# CLI subcommand — `hermes cars-seller …`
#
# For now we shell out to `python mvp/seller.py …` because the universal
# `chaos-seller` engine is still scaffolding (NotImplementedError).
# When the engine ships we'll call its main directly instead. See
# hermes_integration_notes.md § "Future work".
# ---------------------------------------------------------------------------


def _cli_setup(subparser: argparse.ArgumentParser) -> None:
    """Build the argparse tree for `hermes cars-seller`.

    Hermes calls this with the subparser the plugin manager created
    (plugins.py:298). We add child subcommands matching mvp/seller.py.
    """
    subs = subparser.add_subparsers(dest="cars_seller_cmd")

    p_keygen = subs.add_parser("keygen", help="Show / generate the seller keypair")
    p_keygen.set_defaults(func=_cli_dispatch)

    p_publish = subs.add_parser("publish", help="Publish a NIP-99 listing")
    p_publish.add_argument("file", help="Path to a TOML listing definition")
    p_publish.set_defaults(func=_cli_dispatch)

    p_listen = subs.add_parser("listen", help="Listen for incoming NIP-17 inquiries")
    p_listen.set_defaults(func=_cli_dispatch)

    p_serve = subs.add_parser(
        "serve",
        help="publish + listen + run the FastMCP HTTP+SSE server in one process",
    )
    p_serve.add_argument("file", help="Path to a TOML listing definition")
    p_serve.set_defaults(func=_cli_dispatch)

    p_status = subs.add_parser("status", help="Show plugin status")
    p_status.set_defaults(func=_cli_dispatch)

    # Default action when no subcommand given
    subparser.set_defaults(func=_cli_dispatch)


def _cli_dispatch(args: argparse.Namespace) -> None:
    """Forward the parsed args to mvp/seller.py via subprocess.

    The MVP seller is a self-contained script that already does
    Nostr publishing, NIP-17 inquiry handling, and FastMCP serving.
    Until the universal seller engine is implemented, the plugin's
    job is to surface that script as a Hermes-discoverable CLI.
    """
    cmd = getattr(args, "cars_seller_cmd", None)
    if not cmd:
        print(
            "Usage: hermes cars-seller {keygen,publish,listen,serve,status}",
            file=sys.stderr,
        )
        return

    if not _MVP_SELLER.exists():
        print(
            f"[cars-seller] cannot find mvp/seller.py at {_MVP_SELLER}.\n"
            f"             ensure the chaos repo is checked out and "
            f"the plugin is installed by symlinking into ~/.hermes/plugins/.",
            file=sys.stderr,
        )
        return

    if cmd == "status":
        print(_slash_status(""))
        return

    argv = ["python3", str(_MVP_SELLER), cmd]
    if cmd in ("publish", "serve"):
        argv.append(args.file)

    try:
        rc = subprocess.call(argv, cwd=_MVP_SELLER.parent)
    except FileNotFoundError:
        print("[cars-seller] python3 not found on PATH", file=sys.stderr)
        return
    if rc != 0:
        sys.exit(rc)


# ---------------------------------------------------------------------------
# register() — called by Hermes' plugin manager
# ---------------------------------------------------------------------------


def register(ctx: Any) -> None:
    """Wire the cars-seller plugin into a Hermes runtime.

    Args:
        ctx: PluginContext instance (hermes_cli/plugins.py:230).
    """
    # 1. Skill — only register if the file actually exists. Hermes'
    #    register_skill raises FileNotFoundError otherwise (plugins.py:574).
    if _SKILL_PATH.exists():
        try:
            ctx.register_skill(
                name="main",
                path=_SKILL_PATH,
                description="Seller-cars role skill (cars-pack@1).",
            )
            logger.info("cars-seller: registered skill %s", _SKILL_PATH)
        except Exception as exc:
            logger.warning("cars-seller: register_skill failed: %s", exc)
    else:
        logger.warning(
            "cars-seller: SKILL.md not found at %s — skipping register_skill",
            _SKILL_PATH,
        )

    # 2. Slash command — `/cars-seller`
    try:
        ctx.register_command(
            "cars-seller",
            handler=_slash_status,
            description="chaos cars-seller status and shortcuts.",
        )
    except Exception as exc:
        logger.warning("cars-seller: register_command failed: %s", exc)

    # 3. CLI subcommand — `hermes cars-seller …`
    try:
        ctx.register_cli_command(
            name="cars-seller",
            help="chaos cars-seller — publish listings, run seller MCP",
            setup_fn=_cli_setup,
            handler_fn=_cli_dispatch,
            description=(
                "Publish NIP-99 car listings, listen for inquiries over NIP-17, "
                "and serve photos / inspection PDFs from a per-seller FastMCP server."
            ),
        )
    except Exception as exc:
        logger.warning("cars-seller: register_cli_command failed: %s", exc)

    logger.info("cars-seller plugin loaded (v%s)", __version__)
