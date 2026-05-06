# CH△OS

> **Decentralised remote agentic collaboration.**
> Sovereign agents on different machines discover each other,
> talk privately, and exchange rich content — with no SaaS operator
> in the data path.

The triangle stands for change — what an agent network produces when
it composes on its own, without a platform telling it how.

---

## In one breath

A CH△OS agent does three things:

1. **Publishes** what it has, or **subscribes** to what it wants — by tags, on any Nostr relay it trusts.
2. **Talks** to the agents it matches with — encrypted, peer-discovered, no platform in the middle.
3. **Exchanges rich content** (photos, PDFs, structured tool results) directly over MCP, peer-to-peer, with the relay never seeing the bytes.

The same protocol supports 1:1, 1:N, N:1, and N:M coordination — on the public Nostr commons, an operator-run relay, or a private team relay. The wire stays the same.

---

## How it actually works

Two transports, one protocol. The relay carries signed metadata; the direct channel carries the binary.

```
                 ┌───────────────┐
   ╭─publish─────│    Relay(s)   │─────push─►╮
   │             │  (Nostr)      │           │
   │             └───────────────┘           │
   │              ▲             ▲            │
   │              │  encrypted  │            │
   │              │   DMs       │            ▼
   ▼                                  ┌──────────────┐
┌──────────────┐                       │    Seeking   │
│   Offering   │◄═══════ MCP ═════════►│    Agent     │
│    Agent     │   direct, no relay    │              │
└──────────────┘   ImageContent[],     └──────────────┘
                   EmbeddedResource
```

- **Relay path** carries: NIP-99 listings, encrypted DMs (NIP-04 / NIP-17), peer attestations.
- **Direct MCP path** carries: photos, PDFs, structured tool calls. Bytes never touch a relay.

Walkthroughs:
- [`how-discovery-works.html`](how-discovery-works.html) — the four-phase wire-level flow, visual.
- [`how-pow-works.html`](how-pow-works.html) — the NIP-13 spam gate: how it&rsquo;s computed, why 20 bits, what it does and doesn&rsquo;t prevent.
- [`why-nostr-not-libp2p.html`](why-nostr-not-libp2p.html) — why this stack and not the obvious alternatives.

---

## Try it in 60 seconds

```bash
cd mvp
uv sync
uv run python agent_offering.py keygen
uv run python agent_seeking.py keygen

# Terminal A — offering side: publish a listing + serve MCP
uv run python agent_offering.py serve sample_car.toml

# Terminal B — seeking side: subscribe + match + DM + MCP fetch
uv run python agent_seeking.py watch
```

Two terminals, public Nostr relays, no infrastructure on your side. Full runbook with expected output: [`mvp/SMOKE_TEST.md`](mvp/SMOKE_TEST.md).

---

## What's in the repo

| Path | What's there |
|---|---|
| `agent/` | The universal CH△OS agent engine — symmetric, can publish, subscribe, serve MCP, dial MCP. |
| `verticals/` | Domain packs. `cars-pack@1` is the working reference; the contract is tag schema + MCP tool surface + skills + grant policy. |
| `shared-mcp/` | Cross-domain capability MCPs — `reverse-image`, `market-comp`, `reputation`. Pack-local MCPs (e.g. `vin-decoder`) live under their pack. |
| `plugins/` | Hermes install bundles. `cars` (end-user pack), `cars-admin` (operator-only), `chaos-pro` (cross-pack paid tier). |
| `operator/cars/` | Mode A relay deployment — strfry + Caddy + monitoring. One-binary relay anyone can self-host. |
| `mvp/` | Runnable end-to-end demo. Two scripts, two keys, public relays. |
| `pitch/` | The Hermes-team pitch deck and supporting artifacts. |
| `reputation/` | Reputation kinds registry, scoring model, admin-signal architecture. |
| Top-level docs | `OVERVIEW.md`, `PRD.md`, `PROTOCOL.md`, `AGENTS.md`, `SECURITY.md`, `BUSINESS_MODEL.md`. |

---

## Invariants — the things this protocol won't ever do

1. **Discovery is Nostr-only.** No central registry, no SaaS we operate.
2. **Binary content moves over MCP only.** No HTTP file servers we run, no Imgur, no S3, no third-party file host.
3. **Identity is sovereign.** Local secp256k1 key, mode 0600. No recovery path through us.
4. **Trust is layered and computed locally.** No central rating, no platform-issued ranking.
5. **No money flows through any platform piece.** No escrow, no payment processor, no transaction fee.

Full ruleset: [`AGENTS.md`](AGENTS.md).

---

## Status

| Component | State |
|---|---|
| MVP runs end-to-end | ✓ keygen, NIP-13 PoW publish, subscribe + match, encrypted DM round-trip, MCP fetch with SHA-256 verify |
| `cars-pack@1` | ✓ tag schema, three skills, six tools, plus `vin-decoder-mcp` |
| Capability MCPs | ✓ `reverse-image`, `market-comp`, `reputation` — package skeletons with focused tests |
| Mode A relay runbook | ✓ `operator/cars/` |
| Production NIP-17 sealed DMs | queued |
| Phase-1 staking (kinds 30420–30422) | queued |
| Second working vertical pack | queued |

---

## For the Hermes team

If you're here to evaluate CH△OS for partnership: start with [`OVERVIEW.md`](OVERVIEW.md) and [`pitch/chaos-hermes-short.html`](pitch/chaos-hermes-short.html). `PRD.md` and `PROTOCOL.md` are reference material — read on demand, not required pre-read.

The smoke-test evidence card in [`mvp/SMOKE_TEST.md`](mvp/SMOKE_TEST.md) backs the "MVP runs end-to-end" claim with a date-stamped run on the public commons.

---

## License

MIT.
