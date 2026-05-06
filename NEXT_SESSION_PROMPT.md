# Next session — run the chaos smoke test against public relays

Paste this whole block as your first message in a new Claude session.

---

I want to run the chaos MVP smoke test end-to-end against public Nostr
relays and produce the evidence card that backs the Hermes pitch claims.
The full runbook is at `mvp/SMOKE_TEST.md` in this repo
(`~/development/chaos`) — that file is the contract; follow it verbatim.

## Goal

Fill in the evidence card at the bottom of `mvp/SMOKE_TEST.md`:

```
date:                  <ISO-8601 timestamp>
offering npub:         npub1...
seeking npub:          npub1...
listing event id:      <64 hex>
relays accepted:       <n of N>
match arrived (s):     <wallclock from publish to [match]>
DM round-trip ms:      <approx>
MCP tools/list:        6 tools — view_listing, request_photos,
                       request_inspection_report, request_vin,
                       submit_offer, cancel_inquiry
photos downloaded:     <n> ImageContent blocks, total <kB>
inspection PDF:        <n> bytes EmbeddedResource
SHA-256 verify:        all blocks ✓
third-party host:      NONE — bytes flowed offering→seeking over MCP
```

## Recent context you should know before reading SMOKE_TEST.md

A big refactor just landed (`git log --oneline -1` should show
"refactor: collapse seller/buyer split into symmetric agent + tier-isolated plugins").
Important file-path facts:

- The MVP scripts are `mvp/agent_offering.py` (was `mvp/seller.py`) and
  `mvp/agent_seeking.py` (was `mvp/buyer.py`). SMOKE_TEST.md already
  uses the new names; if anything in your environment references the
  old ones, that's stale.
- Identity key now lives at `~/.chaos/keys/agent.key` (mode 0600). One
  key per role install, not separate seller/buyer keys.
- The cars plugin merged: `plugins/cars/` registers both
  `offering-cars` and `seeking-cars` skills. `plugins/cars-{seller,buyer}/`
  no longer exist.
- Wire field: `from_pubkey` (not `buyer_pubkey`). Counter-attestation
  arg: `parent_attestation_event_id` (not `seller_…`). Test suite is
  green (`uv run pytest`).

## What I want you to do, in order

1. **Pre-flight check** — before opening two terminals:
   - Confirm `uv sync` is clean (Python 3.12+, all workspace members
     resolve).
   - Confirm port 8765 is free locally
     (`lsof -nP -iTCP:8765 -sTCP:LISTEN || echo free`).
   - Confirm at least two public relays from
     `wss://relay.damus.io`, `wss://nos.lol`, `wss://relay.snort.social`,
     `wss://nostr-pub.wellorder.net`, `wss://relay.nostr.band` are
     reachable from this machine (`websocat -1 wss://relay.damus.io`
     or any equivalent works).
   - If `~/.chaos/keys/agent.key` already exists from a prior run,
     decide with me whether to reuse it (faster, same npub continuity)
     or `mv` it aside and regenerate (cleaner card).

2. **Run the runbook** — open two terminals as Step 1 / Step 2 of
   `mvp/SMOKE_TEST.md` direct, and walk through Steps 0–6. Capture the
   raw stdout from each terminal as you go. Don't paraphrase the output;
   I want the actual lines (`✓` / `✗` per relay, the hex64 event id,
   the `[match]` line, the `[mcp]` lines).

3. **Verify the cache** — Step 6 of the runbook. Confirm that
   `mvp/received/<offering_npub>/<item_id>/photos/` has the expected
   PNGs and `inspection.pdf` (or `.txt` for the sample) is present, and
   that the seeking agent printed `sha256 ✓` for every block.

4. **Fill in the evidence card** — using the template in SMOKE_TEST.md
   § "Smoke-test evidence card". Save the filled-in version somewhere
   sensible (suggest `mvp/evidence/<YYYY-MM-DD>.md`) so the deck and
   the README can link to it.

## Failure modes the runbook calls out — handle them, don't escalate

- **Public relay returns HTTP 503 under load** — `pynostr` already
  retries. Wait up to 60 s before declaring a publish failure. As long
  as ≥ 1 relay shows `✓`, the publish succeeded.
- **`[match]` doesn't arrive within 15 s** — relay indexing lag is
  real. Wait up to 60 s. If still nothing, the publish probably
  succeeded on a relay the seeking agent isn't subscribed to — look at
  the `[subscribe]` lines in terminal B and the `→ event` line in
  terminal A and confirm there's at least one relay in common.
- **`SSL: CERTIFICATE_VERIFY_FAILED`** — `agent_seeking.py`
  pre-points at `certifi`. If it still fails on macOS python.org
  builds, run
  `/Applications/Python\ 3.13/Install\ Certificates.command`.
- **MCP fetch hangs** — `mcp_url` in `sample_car.toml` is
  `http://127.0.0.1:8765/sse`. That works only on the same machine. If
  the two terminals are on different hosts, expose 8765 via
  `cloudflared tunnel` or `ngrok` and update the TOML before
  publishing.
- **Stale `__pycache__`** — if imports go weird,
  `find . -type d -name __pycache__ -exec rm -rf {} +` and re-run.

## What I do NOT want you to do

- Don't modify `mvp/SMOKE_TEST.md`, the MVP scripts, or any
  protocol code while running the test. The point is to prove the
  current code works as-is. If you find a bug, surface it and we'll
  decide together — don't silently patch and re-run.
- Don't introduce a new file host or a "just for testing" relay
  bypass. PoW must remain at ≥ 20 bits; binary content must stay on
  MCP. Those are AGENTS.md hard rules.
- Don't fake the evidence card. If a step fails, the card reflects it.

## Deliverables at end of session

1. The filled-in evidence card.
2. A short "what happened" summary: which relays accepted, latency
   numbers, any retries, anything surprising.
3. If the run was clean: a one-line PR-ready note we can drop into the
   deck and README ("Smoke test passed YYYY-MM-DD: <event id>, n/N
   relays, all SHA-256 ✓").
4. If the run had issues: a concrete list of follow-ups, ordered by
   what's blocking the Hermes pitch.

Start by reading `mvp/SMOKE_TEST.md` end-to-end before doing anything.
