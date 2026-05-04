<!-- (Historical -- written under the project's previous name "neuro-spati", now called "chaos".) -->

> **SUPERSEDED.** This document covers the historical A2A
> spike. The project chose MCP after the MCP spike passed cleanly.
> See [`MCP_SPIKE_REPORT.md`](MCP_SPIKE_REPORT.md) for the verdict.
> Kept here only for traceability; do not use as a basis for the
> production seller/ or buyer/ components.

# A2A spike report — verdict and Hermes integration story

**Date**: 2026-05-02
**SDK**: `a2a-sdk==1.0.2`
**Result**: PASS

The spike answered three open architectural questions in one go:
cross-network HTTP transport, binary content streaming, and what
Hermes integration looks like. Verdict: **switch from ACP to A2A
for the seller↔buyer channel.** Reasoning + integration plan below.

## What was tested

Two separate Python processes, fully sandboxed:

- **`seller_a2a.py`** — Starlette app on `127.0.0.1:7421`, A2A
  AgentExecutor that responds to any prompt with a Task →
  TaskArtifactUpdateEvent (carrying a `Part(text=…)`, a
  `Part(raw=PNG_bytes, media_type="image/png")`, and a
  `Part(raw=report_bytes, media_type="text/plain")`) → completed
  status update.
- **`buyer_a2a.py`** — spawns the seller as a subprocess, fetches
  the agent card from `/.well-known/agent-card.json` via
  `A2ACardResolver`, builds a `Client` via `ClientFactory`, sends
  a `SendMessageRequest`, iterates the streamed `StreamResponse`s,
  extracts `Part.raw` bytes, SHA-256-compares to known-expected.

The full HTTP request/response cycle with content blocks was
verified, not just the in-process API.

## Result

```
[buyer] → send_message
[seller] execute task=d62253fb-9a64-4437-8a43-7b132b6a853f
[seller] emit artifact image_sha=c19c64e14541… report_sha=c75542c6c985…
[buyer] HTTP Request: POST http://127.0.0.1:7421/ "HTTP/1.1 200 OK"
[buyer] ← event payload=task
[buyer] ← event payload=artifact_update
[buyer]   raw  name=exterior_front.png mime=image/png bytes=69 sha=c19c64e14541…
[buyer]   raw  name=inspection-report.txt mime=text/plain bytes=238 sha=c75542c6c985…
[buyer] ← event payload=status_update
[buyer] final task state = TASK_STATE_COMPLETED
[buyer] PASS image sha256 matches (69 bytes)
[buyer] PASS report sha256 matches (238 bytes)
=== A2A SPIKE PASS ===
```

Bytes-out-of-buyer == bytes-in-seller. HTTP transport. No third
party. JSON-RPC envelope. Streaming response. All native.

## How A2A compares to the ACP spike (same hardware, same network)

| Property | ACP spike | A2A spike |
|---|---|---|
| Transport | stdio (subprocess pipes) | **HTTP + JSON-RPC** |
| Cross-network | impossible without our own bridge | **works as-is** |
| Binary content shape | `image_block(data=base64_str, mime_type=…)` | `Part(raw=bytes, media_type=…)` — raw bytes, no manual base64 |
| Discovery | none | **agent card at `/.well-known/agent-card.json`** |
| Auth | none | OAuth/OIDC/API-key spec built in (we didn't exercise it) |
| Hermes ships an adapter | yes (`acp_adapter/`) | no — we write our own |
| Lines of code in the spike | ~100 (seller) + ~140 (buyer) | ~155 (seller) + ~180 (buyer) |
| API gotchas to document | 1 (image_block vs resource_block wrapping) | 8 (see below) |
| Spec stability | newer | 1.0 stable, Linux Foundation |

ACP still works for what it was designed for (IDE → agent over stdio).
A2A is what was designed for cross-org, cross-network agent-to-agent.
Our marketplace **is** cross-org, cross-network agent-to-agent.

## API gotchas we hit (document for the implementation team)

The SDK is at 1.0.2 and there are real footguns. Each one cost
minutes of debugging in the spike; document them so the team doesn't
re-discover them.

### 1. protobuf version conflict

`a2a-sdk==1.0.2` requires `protobuf>=5.29.5`. The latest
protobuf 7.x has dropped `FieldDescriptor.label`, which the SDK's
`validate_proto_required_fields` still uses. Pin protobuf:

```
protobuf>=5.29.5,<6
```

Symptom if wrong: `AttributeError: 'FieldDescriptor' object has no
attribute 'label'` server-side, after which the buyer sees an
opaque `InternalError`.

### 2. `AgentInterface` field name

The proto field is `protocol_binding`, not `transport`:

```python
AgentInterface(protocol_binding="JSONRPC", url=...)  # ✅
AgentInterface(transport="JSONRPC", url=...)         # ❌ ValueError at construction
```

### 3. `DefaultRequestHandler` requires `agent_card`

```python
DefaultRequestHandler(
    agent_card=card,             # required positional kwarg
    agent_executor=executor,
    task_store=InMemoryTaskStore(),
)
```

### 4. The agent-card JSON includes v0.3 compat fields the proto rejects

The server emits `preferredTransport` and `url` as legacy fields
on the agent card. The protobuf `AgentCard` parser doesn't have those
fields and `json_format.Parse(...)` raises `ParseError`. Use the
SDK's resolver, which strips them:

```python
from a2a.client.card_resolver import A2ACardResolver
resolver = A2ACardResolver(http_client, base_url)
card = await resolver.get_agent_card()  # ✅ tolerates compat fields
```

### 5. `Client.send_message` takes `SendMessageRequest`, not `Message`

```python
req = SendMessageRequest(message=msg)
async for stream_resp in client.send_message(req):  # ✅
    ...

async for x in client.send_message(msg):            # ❌ AttributeError: configuration
    ...
```

### 6. `TaskStatusUpdateEvent` has no `final` field in 1.0.2

Older example code uses `final=True`. In this SDK version, fields
are `task_id`, `context_id`, `status`, `metadata` — that's it.

### 7. `Task` event MUST be emitted before any status / artifact update

Strictly enforced by the SDK with
`InvalidAgentResponseError: Agent should enqueue Task before
TaskStatusUpdateEvent event`. The execute() method must:

```python
await event_queue.enqueue_event(Task(id=..., context_id=..., status=...))   # FIRST
await event_queue.enqueue_event(TaskArtifactUpdateEvent(...))               # then content
await event_queue.enqueue_event(TaskStatusUpdateEvent(...))                 # then completion
```

### 8. `new_artifact_id` is not in `a2a.utils`

Use `str(uuid.uuid4())` directly. The SDK's `__init__.py` for
`a2a.utils` only exports a small set of constants/helpers; the
artifact-id helper isn't there.

### 9. `socksio` is a transitive optional dep that's not installed by default

`a2a-sdk` uses httpx with SOCKS-aware transport. If httpx is told
about a SOCKS proxy (or the env says so), it imports `socksio` —
which the SDK doesn't pull in. `pip install httpx[socks]` once.

### 10. `a2a-sdk[http-server,sql]` extras are needed for the server side

The base `a2a-sdk` package brings only the proto + client. The
server (Starlette routes, SSE dispatcher) needs `[http-server]` plus
optionally `[sql]` for persistent task store. Install:

```
pip install 'a2a-sdk[http-server,sql]' starlette uvicorn
```

## What actually changes for our architecture

The neuro-spati v5 design (Nostr for discovery, peer protocol for
content) **does not change**. Only the "peer protocol" identity
swaps: ACP → A2A.

| Layer | Before (ACP) | After (A2A) |
|---|---|---|
| Discovery | Nostr NIP-99 listing carries `["acp", "https://a.io/acp"]` | Nostr NIP-99 listing carries `["a2a", "https://a.io/.well-known/agent-card.json"]` |
| Inquiry channel | NIP-17 sealed DM with `acp_session_offer` payload | NIP-17 sealed DM with `a2a_card_url` payload |
| Photo delivery | ACP `ImageContentBlock` over stdio (impossible cross-network without bridge) | A2A `Part(raw=bytes)` over HTTP+JSON-RPC, native cross-network |
| Negotiation | ACP messages | A2A `SendMessageRequest`s with text Parts |
| Auth | application-layer (HMAC, NIP-17 encryption) | A2A's spec'd OAuth/OIDC + still NIP-17 for sensitive content |

`PROTOCOL.md`, the cars-pack skills, and the seller/buyer scaffolds
all need a search-and-replace pass: every "ACP" → "A2A", every
`acp_url` tag → `a2a_card_url`, every `acp.image_block(...)` →
`Part(raw=..., media_type=...)`. The conceptual flow is identical.

## Hermes integration story (the question you flagged as priority #1)

Hermes ships `acp_adapter/` but no A2A adapter. We write our own.
The pattern is short and clean:

```
hermes-plugin/
└── seller_a2a/
    ├── __init__.py            # register(ctx) — Hermes plugin entry
    ├── adapter.py             # MarketplaceSellerAgentExecutor(AgentExecutor)
    ├── server.py              # build_app() — Starlette + uvicorn launch
    ├── grant_policy.py        # per-ask grant policy (cars-pack)
    ├── attestation.py         # Schnorr sign / verify NIP-58 attestations
    └── tools_a2a.py           # Hermes skill tools that wrap A2A operations
```

The `MarketplaceSellerAgentExecutor.execute(context, event_queue)`
method is the boundary:

```python
class MarketplaceSellerAgentExecutor(AgentExecutor):
    def __init__(self, hermes_runtime, item_catalog, grant_policy):
        self.hermes = hermes_runtime
        self.catalog = item_catalog
        self.policy = grant_policy

    async def execute(self, context, event_queue):
        # 1. Translate A2A request to Hermes prompt
        prompt = _build_seller_prompt(context.message, self.catalog)

        # 2. Run Hermes agent loop (the LLM reasoning happens here)
        result = await self.hermes.run_turn(
            prompt=prompt,
            skill="marketplace-seller",
            tools=["nostr_publish", "reverse_image_check"],
            grant_policy=self.policy,
        )

        # 3. Translate Hermes response → A2A events
        await event_queue.enqueue_event(Task(...))
        for asset in result.granted_assets:
            await event_queue.enqueue_event(TaskArtifactUpdateEvent(
                artifact=Artifact(parts=[
                    Part(raw=asset.bytes, media_type=asset.mime, filename=asset.name)
                    for asset in result.granted_assets
                ])
            ))
        await event_queue.enqueue_event(TaskStatusUpdateEvent(
            status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED)
        ))
```

That's about 30 lines of real glue. The buyer side is the symmetric
mirror — Hermes calls `A2A Client.send_message(...)` as if it were
a tool, captures the streamed events, hands the binary back to the
buyer agent's reasoning loop.

**Crucially**, Hermes' agent loop is *inside* `execute()`. We don't
fight Hermes' lifecycle — we plug A2A into one well-defined boundary.

The plugin registers itself at startup:

```python
def register(ctx):
    catalog = LocalItemCatalog(Path.home() / ".neuro_spati/items")
    policy = GrantPolicy.load(Path.home() / ".neuro_spati/grant_policy.yaml")
    executor = MarketplaceSellerAgentExecutor(ctx.hermes_runtime, catalog, policy)
    ctx.register_skill("marketplace-seller", "...path/to/SKILL.md")
    ctx.register_background_task("a2a-server", lambda: run_a2a_server(executor))
```

The A2A server runs as a background task in the Hermes process. Same
pattern Hermes uses for the gateway adapter — long-running asyncio
loop alongside the main agent loop.

**Effort estimate**: 3–5 days for one engineer to wire end-to-end,
including the Nostr-side tag updates and the cars-pack skill rewrites.
Faster than the corresponding ACP scaffold because A2A's HTTP layer
removes the "build our own bridge" branch.

## Recommendation

**Switch from ACP to A2A.** Specifically:

1. Update `PROTOCOL.md` to specify A2A as the peer-to-peer transport.
   Replace `acp` tag → `a2a_card_url` tag in cars-pack listings.
   Photos move via `Part(raw=bytes)` instead of ACP `ImageContentBlock`.
2. Update `seller/IMPLEMENTATION_PLAN.md` and
   `buyer/IMPLEMENTATION_PLAN.md` to point at A2A. Most of the plan
   structure carries over; only the transport layer changes.
3. Pin `protobuf>=5.29.5,<6` and `a2a-sdk==1.0.2` (or whatever the
   current stable is when implementation starts) in
   `seller/pyproject.toml` and `buyer/pyproject.toml`.
4. Carry the 10 gotchas in this report into a checklist that the
   implementation team works against.
5. Optionally: update [`spike/seller_acp.py`](seller_acp.py) and
   [`spike/buyer_acp.py`](buyer_acp.py) headers to mark them as
   "superseded by A2A spike — kept for archival reference only."

The ACP work isn't wasted — it answered "can binary content stream
between two agents at all" in 30 minutes, which informed the A2A
spike's structure. We discovered that ACP couldn't deliver the
cross-network half of the architecture, and pivoted before
committing to it.

## Open questions still left

- **Large-payload performance.** Tested 69 bytes + 238 bytes. A2A's
  `Part` accepts raw bytes inline up to whatever JSON-RPC + base64
  re-encoding tolerates; for >1 MB photos the spec says "use a URL
  reference instead." We haven't tested the boundary. Follow-up
  spike: emit a 5 MB and a 15 MB Part, see what happens. ~1 day.
- **`Part(url=...)` semantics with our "no third-party host" rule.**
  A2A's URL-reference fallback is fine *if* the URL points back at
  the seller's own A2A endpoint (`/files/<token>` route on the same
  Starlette app). Codify this in CLAUDE.md before any large-payload
  code lands: "if `Part(url=...)` is used, the URL MUST be on the
  same agent's A2A endpoint."
- **A2A's auth story for our case.** Spec supports OAuth/OIDC/API key.
  For our marketplace the simpler answer is: rely on NIP-17 for
  privacy of the inquiry channel; A2A endpoint accepts anyone but
  rate-limits per-IP. Sensitive grants go through user-confirm
  (Hermes approval gate) regardless of who's connecting.

None of these block the implementation. They're follow-up items.

## Files this spike produced

- `spike/seller_a2a.py` — A2A AgentExecutor + Starlette server
- `spike/buyer_a2a.py` — A2A Client + verifier
- `spike/A2A_SPIKE_REPORT.md` — this file
- `spike/received_a2a/received_image.png` — the round-tripped 1×1 red pixel
- `spike/received_a2a/received_report.txt` — the round-tripped inspection report

The earlier ACP spike files (`seller_acp.py`, `buyer_acp.py`,
`README.md`) remain in the same folder as historical record.
