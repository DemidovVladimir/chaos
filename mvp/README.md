# MVP — run it

The whole weekend MVP in two scripts plus a config plus an MCP
server module. No infrastructure required.

The MVP exercises the full discovery + peer-transport loop:

1. **Discovery** — offering agent publishes a NIP-99 event on free public
   relays carrying `["mcp", "<url>"]` and `["pack", "cars-pack@1"]`
   tags. Seeking agent subscribes with cars-pack tag filters.
2. **Encrypted handshake** — seeking agent sees match, sends NIP-04 DM
   inquiry; offering agent replies in same encrypted channel. (Production
   uses NIP-17 sealed gift-wrap; NIP-04 is the MVP shortcut.)
3. **Peer transport** — seeking agent connects to the offering agent's FastMCP
   HTTP+SSE server on the URL from the listing, runs `tools/list`,
   calls `view_listing`, `request_photos`, `request_inspection_report`
   on the cars-pack@1 tool surface. Photos arrive as `ImageContent`
   blocks, inspection report as `EmbeddedResource`. SHA-256 verified
   on receipt; saved into `mvp/received/`.

No third-party file host. No HTTP file servers. Everything moves
either over relay-encrypted DMs or directly between agent processes
over MCP.

## Setup (5 min)

```bash
cd mvp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Generate keypairs (one per role):

```bash
python agent_offering.py keygen   # writes ~/.mvp/agent.key
python agent_seeking.py keygen    # writes ~/.mvp/agent.key
```

Each script prints the corresponding `npub` so the other side knows
who to DM.

## Single-machine demo (recommended)

Two terminals on the same machine. Offering agent's FastMCP server binds to
`127.0.0.1:8765` so the seeking agent reaches it locally.

```bash
# Terminal 1 (offering agent)
python agent_offering.py serve sample_car.toml
```

You should see, in order:

```
[+] FastMCP server up on http://127.0.0.1:8765/sse
Published listing 8f4a2b1e (event id 9d3a...) to 5 relay(s).
Listening for inquiries; Ctrl-C to stop.
```

```bash
# Terminal 2 (seeking agent)
python agent_seeking.py watch
```

Within seconds:

```
Match: 2018 Mazda 6 hatchback
  price:    15000 EUR
  location: EU/CZ/Prague
  offering:   ...
  pack:     cars-pack@1
  mcp:      http://127.0.0.1:8765/sse

Send the offering agent a DM? Type a message (blank to skip):
> tell me more about service history
[+] Sent. Listening for reply...
```

Switch back to Terminal 1 — type a reply at the offering agent's prompt.
Switch to Terminal 2 — see the offering agent's reply, then a follow-up
prompt:

```
Reply from npub17c4f...:
> Full Mazda dealer service history. Ask MCP for photos.

This offering agent's listing advertised an MCP endpoint:
  http://127.0.0.1:8765/sse  (item 8f4a2b1e…)
Fetch cover photo + inspection report via MCP now? [y/N] y
```

After answering `y`:

```
=== MCP fetch complete ===
  tools advertised: ['view_listing', 'request_photos',
                     'request_inspection_report', 'request_vin',
                     'submit_offer', 'cancel_inquiry']
  summary:    2018 Mazda 6 hatchback
              65k mi, 1 owner, full Mazda service history. ...
  cover:      69 bytes → /Users/.../mvp/received/8f4a2b1e_cover.png
              sha256 a1b2c3d4e5f6...
  inspection: 1024 bytes → /Users/.../mvp/received/8f4a2b1e_inspection.txt
              sha256 9876543210ab...
```

The cover PNG and inspection report are now on the seeking agent's disk,
delivered agent-to-agent over MCP, never via HTTP file host.

## Multi-listing offering agent

Drop multiple `.toml` listings into `mvp/listings/` (use
`sample_car.toml` as a template — see `mvp/listings/README.md`),
then:

```bash
python agent_offering.py serve-multi listings/
```

Each listing is published as its own NIP-99 event. The same MCP
server on `127.0.0.1:8765` serves all of them — resolution by
`item_id` happens at call time inside `mcp_server.py`'s in-memory
catalog.

Per-item assets are auto-detected:

- `mvp/sample_photos/<item_id>/*.png` — listing-specific photos
  (all PNGs in the directory are returned)
- `mvp/sample_inspection_<item_id>.{pdf,txt,md}` — listing-specific
  inspection report (MIME auto-detected: `.pdf` →
  `application/pdf`, `.txt` → `text/plain`, `.md` →
  `text/markdown`, anything else → `application/octet-stream`)

Items missing per-item assets fall back to the global
`sample_photos/cover.png` + `sample_inspection.txt` fixtures, so a
half-populated catalog still demos cleanly.

The single-listing `serve sample_car.toml` path is unchanged.

## Optional: point at your own Mode-A relay

If the public default relays are 503-ing, or you want to demo on a flight,
boot your own strfry locally. See `operator/cars/README.md` § "Quick
start: 5-min local relay" for full setup. One-shot:

```bash
# Terminal 0 — start your own strfry on :7777
cd ../operator/cars
docker compose -f strfry-compose.yml -f strfry-compose.local.yml up -d
python3 verify_relay.py    # confirms ws://localhost:7777 is alive

# Terminal 1 — offering agent, pointing at the local relay
cd ../../mvp
export MVP_RELAYS="ws://localhost:7777"
python3 agent_offering.py serve sample_car.toml

# Terminal 2 — seeking agent, same relay
cd mvp
export MVP_RELAYS="ws://localhost:7777"
python3 agent_seeking.py watch
```

`MVP_RELAYS` accepts a comma-separated list, so you can mix your local
relay with the public defaults while testing federation behaviour.

## Two-machine demo

Same flow, but the offering agent's FastMCP server needs to be reachable from
the seeking agent's machine. Easiest: put an https tunnel in front (ngrok,
cloudflared) and update `sample_car.toml`:

```toml
mcp_url = "https://abc123.ngrok.app/sse"
```

**Important security boundary**: `mcp_client.py` rejects http:// URLs
with non-localhost hosts to avoid the seeking agent being tricked into
connecting to a malicious public host via a crafted listing tag
during the demo. Cross-machine demos must use https.

## Files

- `agent_offering.py` — publish + listen + reply + boots MCP server in background;
  `serve` (one listing) and `serve-multi` (a directory of listings)
- `agent_seeking.py` — subscribe + match + DM + receive reply + optional MCP fetch
- `shared.py` — keypair load/save, NIP-99 event builder, mcp/pack tag helpers,
  default relay list (override via `MVP_RELAYS` env var)
- `mcp_server.py` — FastMCP HTTP+SSE server exposing cars-pack@1 tool surface;
  builds a per-`item_id` catalog from `MVP_LISTINGS_DIR` when set,
  otherwise serves the single global fixture
- `mcp_client.py` — async helper that drives `tools/list` + `call_tool`
- `sample_car.toml` — fake car listing in TOML; edit to change facets,
  also serves as a template for files in `listings/`
- `listings/` — drop multiple `.toml`s here for `serve-multi`
- `sample_inspection.txt` — fixture inspection report (global fallback)
- `sample_photos/` — fixture cover image + per-item photo subdirs
- `received/` — seeking agent's downloaded photos + reports (created on first MCP fetch)
- `requirements.txt` — `pynostr`, `tomli`, `mcp`

## Common failures and fixes

- **`SSL: CERTIFICATE_VERIFY_FAILED`** — already handled in
  `agent_offering.py` and `agent_seeking.py` via `certifi`. If you see this on a new
  machine, run `pip install --upgrade certifi` in the venv.
- **`websockets.exceptions.ConnectionClosed`** — relay disconnected.
  Re-run; both scripts auto-reconnect once.
- **No matches in `agent_seeking.py`** — check that the filter in `agent_seeking.py`
  matches the offering agent's tags. Default filter is `t=cars, make=mazda`;
  if you changed `sample_car.toml`, change the filter too.
- **DM not arriving** — both scripts need to share at least one
  relay. Default is the 5-relay list in `shared.py` (damus, nos.lol,
  snort.social, wellorder.net, nostr.band). If you set
  `MVP_RELAYS` on one side, make sure the other side has at least
  one relay in common.
- **`refusing http:// MCP URL with non-local host`** — the seeking agent
  refused a non-https public URL. Either run single-machine
  (localhost is allowed) or front the offering agent's MCP with an https
  tunnel.
- **`Connection refused` on MCP fetch** — offering agent's MCP server isn't
  bound. Check the offering agent terminal printed `FastMCP server up on
  http://127.0.0.1:8765/sse` before publishing. If it crashed,
  rerun `agent_offering.py serve` (or `python mcp_server.py` standalone to
  diagnose).
- **`OSError: [Errno 48] address already in use`** — port 8765 is
  taken (likely a previous `serve` is still running). Kill it or
  set `MVP_MCP_PORT=9876` (and update `sample_car.toml.mcp_url`
  to match).
- **`ImportError: Using SOCKS proxy, but the 'socksio' package is
  not installed`** — your shell has `HTTP_PROXY` / `HTTPS_PROXY` /
  `ALL_PROXY` set to a `socks5://...` URL. Either `unset` those for
  the seeking agent terminal (the MVP's localhost-only flow doesn't need a
  proxy) or `pip install 'httpx[socks]'` into the venv. Doesn't
  affect single-machine demos unless your shell exports a SOCKS
  proxy by default.

## What this MVP intentionally does NOT do

These all live in `offering agent/`, `seeking agent/`, `plugins/cars`,
`plugins/cars`, etc. — the production wiring:

- **Per-tool grant policy**. The MVP MCP server auto-grants
  view_listing, request_photos, request_inspection_report, and stubs
  request_vin to a hard-coded "denied" string. Production wires
  `mcp_grant_decision(...)` to prompt the offering agent's user.
- **NIP-17 sealed DMs**. The MVP uses NIP-04 for inquiry channel.
  Production switches to NIP-17 gift-wrap with NIP-44 encryption.
- **Session_token binding**. The MVP MCP server trusts whoever
  reaches localhost. Production binds a session_token established
  via NIP-17 to the calling seeking agent's pubkey.
- **PoW on listing publish**. The MVP skips NIP-13. Production
  mines ≥ 20 bits before publishing.
- **input_safety on returned tool content**. The MVP logs server
  text verbatim (capped at 500 chars by `_truncate_for_print`).
  Production wraps every TextContent / ImageContent.mimeType /
  EmbeddedResource.uri text field in `<untrusted>` and runs through
  `input_safety` before surfacing to the LLM planner.
- **reverse_image_check, vin_decode, market_comp, reputation_mcp**.
  The MVP doesn't load any capability MCPs. Production seeking agent
  plugins ship them per `plugins/cars/plugin.yaml`.
- **Negotiation state machine**. `submit_offer` returns a stub
  refusal. Production wires the round-counted negotiation flow from
  `offering agent/src/chaos_agent/negotiation.py`.

## Next steps once it works

Use the `offering agent/` and `seeking agent/` component scaffolds for the production
wiring path after the demo works.
