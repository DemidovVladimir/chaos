"""chaos-cars — Hermes plugin entry point.

Hermes' plugin loader (`hermes-agent/hermes_cli/plugins.py:614`)
imports this module as `hermes_plugins.cars` and calls
`register(ctx)` exactly once at startup, after parsing
`plugin.yaml`. `ctx` is a `PluginContext` instance defined at
`hermes-agent/hermes_cli/plugins.py:230`.

This file is the *real* `register()` — earlier scaffolds expected
a `register.py` and methods like `ctx.resolve_dependency` /
`ctx.register_pack_contract` / `ctx.install_capability_mcp` that
do **not** exist on Hermes' PluginContext (see
`hermes_integration_notes.md`). Don't reintroduce them here.

This is the *merged* cars plugin. Per `AGENTS.md` Rule 11 the cars
pack ships as a single role-flexible plugin — the host agent can
publish, subscribe, inquire, and serve from the same install. The
plugin registers *both* the offering-cars and seeking-cars skills
so Hermes can route into either based on user intent.

What we wire:

1. **Skills** — registers
   `verticals/cars-pack/skills/offering-cars/SKILL.md` and
   `verticals/cars-pack/skills/seeking-cars/SKILL.md` so
   `cars:offering` and `cars:seeking` are both resolvable inside
   Hermes (`PluginContext.register_skill`, plugins.py:544).
2. **Slash command** — `/cars status` for in-session presence
   (`PluginContext.register_command`, plugins.py:323).
3. **CLI subcommand** — `hermes cars {keygen,publish,subscribe,inquire,serve,status}`
   delegating to the working `mvp/agent_offering.py` and
   `mvp/agent_seeking.py` until the universal `chaos-agent` engine is
   implemented (`PluginContext.register_cli_command`, plugins.py:298).

AGENTS.md rules touched: Rule 1 (Nostr-only discovery), Rule 2
(MCP-only binary), Rule 3 (sovereign keys at `~/.chaos/`),
Rule 11 (plugin tier isolation: this plugin registers zero
`register_tool` calls — only the agent runtime exposes capabilities).
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
# When installed as a symlink to ~/.hermes/plugins/cars, the
# symlink's resolved location lives at
# <repo>/plugins/cars/src/chaos_cars/__init__.py,
# so the repo root is four parents up.
# ---------------------------------------------------------------------------

_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent.parent  # chaos/
_SKILL_OFFERING = _REPO_ROOT / "verticals" / "cars-pack" / "skills" / "offering-cars" / "SKILL.md"
_SKILL_SEEKING = _REPO_ROOT / "verticals" / "cars-pack" / "skills" / "seeking-cars" / "SKILL.md"
_MVP_OFFERING = _REPO_ROOT / "mvp" / "agent_offering.py"
_MVP_SEEKING = _REPO_ROOT / "mvp" / "agent_seeking.py"


# ---------------------------------------------------------------------------
# Slash command — visible inside a Hermes session
# ---------------------------------------------------------------------------


def _slash_status(_raw_args: str) -> str:
    """`/cars` slash handler. Reports plugin + env status."""
    relays = os.getenv("CHAOS_RELAYS", "<unset>")
    mcp_url = os.getenv("CHAOS_MCP_URL", "<unset>")
    keyfile = Path("~/.chaos/keys/agent.key").expanduser()
    skills = []
    skills.append(("offering-cars", "OK" if _SKILL_OFFERING.exists() else f"MISSING ({_SKILL_OFFERING})"))
    skills.append(("seeking-cars",  "OK" if _SKILL_SEEKING.exists()  else f"MISSING ({_SKILL_SEEKING})"))
    mvp_o = "OK" if _MVP_OFFERING.exists() else f"MISSING ({_MVP_OFFERING})"
    mvp_s = "OK" if _MVP_SEEKING.exists() else f"MISSING ({_MVP_SEEKING})"
    skill_lines = "\n".join(f"  skill[{name}]: {status}" for name, status in skills)
    return (
        f"chaos cars v{__version__}\n"
        f"  relays: {relays}\n"
        f"  mcp_url: {mcp_url}\n"
        f"  keyfile: {keyfile} ({'present' if keyfile.exists() else 'absent'})\n"
        f"{skill_lines}\n"
        f"  mvp agent_offering.py: {mvp_o}\n"
        f"  mvp agent_seeking.py:  {mvp_s}\n"
        "\n"
        "Run `hermes cars publish FILE.toml` to publish a listing.\n"
        "Run `hermes cars subscribe` to watch for matching listings.\n"
        "Run `hermes cars serve FILE.toml` to publish + listen + serve MCP."
    )


# ---------------------------------------------------------------------------
# CLI subcommand — `hermes cars …`
#
# We shell out to the MVP scripts (`mvp/agent_offering.py`,
# `mvp/agent_seeking.py`) because the universal `chaos-agent` engine
# is still scaffolding (NotImplementedError). When the engine ships
# we'll call its main directly instead. See
# hermes_integration_notes.md § "Future work".
# ---------------------------------------------------------------------------


def _cli_setup(subparser: argparse.ArgumentParser) -> None:
    """Build the argparse tree for `hermes cars`.

    Hermes calls this with the subparser the plugin manager created
    (plugins.py:298). Subcommands cover both offering and seeking
    sides since the merged plugin is symmetric.
    """
    subs = subparser.add_subparsers(dest="cars_cmd")

    p_keygen = subs.add_parser("keygen", help="Show / generate the agent keypair")
    p_keygen.set_defaults(func=_cli_dispatch)

    p_publish = subs.add_parser("publish", help="Publish a NIP-99 listing (offering side)")
    p_publish.add_argument("file", help="Path to a TOML listing definition")
    p_publish.set_defaults(func=_cli_dispatch)

    p_listen = subs.add_parser("listen", help="Listen for incoming NIP-17 inquiries (offering side)")
    p_listen.set_defaults(func=_cli_dispatch)

    p_serve = subs.add_parser(
        "serve",
        help="offering side: publish + listen + run the FastMCP HTTP+SSE server",
    )
    p_serve.add_argument("file", help="Path to a TOML listing definition")
    p_serve.set_defaults(func=_cli_dispatch)

    p_subscribe = subs.add_parser(
        "subscribe", help="Watch matching NIP-99 listings (seeking side)"
    )
    p_subscribe.set_defaults(func=_cli_dispatch)

    p_inquire = subs.add_parser(
        "inquire", help="Send an NIP-17 inquiry to a listing (seeking side)"
    )
    p_inquire.add_argument("event_id", help="NIP-99 event id (hex64) to inquire about")
    p_inquire.set_defaults(func=_cli_dispatch)

    p_status = subs.add_parser("status", help="Show plugin status")
    p_status.set_defaults(func=_cli_dispatch)

    # Default action when no subcommand given
    subparser.set_defaults(func=_cli_dispatch)


# Subcommands that route into the offering-side MVP script.
_OFFERING_CMDS = {"keygen", "publish", "listen", "serve"}
# Subcommands that route into the seeking-side MVP script.
_SEEKING_CMDS = {"subscribe", "inquire"}


def _cli_dispatch(args: argparse.Namespace) -> None:
    """Forward the parsed args to the relevant MVP script.

    The MVP scripts are self-contained and already do Nostr
    publishing, NIP-17 inquiry handling, and FastMCP serving.
    Until the universal agent engine is implemented, the plugin's
    job is to surface those scripts as Hermes-discoverable CLIs.
    """
    cmd = getattr(args, "cars_cmd", None)
    if not cmd:
        print(
            "Usage: hermes cars {keygen,publish,listen,serve,subscribe,inquire,status}",
            file=sys.stderr,
        )
        return

    if cmd == "status":
        print(_slash_status(""))
        return

    if cmd in _OFFERING_CMDS:
        target = _MVP_OFFERING
    elif cmd in _SEEKING_CMDS:
        target = _MVP_SEEKING
    else:
        print(f"[cars] unknown subcommand: {cmd}", file=sys.stderr)
        return

    if not target.exists():
        print(
            f"[cars] cannot find {target}.\n"
            f"       ensure the chaos repo is checked out and the plugin is "
            f"installed by symlinking into ~/.hermes/plugins/.",
            file=sys.stderr,
        )
        return

    argv = ["python3", str(target), cmd]
    if cmd in ("publish", "serve"):
        argv.append(args.file)
    elif cmd == "inquire":
        argv.append(args.event_id)

    try:
        rc = subprocess.call(argv, cwd=target.parent)
    except FileNotFoundError:
        print("[cars] python3 not found on PATH", file=sys.stderr)
        return
    if rc != 0:
        sys.exit(rc)


# ---------------------------------------------------------------------------
# register() — called by Hermes' plugin manager
# ---------------------------------------------------------------------------


def register(ctx: Any) -> None:
    """Wire the cars plugin into a Hermes runtime.

    Args:
        ctx: PluginContext instance (hermes_cli/plugins.py:230).
    """
    # 1. Skills — register both offering-cars and seeking-cars when they
    #    exist on disk. Hermes' register_skill raises FileNotFoundError
    #    otherwise (plugins.py:574).
    for skill_name, skill_path, description in [
        ("offering", _SKILL_OFFERING, "cars-pack@1 offering-side skill (publish + serve)."),
        ("seeking",  _SKILL_SEEKING,  "cars-pack@1 seeking-side skill (subscribe + inquire)."),
    ]:
        if skill_path.exists():
            try:
                ctx.register_skill(name=skill_name, path=skill_path, description=description)
                logger.info("cars: registered skill %s -> %s", skill_name, skill_path)
            except Exception as exc:
                logger.warning("cars: register_skill(%s) failed: %s", skill_name, exc)
        else:
            logger.warning(
                "cars: SKILL.md for %s not found at %s — skipping register_skill",
                skill_name, skill_path,
            )

    # 2. Slash command — `/cars`
    try:
        ctx.register_command(
            "cars",
            handler=_slash_status,
            description="chaos cars status and shortcuts.",
        )
    except Exception as exc:
        logger.warning("cars: register_command failed: %s", exc)

    # 3. CLI subcommand — `hermes cars …`
    try:
        ctx.register_cli_command(
            name="cars",
            help="chaos cars — symmetric publish / subscribe / inquire / serve",
            setup_fn=_cli_setup,
            handler_fn=_cli_dispatch,
            description=(
                "Publish NIP-99 car listings, watch for matching listings, send "
                "NIP-17 inquiries, and serve photos / inspection PDFs over MCP."
            ),
        )
    except Exception as exc:
        logger.warning("cars: register_cli_command failed: %s", exc)

    logger.info("cars plugin loaded (v%s)", __version__)
