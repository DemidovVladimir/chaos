# chaos-agent

The role-flexible engine that powers a chaos agent. Any agent that
installs `chaos-agent` can:

- **Publish** signed NIP-99 events to one or more Nostr relays
  (`publish.py`)
- **Subscribe** to others' events with REQ filters (`subscribe.py`)
- **Receive** NIP-17 sealed gift-wrap inquiries (`inquiry_listener.py`)
- **Send** NIP-17 inquiries to other agents (`inquiry.py`)
- **Serve** rich content over MCP HTTP+SSE (`mcp_server.py`)
- **Dial** other agents' MCP servers as a client (`mcp_client.py`)

A single agent does any of these in any combination, simultaneously,
against any number of counterparts. Topology is unconstrained: 1:1,
1:N, N:1, N:M concurrent on the same Nostr substrate.

There is **no built-in seller / buyer split**. The agent is symmetric;
which capabilities it exercises in any given session is decided by
the user (or by the pack plugin loaded into Hermes).

## Repo structure

```
agent/
├── pyproject.toml
├── src/chaos_agent/
│   ├── identity.py          # secp256k1 keypair, npub
│   ├── publish.py           # NIP-99 publish + NIP-13 PoW
│   ├── subscribe.py         # REQ filter subscriptions
│   ├── filters.py           # filter generation helpers
│   ├── inquiry.py           # send NIP-17 sealed gift-wraps
│   ├── inquiry_listener.py  # receive NIP-17 sealed gift-wraps
│   ├── mcp_server.py        # FastMCP HTTP+SSE server
│   ├── mcp_client.py        # FastMCP HTTP+SSE client
│   ├── inbox.py             # local store of received DMs / matches
│   ├── catalog.py           # pack-side: load offerings from disk
│   ├── evaluator.py         # rubric / red-flag scoring
│   ├── grant_policy.py      # per-tool grant decisions
│   ├── negotiation.py       # offer / counter-offer state machine
│   ├── attestation.py       # peer-attestation send / verify
│   ├── input_safety.py      # untrusted-text sanitiser
│   ├── schemas.py           # data types
│   ├── config.py            # AgentConfig dataclasses
│   ├── main.py              # CLI: `chaos-agent <subcommand>`
│   └── tools_*.py           # Hermes tool wrappers (publish / subscribe / inquire / negotiate)
└── tests/
```

## Hermes integration

`chaos-agent` registers as a Hermes plugin (`chaos_agent:register`).
Pack plugins (e.g. `plugins/cars/`) load `chaos-agent` and bind the
pack's tag schema, MCP tool surface, skills, and grant policy on top.
A user that wants their agent to participate in a domain just installs
that pack's plugin; the agent then both publishes for that domain
AND subscribes for it, automatically.
