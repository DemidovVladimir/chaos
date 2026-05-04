"""Append-only conversation log under ``~/.chaos/buyer/inbox/``.

One JSONL file per conversation:
``~/.chaos/buyer/inbox/<conversation_id>.jsonl``.

Each line is a JSON object: ``{ts, role, kind, payload, ...}``.
Per-conversation entries record both NIP-17 rumor exchanges (the
inquiry + reply) and per-MCP-tool-call audit rows: when the buyer
opens an MCP HTTP+SSE session against the seller's ``["mcp", url]``
tag, every ``tools/list`` and ``tools/call`` invocation gets a row
(tool name, arguments, content-block summary, byte counts), and
every response writes one row referencing the saved bytes.

Bytes themselves (photos, PDFs) live alongside the JSONL under
``~/.chaos/buyer/inbox/<conversation_id>/{photos,documents}/``
— they are written by ``mcp_client``, not this module.

Per CLAUDE.md rule 5 ("No data custody"), retention is bounded.
Default: cleartext payloads are pruned after 7 days, leaving only
the metadata (event id / tool name, role, kind, timestamp).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_INBOX_DIR = Path.home() / ".chaos" / "buyer" / "inbox"
DEFAULT_RETENTION_DAYS = 7


@dataclass(frozen=True, slots=True)
class InboxEntry:
    """One line in a conversation JSONL.

    Attributes:
        conversation_id: Either an item id (one-conversation-per-item)
                         or a session id minted for an MCP-only flow.
        ts: Unix seconds.
        role: ``"me"`` (buyer) or ``"seller"``.
        kind: e.g. ``"inquiry"``, ``"reply"``, ``"counter"``,
              ``"mcp_tools_list"``, ``"mcp_tool_call"``,
              ``"mcp_tool_response"``.
        payload: Free-form JSON-serializable dict.
    """

    conversation_id: str
    ts: int
    role: str
    kind: str
    payload: dict


def append(
    entry: InboxEntry,
    *,
    inbox_dir: Path = DEFAULT_INBOX_DIR,
) -> Path:
    """Append a JSON line to the conversation file.

    Args:
        entry: The entry to write.
        inbox_dir: Inbox root.

    Returns:
        Path to the JSONL file written.

    Raises:
        OSError: on filesystem failure.
    """
    raise NotImplementedError("inbox.append not implemented")


def read(
    conversation_id: str,
    *,
    inbox_dir: Path = DEFAULT_INBOX_DIR,
) -> list[InboxEntry]:
    """Return all entries for a conversation in chronological order.

    Args:
        conversation_id: Conversation id.
        inbox_dir: Inbox root.

    Returns:
        List of ``InboxEntry``. Empty if the file doesn't exist.
    """
    raise NotImplementedError("inbox.read not implemented")


def retention_sweep(
    *,
    inbox_dir: Path = DEFAULT_INBOX_DIR,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> int:
    """Strip cleartext payloads from entries older than ``retention_days``.

    Args:
        inbox_dir: Inbox root.
        retention_days: Days of cleartext retention. Older entries
                        retain only their metadata (id, role, kind,
                        ts). Photos / documents on disk are NOT
                        affected by this sweep — those follow the
                        per-item user-driven cleanup flow.

    Returns:
        Number of entries pruned.
    """
    raise NotImplementedError("inbox.retention_sweep not implemented")


def _path_for(conversation_id: str, inbox_dir: Path) -> Path:
    """Return the JSONL path for a conversation.

    Args:
        conversation_id: Conversation id (must not contain ``/`` or
                         ``..``).
        inbox_dir: Inbox root.

    Returns:
        Path to the JSONL file.

    Raises:
        ValueError: if ``conversation_id`` is unsafe.
    """
    if "/" in conversation_id or ".." in conversation_id:
        raise ValueError(f"unsafe conversation_id: {conversation_id!r}")
    return inbox_dir / f"{conversation_id}.jsonl"


def _serialize(entry: InboxEntry) -> str:
    """JSON-serialize a single entry.

    Args:
        entry: The entry.

    Returns:
        A JSON string with no trailing newline.
    """
    return json.dumps({
        "conversation_id": entry.conversation_id,
        "ts": entry.ts,
        "role": entry.role,
        "kind": entry.kind,
        "payload": entry.payload,
    }, default=str)
