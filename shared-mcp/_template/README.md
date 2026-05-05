# `<mcp-name>-mcp` — one-line summary

Replace this with: what this MCP does, in one sentence.

## Tier model

- **Free tier** — what's included for everyone, run locally.
- **Paid tier** (if any) — per-call x402 price, what extra it
  unlocks.

This MCP follows `AGENTS.md` rule 6: no commercial data brokers, no
third-party file hosts, no PII reseller. All computation is local
or against free authoritative sources.

## Threat model

- Inputs are bytes / strings the user already has locally.
- The MCP MUST NOT make outbound HTTP except to a small allowlist
  documented here (e.g. ECB FX rates, public WMI registry).
- The MCP MUST NOT retain user inputs beyond the request lifetime.

## Tool surface

```
- <tool_name>(args) -> <return_type>
```

(Replace with actual tool list. Use MCP content types —
`TextContent`, `ImageContent`, `EmbeddedResource` — where
appropriate.)

## Pricing

Free / per-call x402 / both (with config flag).

## Implementation notes

Stub today; real implementation lands in a follow-up.
