<!-- (Historical -- written under the project's previous name "neuro-spati", now called "chaos".) -->

# spike — MCP peer-transport proof

MCP is the peer wire for chaos. This directory keeps the small
FastMCP proof that established the required properties:

- dynamic tool discovery with `tools/list`
- inline binary content with `ImageContent`
- arbitrary binary resources with `EmbeddedResource`
- one seeking agent querying multiple offering agents concurrently

## Run

```bash
cd spike
python3 buyer_mcp.py
```

The seeking agent spawns two local offering agent MCP servers, calls their tool
surfaces in parallel, verifies image/report bytes by SHA-256, and
writes outputs to `received_mcp/`.

## Files

- `seller_mcp.py` — FastMCP offering agent server exposing the cars-pack-like
  tool surface used by the spike.
- `buyer_mcp.py` — seeking agent fanout client; starts two offering agents and verifies
  returned content blocks.
- `received_mcp/` — last successful run outputs.
- `MCP_SPIKE_REPORT.md` — short technical record of the MCP result.
