"""Per-tool grant policy for incoming MCP tool calls.

The policy table comes from
``verticals/cars-pack/skills/seller-cars/SKILL.md`` § "Inquiry-handling
policy". This module is the executable form of that table — pure
functions, no I/O, fully testable.

The seller's MCP server (see ``mcp_server.py``) consults this module
on every ``tools/call`` from a buyer's agent. Each cars-pack@1 tool
gets a default decision; some tools also have per-argument decisions
(e.g. ``request_photos(kinds=["license_plate"])`` always escalates).

Decision categories:

- ``GRANT`` — execute the tool call; return its result (text,
  ``ImageContent`` blocks, or ``EmbeddedResource`` blocks).
- ``ASK_USER`` — block until the user explicitly grants this tool
  call for this specific buyer.
- ``DENY`` — refuse the tool call with a one-line ``denial_reason``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .catalog import Item


class Decision(str, Enum):
    """Possible per-tool-call decisions."""

    GRANT = "grant"
    ASK_USER = "ask_user"
    DENY = "deny"

    def is_grant(self) -> bool:
        """True when this decision lets the tool call proceed.

        Returns:
            True for ``GRANT``; False for ``ASK_USER`` and ``DENY``.
        """
        return self is Decision.GRANT


# Default decisions for every cars-pack@1 tool. Keys MUST match the
# tool names exposed by ``mcp_server.py`` exactly.
DEFAULT_TOOL_TABLE: dict[str, Decision] = {
    # Core cars-pack@1 surface
    "view_listing": Decision.GRANT,
    "request_photos": Decision.GRANT,
    "request_inspection_report": Decision.GRANT,
    "request_vin": Decision.ASK_USER,
    "submit_offer": Decision.GRANT,
    "cancel_inquiry": Decision.GRANT,
    # Optional cars-pack@1 tools
    "request_test_drive_slots": Decision.GRANT,
    "request_inspection_at_shop": Decision.GRANT,
    "request_delivery_options": Decision.GRANT,
}

# Per-argument overrides keyed by (tool_name, arg_name, arg_value).
# Triggered when the call's arguments match the key — escalates the
# decision regardless of the default. Example: photos requested with
# ``kinds=["license_plate"]`` always need user confirmation.
PER_ARG_OVERRIDES: dict[tuple[str, str, str], Decision] = {
    ("request_photos", "kinds", "license_plate"): Decision.ASK_USER,
    ("request_photos", "kinds", "license_plate_blurred"): Decision.ASK_USER,
}

# Tools that ALWAYS escalate to user confirmation even if the table
# above says otherwise. Configurable via ``SellerConfig.grant_policy
# .always_user_confirm``.
ALWAYS_USER_CONFIRM: frozenset[str] = frozenset(
    {"request_vin", "request_pickup_address", "request_phone_number"}
)


@dataclass(frozen=True, slots=True)
class GrantOutcome:
    """Result of evaluating one MCP tool call.

    Attributes:
        tool: The tool name (e.g. ``"request_photos"``).
        decision: The chosen ``Decision``.
        reason: One-line explanation, used for the
                ``denial_reason`` field on denials and for the
                ``hint`` shown to the user on ``ASK_USER``.
    """

    tool: str
    decision: Decision
    reason: str = ""


def decide(
    tool: str,
    arguments: dict[str, Any],
    item: Item,
    *,
    always_user_confirm: frozenset[str] = ALWAYS_USER_CONFIRM,
) -> GrantOutcome:
    """Evaluate a single MCP tool call against the policy.

    Args:
        tool: The tool name (e.g. ``"request_photos"``).
        arguments: The arguments dict from the ``tools/call`` request.
            Inspected for per-argument overrides (e.g. license-plate
            photos).
        item: The item being asked about.
        always_user_confirm: Override set of tools that must escalate
            to the user. Defaults to ``ALWAYS_USER_CONFIRM``.

    Returns:
        A ``GrantOutcome`` with the policy decision and a one-line
        reason. Unknown tools default to ``DENY`` with reason
        ``"unknown_tool"``.
    """
    raise NotImplementedError("grant_policy.decide not implemented")


def evaluate(
    calls: list[tuple[str, dict[str, Any]]],
    item: Item,
    *,
    always_user_confirm: frozenset[str] = ALWAYS_USER_CONFIRM,
) -> list[GrantOutcome]:
    """Evaluate a batch of pending tool calls.

    Args:
        calls: Ordered list of ``(tool_name, arguments)`` pairs.
        item: The item.
        always_user_confirm: Override set; see ``decide()``.

    Returns:
        One ``GrantOutcome`` per input call, in the same order.
    """
    raise NotImplementedError("grant_policy.evaluate not implemented")
