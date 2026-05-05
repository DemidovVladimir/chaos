# MVP smoke test — proves Nostr discovery + MCP rich-content round-trip

Goal: produce visible end-to-end evidence that the chaos protocol
works on the public Nostr commons. By the end, you should have:

- A NIP-99 listing event id signed by your publisher pubkey, accepted
  by ≥ 1 public relay
- A seeking-side `[match]` line for that exact event id
- A NIP-04 inquiry round-trip (encrypted DM both ways)
- An MCP `tools/list` response with the cars-pack@1 surface
- Photos downloaded as `ImageContent` blocks + an inspection PDF
  as `EmbeddedResource`, all SHA-256-verified, written to
  `mvp/received/<offering_npub>/`

That output is the smoke-test evidence. Screenshot or paste it; it's
what backs the deck's "MVP runs end-to-end" claim.

## Prereqs

- Working `uv sync` from the repo root (the workspace venv has the
  deps the mvp/ scripts need).
- Two terminals open, both `cd`'d to the repo root.
- Network access to public Nostr relays (`relay.damus.io`,
  `nos.lol`, etc.).

## Step 0 — keygen (one-shot, either terminal)

```bash
cd mvp
uv run python agent_offering.py keygen
uv run python agent_seeking.py keygen
```

Expected output (each command):

```
✓ wrote ~/.chaos/keys/agent.key (mode 0600)
  npub: npub1...
```

Capture both `npub1...` strings. You'll need them later to verify
the loop closed correctly.

## Step 1 — terminal A — offering agent publishes + serves

```bash
# terminal A
cd mvp
uv run python agent_offering.py serve sample_car.toml
```

Expected output (in order — it'll take ~5–10 s):

1. `→ event 30402 id <hex64> published to:` followed by relay status
   lines (`✓` or `✗`).
2. `FastMCP HTTP+SSE listening on :8765`
3. `watching for NIP-04 inquiries on <relay set>...`

If you see a NIP-13 PoW progress line (`computing PoW (target 20
bits)... <ms>`), that's the spam-gate working. If ≥ 1 relay shows
`✓` and the FastMCP banner appears, **Phase A is done.** Leave this
terminal running.

## Step 2 — terminal B — seeking agent subscribes + watches

```bash
# terminal B
cd mvp
uv run python agent_seeking.py watch
```

Expected output within ~5–15 s (the relays push the matching event
once they index it):

```
[subscribe] wss://relay.damus.io  ✓
[subscribe] wss://nos.lol         ✓
...
[match  ] kind=30402 id=<hex64>  "2018 Mazda 6 hatchback"  €15000
          mcp=http://127.0.0.1:8765/sse  pack=cars-pack@1
DM offering agent? [y/N]
```

The `id=<hex64>` here MUST equal the one terminal A printed at Step
1. **If it matches, Phase B is done — Nostr discovery works.**

## Step 3 — terminal B — type `y` and an inquiry

Type `y`, then a short inquiry:

```
DM offering agent? [y/N] y
Inquiry text: hi, is the 2018 Mazda 6 still available?
[dm sent ] kind=4 to npub1<offering>... (NIP-04 ciphertext)
```

## Step 4 — terminal A — offering agent sees the DM, replies

Terminal A should now print:

```
[inquiry] from npub1<seeking>... session=<token>
          decrypted: "hi, is the 2018 Mazda 6 still available?"
Reply (blank to skip):
```

Type a reply:

```
Reply (blank to skip): yes, available, viewing welcome
[dm sent ] kind=4 to npub1<seeking>...
```

**Phase C is done — encrypted DM round-trip works.**

## Step 5 — terminal B — seeking agent fetches via MCP

Terminal B receives the offering agent's reply and prompts:

```
[reply  ] from npub1<offering>...: "yes, available, viewing welcome"
Fetch photos + inspection now via MCP? [y/N]
```

Type `y`. Expected:

```
[mcp    ] connecting http://127.0.0.1:8765/sse
[mcp    ] tools/list  →  6 tools (cars-pack@1)
            view_listing, request_photos, request_inspection_report,
            request_vin, submit_offer, cancel_inquiry
[mcp    ] view_listing                  → text/plain (<n> bytes)
[mcp    ] request_photos                → ImageContent[<n>]
[verify ] sha256 ✓ on every block
[mcp    ] request_inspection_report     → EmbeddedResource (<n> bytes)
[verify ] sha256 ✓
[cache  ] saved ~/.../mvp/received/<offering_npub>/<item_id>/
```

**Phase D is done — MCP rich-content delivery works.** The bytes
flowed from the offering agent's MCP server (running in terminal A's
process) directly to the seeking agent (terminal B), with no third-party
host in the path.

## Step 6 — verify the cache

```bash
ls -la mvp/received/*/*/photos/
ls -la mvp/received/*/*/inspection.pdf  # or .txt for the sample
```

You should see the photos from `mvp/sample_photos/` and the
inspection text/PDF from `mvp/sample_inspection.txt`. SHA-256
verified.

## Cleanup

- `Ctrl-C` in terminal A and terminal B.
- The keys at `~/.chaos/keys/agent.key` are real and
  reusable. Delete if you want a fresh test.

## Smoke-test evidence card (paste this back to share)

After running, you should be able to fill this in:

```
date:                   <ISO-8601 timestamp>
offering npub:            npub1...
seeking npub:            npub1...
listing event id:       <64 hex>
relays accepted:        <n of N> (e.g. "3/5: damus, nos.lol, snort")
match arrived (s):      <wallclock from publish to [match])
DM round-trip ms:       <approx>
MCP tools/list:         6 tools — view_listing, request_photos,
                        request_inspection_report, request_vin,
                        submit_offer, cancel_inquiry
photos downloaded:      <n> ImageContent blocks, total <kB>
inspection PDF:         <n> bytes EmbeddedResource
SHA-256 verify:         all blocks ✓
third-party host:       NONE — bytes flowed offering→seeking over MCP
```

That card is what backs every "MVP runs end-to-end" claim in the
deck and the README.

## Troubleshooting

- **Seeking agent's `[match]` never arrives.** Public relays sometimes
  return HTTP 503 under load, which `pynostr` retries through. Wait
  60 s. If still nothing, check `agent_offering.py serve`'s output — at
  least one relay must show `✓` for the publish.
- **MCP fetch hangs.** The `mcp_url` in `sample_car.toml`
  (`http://127.0.0.1:8765/sse`) only works on the same machine. If
  you're running terminals on two different machines, expose
  port 8765 via `cloudflared tunnel` or `ngrok` and update
  `mcp_url` in the TOML before publishing.
- **`SSL: CERTIFICATE_VERIFY_FAILED`.** macOS Python from
  python.org doesn't wire CA certs into the stdlib `ssl` module.
  `agent_seeking.py` already pre-points at `certifi` for this reason. If
  it still fails, run
  `/Applications/Python\ 3.13/Install\ Certificates.command`.
- **Stale `__pycache__`.** If imports go weird after editing the
  scripts: `find . -type d -name __pycache__ -exec rm -rf {} +`
  and re-run.
