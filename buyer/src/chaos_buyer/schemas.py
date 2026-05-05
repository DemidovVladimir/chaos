"""Tool schemas — buyer-side LLM-facing tools."""

from __future__ import annotations

CREATE_FILTER = {
    "name": "create_filter",
    "description": (
        "Create a saved Nostr REQ filter from a high-level UserWant "
        "(make/model/year-range/body-type/etc.). The filter starts "
        "active and is added to the running subscription set. Use "
        "when the user describes what they want to find."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "want": {
                "type": "object",
                "description": "UserWant fields; missing fields mean 'any'.",
            },
        },
        "required": ["name", "want"],
    },
}

LIST_FILTERS = {
    "name": "list_filters",
    "description": "List all saved filters with active/paused state.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

PAUSE_FILTER = {
    "name": "pause_filter",
    "description": (
        "Pause a saved filter. The REQ subscription is dropped on "
        "every relay; the user stops getting matches until "
        "resume_filter is called."
    ),
    "parameters": {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
}

DELETE_FILTER = {
    "name": "delete_filter",
    "description": "Delete a saved filter and stop its subscription.",
    "parameters": {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
}

SEND_INQUIRY = {
    "name": "send_inquiry",
    "description": (
        "Send a NIP-17 sealed gift-wrap inquiry to the seller of a "
        "matched listing. Rumor type is `mcp_inquiry_open`; the "
        "payload carries the user's selected asks (e.g. "
        "service_history, photos:exterior, inspection_at_shop), the "
        "buyer's pubkey, and a fresh `session_token` the seller will "
        "later bind to its grant. The seller's MCP HTTP+SSE URL is "
        'discovered from the matched listing\'s `["mcp", url]` tag — '
        "it is NOT carried in the inquiry. Use after the user "
        "approves the draft asks list."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "asks": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["item_id", "asks"],
    },
}

MCP_CONNECT = {
    "name": "mcp_connect",
    "description": (
        'Open an MCP HTTP+SSE session to the seller\'s `["mcp", url]` '
        "tag from the matched listing and call `tools/list` to "
        "bootstrap the seller's tool surface (cars-pack@1: "
        "view_listing, request_photos, request_inspection_report, "
        "request_vin, submit_offer, cancel_inquiry). Returns the list "
        "of advertised tools. Run once after the seller's NIP-17 "
        "reply confirms granted asks and before any `mcp_call_tool`."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
        },
        "required": ["item_id"],
    },
}

MCP_CALL_TOOL = {
    "name": "mcp_call_tool",
    "description": (
        "Dispatch a single `tools/call` against the open MCP session "
        "for an item. Decodes the returned content blocks: "
        "`ImageContent` and `EmbeddedResource` bytes are written to "
        "the inbox (photos/ and documents/ subfolders); `TextContent` "
        "is sanitized and returned inline. Per AGENTS.md rule 2 the "
        "buyer NEVER fetches binary content from any URL — bytes only "
        "arrive inline as MCP content blocks."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "tool_name": {
                "type": "string",
                "description": (
                    "One of the names returned by `mcp_connect` — "
                    "e.g. `request_photos`, "
                    "`request_inspection_report`, `request_vin`, "
                    "`submit_offer`, `cancel_inquiry`."
                ),
            },
            "arguments": {
                "type": "object",
                "description": (
                    "Tool-specific arguments. The buyer's "
                    "`session_token` from the inquiry MUST be "
                    "included so the seller can bind the call to "
                    "the inquiry's grant policy."
                ),
            },
        },
        "required": ["item_id", "tool_name", "arguments"],
    },
}

LIST_INQUIRIES = {
    "name": "list_inquiries",
    "description": "List the user's open inquiries with status and last activity.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

DRAFT_OFFER = {
    "name": "draft_offer",
    "description": (
        "Suggest a counter-offer based on market_comp median and the "
        "evaluator's soft-flag count. Returns the suggested amount, "
        "currency, and rationale. Does NOT send — the user reviews "
        "and confirms via counter_offer."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "stance": {
                "type": "string",
                "description": "Optional stance: fair | low | high.",
            },
        },
        "required": ["item_id"],
    },
}

ACCEPT_OFFER = {
    "name": "accept_offer",
    "description": (
        "Accept the seller's most recent offer. ALWAYS requires "
        "explicit user confirmation — refuses if the user has not "
        "approved within this same Hermes session."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
        },
        "required": ["item_id"],
    },
}

REJECT_OFFER = {
    "name": "reject_offer",
    "description": (
        "Reject the seller's most recent offer with a brief reason. "
        "Closes the match unless the user re-opens it with a fresh "
        "counter via counter_offer."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["item_id", "reason"],
    },
}

COUNTER_OFFER = {
    "name": "counter_offer",
    "description": (
        "Send a counter-offer to the seller. Enforces ≤ 5 rounds, "
        "≤ 1000 chars per offer, ≤ 50,000 chars per match."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "amount_cents": {"type": "integer"},
            "currency": {"type": "string"},
            "conditions": {"type": "string"},
        },
        "required": ["item_id", "amount_cents", "currency"],
    },
}
