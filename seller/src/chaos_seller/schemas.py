"""Tool schemas — what the LLM sees for each Hermes tool.

Each constant is a JSON-schema dict the Hermes plugin loader passes
to ``ctx.register_tool()``. Descriptions follow the build-a-plugin
guide rule: "Be specific about what it does and when to use it."

CLAUDE.md rule 6 forbids any tool that resells third-party data. Our
tool surface is intentionally narrow.
"""
from __future__ import annotations

PUBLISH_ITEM = {
    "name": "publish_item",
    "description": (
        "Publish a NIP-99 (kind-30402) classified listing for one of "
        "the user's local items to the seller's configured Nostr "
        "relays. Builds the event from the local manifest, mines "
        "≥ 20-bit NIP-13 PoW, signs with the seller's identity, and "
        "publishes. Returns the event id and the relays that "
        "accepted it. Use after the user has confirmed the listing "
        "draft."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {
                "type": "string",
                "description": "UUID of a local item under ~/.chaos/items/",
            },
        },
        "required": ["item_id"],
    },
}

ARCHIVE_ITEM = {
    "name": "archive_item",
    "description": (
        "Archive a previously-published listing. Republishes the "
        "kind-30402 event with status='archived' and emits a NIP-09 "
        "deletion request. Use when the user wants to take the "
        "listing down without selling (e.g. reconsidered)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "reason": {
                "type": "string",
                "description": "Short reason; stored locally only.",
            },
        },
        "required": ["item_id"],
    },
}

UPDATE_ITEM = {
    "name": "update_item",
    "description": (
        "Update an existing listing. Edits the local manifest with "
        "the supplied patch and republishes the kind-30402 event "
        "with the same `d` tag — cooperative relays replace the "
        "previous version. Use for price changes, status updates "
        "(reserved/sold), or description tweaks."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "patch": {
                "type": "object",
                "description": "Subset of item fields to overwrite.",
            },
        },
        "required": ["item_id", "patch"],
    },
}

HANDLE_INQUIRY = {
    "name": "handle_inquiry",
    "description": (
        "Process a NIP-17 inquiry from a buyer. Decrypts the "
        "mcp_inquiry_open rumor, sanitizes free text, binds the "
        "buyer's session_token to their pubkey, and runs each "
        "pending MCP tool call through the per-tool grant policy. "
        "For tool calls tagged ASK_USER, the tool emits notify_user "
        "calls and waits for explicit approval before allowing the "
        "FastMCP server to return a result. Use whenever a new "
        "gift-wrapped inquiry arrives in the inbox."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_token": {"type": "string"},
            "calls": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string"},
                        "arguments": {"type": "object"},
                    },
                    "required": ["tool"],
                },
            },
        },
        "required": ["session_token", "calls"],
    },
}

GRANT_ASKS = {
    "name": "grant_asks",
    "description": (
        "Explicitly grant the supplied list of pending MCP tool "
        "calls for a specific buyer's session. Use only when the "
        "user has confirmed they want this buyer's agent to receive "
        "the result of these tool calls (e.g. request_vin, "
        "request_pickup_address)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_token": {"type": "string"},
            "calls": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["session_token", "calls"],
    },
}

DENY_ASK = {
    "name": "deny_ask",
    "description": (
        "Refuse a single MCP tool call with a one-line reason. Use "
        "when the user explicitly declines to grant the call the "
        "policy would otherwise have allowed, or when the call is "
        "not applicable to this item (e.g. request_inspection_report "
        "with no PDF on file)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_token": {"type": "string"},
            "tool": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["session_token", "tool", "reason"],
    },
}

COUNTER_OFFER = {
    "name": "counter_offer",
    "description": (
        "Send a counter-offer in an ongoing negotiation. Enforces "
        "≤ 5 rounds, ≤ 1000 chars per offer, ≤ 50,000 chars per "
        "match. Use only after the user has approved the new price "
        "and conditions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "buyer_pubkey": {"type": "string"},
            "amount_cents": {"type": "integer"},
            "currency": {"type": "string"},
            "conditions": {"type": "string"},
        },
        "required": ["item_id", "buyer_pubkey", "amount_cents", "currency"],
    },
}

ACCEPT_OFFER = {
    "name": "accept_offer",
    "description": (
        "Accept the buyer's most recent offer. ALWAYS requires "
        "explicit user confirmation — the tool refuses if the user "
        "has not approved within the same Hermes session. The "
        "listing is NOT marked sold by this tool; that's a separate "
        "update_item call after the buyer's confirmation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "buyer_pubkey": {"type": "string"},
        },
        "required": ["item_id", "buyer_pubkey"],
    },
}

REJECT_OFFER = {
    "name": "reject_offer",
    "description": (
        "Reject the buyer's most recent offer with a brief reason. "
        "Closes the match unless the user re-opens it with a fresh "
        "counter."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "buyer_pubkey": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["item_id", "buyer_pubkey", "reason"],
    },
}
