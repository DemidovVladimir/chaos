"""Layer-1 input sanitizer — buyer-side copy.

Identical contract to ``chaos_seller.input_safety``. Copied
across components per AGENTS.md § "Repository layout" so each
component installs independently.

Every untrusted text surface that reaches the planner passes through
``sanitize`` first. On the buyer side that includes:

- Listing ``content`` (the seller's free-form description on a
  NIP-99 event).
- The decrypted body of any incoming NIP-17 rumor (seller reply,
  counter-offer, etc.).
- The ``text`` field of every ``mcp.types.TextContent`` block
  returned from a ``tools/call`` against the seller's MCP server.
- Any string field present on an ``mcp.types.ImageContent`` or
  ``mcp.types.EmbeddedResource`` block (e.g. ``mimeType``, captions
  carried in adjacent ``TextContent`` blocks, or ``resource.uri``
  before it is touched on disk). Binary ``data`` / ``blob`` bytes
  are NOT passed through ``sanitize``; they are size-capped and
  written to disk by ``mcp_client``.

See ``../../../seller/src/chaos_seller/input_safety.py`` for
the full pipeline rationale.
"""

from __future__ import annotations

import re
import unicodedata

_RESERVED_TAGS = (
    "system",
    "assistant",
    "untrusted",
    "memory",
    "context",
    "tool",
    "policy",
    "secret",
)

_INVISIBLE_RE = re.compile(
    r"[​-‏"
    r"‪-‮"
    r"⁠-⁯"
    r"﻿]"
)

_RESERVED_TAG_RE = re.compile(
    r"</?(?:" + "|".join(_RESERVED_TAGS) + r")\b[^>]*>",
    re.IGNORECASE,
)

_INJECTION_PHRASES = (
    "ignore previous instructions",
    "disregard the above",
    "you are now",
    "system prompt",
    "developer mode",
    "jailbreak",
)

DEFAULT_MAX_CHARS = 8_000


def sanitize(
    text: str,
    *,
    source: str,
    key: str = "",
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """Run the full layer-1 sanitization pipeline.

    Args:
        text: Untrusted input.
        source: Identifier of where this came from
                (e.g. ``"seller_listing"``, ``"mcp_text_content"``,
                ``"nip17_reply"``).
        key: Optional disambiguating identifier (event id).
        max_chars: Hard cap on the output length.

    Returns:
        ``<untrusted source="..." key="...">...</untrusted>``.
    """
    raise NotImplementedError("input_safety.sanitize not implemented")


def is_suspicious(text: str) -> bool:
    """Pure detector for known injection phrases.

    Args:
        text: Input string (case-insensitive scan).

    Returns:
        True if any known phrase appears.
    """
    raise NotImplementedError("input_safety.is_suspicious not implemented")


def strip_reserved_tags(text: str) -> str:
    """Strip reserved-tag markup, keeping inner content."""
    raise NotImplementedError("input_safety.strip_reserved_tags not implemented")


def nfkc(text: str) -> str:
    """NFKC-normalize the string."""
    return unicodedata.normalize("NFKC", text)
