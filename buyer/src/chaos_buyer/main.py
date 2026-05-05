"""CLI entry: ``hermes chaos-buyer {watch, inquire, status}``.

Subcommands:

- ``watch`` — keep the REQ subscription open and surface matches.
- ``inquire ITEM_ID`` — send an inquiry for a known item id; await
  the seller's NIP-17 reply; for any granted asks, dial the
  listing's ``["mcp", url]`` tag with an MCP HTTP+SSE client and
  pull ``ImageContent`` / ``EmbeddedResource`` blocks via
  ``tools/call``.
- ``status`` — print configured filters, identity, recent matches.
- ``keygen`` — generate the buyer keypair if missing.
"""

from __future__ import annotations

import argparse


def setup_argparse(subparser: argparse.ArgumentParser) -> None:
    """Build the argparse tree for ``hermes chaos-buyer``.

    Args:
        subparser: argparse parser provided by Hermes.
    """
    subs = subparser.add_subparsers(dest="buyer_command")

    p_keygen = subs.add_parser("keygen", help="Show / generate the buyer keypair")
    p_keygen.set_defaults(func=cmd_keygen)

    p_watch = subs.add_parser("watch", help="Keep the REQ subscription open")
    p_watch.set_defaults(func=cmd_watch)

    p_inquire = subs.add_parser("inquire", help="Send an inquiry for an item")
    p_inquire.add_argument("item_id", help="The seller's d-tag value")
    p_inquire.set_defaults(func=cmd_inquire)

    p_status = subs.add_parser("status", help="Show plugin status")
    p_status.set_defaults(func=cmd_status)

    subparser.set_defaults(func=dispatch)


def dispatch(args: argparse.Namespace) -> None:
    """Default handler.

    Args:
        args: The parsed argparse namespace.
    """
    func = getattr(args, "func", None)
    if func is None or func is dispatch:
        print("Usage: hermes chaos-buyer {keygen,watch,inquire,status}")
        return
    func(args)


def cmd_keygen(args: argparse.Namespace) -> None:
    """Print or create the buyer identity.

    Args:
        args: Parsed argparse namespace (unused).
    """
    raise NotImplementedError("main.cmd_keygen not implemented")


def cmd_watch(args: argparse.Namespace) -> None:
    """Keep the subscription open in the foreground.

    Args:
        args: Parsed argparse namespace (unused).
    """
    raise NotImplementedError("main.cmd_watch not implemented")


def cmd_inquire(args: argparse.Namespace) -> None:
    """Send an inquiry for a single item id.

    Args:
        args: ``args.item_id`` is the seller's d-tag value.
    """
    raise NotImplementedError("main.cmd_inquire not implemented")


def cmd_status(args: argparse.Namespace) -> None:
    """Print configured filters, identity, recent matches.

    Args:
        args: Parsed argparse namespace (unused).
    """
    raise NotImplementedError("main.cmd_status not implemented")
