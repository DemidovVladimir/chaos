# MCP spike report

MCP is the canonical chaos peer transport.

The spike proved the three properties the protocol needs after Nostr
discovery has matched two agents:

1. **Dynamic capability discovery**: the seeking agent connects to a offering agent's
   MCP endpoint and calls `tools/list` before deciding what to call.
2. **Binary content over the peer channel**: offering agent tools return
   `ImageContent` for images and `EmbeddedResource` for non-image
   payloads.
3. **Fanout**: one seeking agent can maintain independent MCP sessions to
   multiple offering agents concurrently with ordinary async client code.

## How to Reproduce

```bash
cd spike
python3 buyer_mcp.py
```

`buyer_mcp.py` starts two `seller_mcp.py` instances on local ports,
queries both in parallel, verifies content hashes, and writes received
artifacts under `spike/received_mcp/`.

## Production Implication

Nostr handles discovery and encrypted session bootstrap. MCP carries
the rich conversation after that:

- `tools/list` for per-session capability discovery.
- `tools/call` for pack-defined operations.
- `ImageContent` and `EmbeddedResource` for all binary payloads.
- `resources/read` on the same MCP server for large `local://...`
  resources.

No public file URLs, no operated file server, no second peer transport.
