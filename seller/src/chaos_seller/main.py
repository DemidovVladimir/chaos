"""CLI entry: ``hermes chaos-seller {publish, listen, serve, status}``.

The seller plugin registers a CLI subcommand via ``ctx.register_cli_command``
(see ``__init__.py::register``). This module exposes the
``setup_argparse(subparser)`` and ``dispatch(args)`` callbacks the
plugin manager invokes.

Subcommands:

- ``publish FILE.toml`` — load a TOML listing, publish it to relays.
- ``listen`` — listen for inquiries; reply via the configured
  grant policy.
- ``serve FILE.toml`` — publish + listen + FastMCP HTTP+SSE server in
  one process. Useful for two-machine end-to-end tests.
- ``status`` — print configured relays, identity (npub), and recent
  publish / inquiry counts.
- ``keygen`` — generate the seller keypair if it doesn't exist.
"""
from __future__ import annotations

import argparse
from typing import Any


def setup_argparse(subparser: argparse.ArgumentParser) -> None:
    """Build the argparse tree for ``hermes chaos-seller``.

    Called by the Hermes plugin loader; matches the signature shown
    in build-a-plugin guide § "Register CLI commands".

    Args:
        subparser: The ``argparse`` parser provided by Hermes.
    """
    subs = subparser.add_subparsers(dest="seller_command")

    p_keygen = subs.add_parser("keygen", help="Show / generate the seller keypair")
    p_keygen.set_defaults(func=cmd_keygen)

    p_publish = subs.add_parser("publish", help="Publish a NIP-99 listing")
    p_publish.add_argument("file", help="Path to a TOML listing definition")
    p_publish.set_defaults(func=cmd_publish)

    p_listen = subs.add_parser("listen", help="Listen for incoming inquiries")
    p_listen.set_defaults(func=cmd_listen)

    p_serve = subs.add_parser(
        "serve",
        help="Publish + listen + run the FastMCP HTTP+SSE server",
    )
    p_serve.add_argument("file", help="Path to a TOML listing definition")
    p_serve.set_defaults(func=cmd_serve)

    p_status = subs.add_parser("status", help="Show plugin status")
    p_status.set_defaults(func=cmd_status)

    subparser.set_defaults(func=dispatch)


def dispatch(args: argparse.Namespace) -> None:
    """Default handler: dispatch to the chosen subcommand.

    Args:
        args: The parsed argparse namespace.
    """
    func = getattr(args, "func", None)
    if func is None or func is dispatch:
        print("Usage: hermes chaos-seller {keygen,publish,listen,serve,status}")
        return
    func(args)


def cmd_keygen(args: argparse.Namespace) -> None:
    """Print or create the seller identity.

    Args:
        args: Parsed argparse namespace (unused).
    """
    raise NotImplementedError("main.cmd_keygen not implemented")


def cmd_publish(args: argparse.Namespace) -> None:
    """Publish a single listing from a TOML file.

    Args:
        args: ``args.file`` is the path to the TOML listing.
    """
    raise NotImplementedError("main.cmd_publish not implemented")


def cmd_listen(args: argparse.Namespace) -> None:
    """Run the inquiry listener in the foreground.

    Args:
        args: Parsed argparse namespace (unused).
    """
    raise NotImplementedError("main.cmd_listen not implemented")


def cmd_serve(args: argparse.Namespace) -> None:
    """Publish, then run the inquiry listener and FastMCP server in one process.

    The serve loop boots the FastMCP HTTP+SSE server (see
    ``mcp_server.py``) alongside the NIP-17 inquiry listener so a
    single process exposes the full cars-pack@1 tool surface.

    Args:
        args: ``args.file`` is the path to the TOML listing.
    """
    raise NotImplementedError("main.cmd_serve not implemented")


def cmd_status(args: argparse.Namespace) -> None:
    """Print configured relays, identity, and recent counters.

    Args:
        args: Parsed argparse namespace (unused).
    """
    raise NotImplementedError("main.cmd_status not implemented")
