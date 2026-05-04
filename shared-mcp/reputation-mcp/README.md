# `reputation-mcp` — layered trust-signal aggregation

Universal across verticals. Every vertical needs a way to ask "what
do I know about this seller pubkey?" without depending on a central
reputation oracle.

## Why this MCP

`CLAUDE.md` rule 4 says trust must be **layered, not centralized**.
This MCP is the layering point. It reads multiple sources, weights
them, and returns a structured `ReputationReport` the buyer skill
can use as one input among many. It does NOT make the gatekeeping
decision for the user.

The MCP also implements the **peer-attestation submission** path
(rules 12 and 13 of `CLAUDE.md`) and the **counter-attestation /
dispute** path (rule 14). It NEVER stores reputation centrally —
attestations are signed Nostr events; aggregation is per-query and
in-memory only.

## Trust signals layered here

1. **NIP-58 badges** issued by operator(s) the user trusts.
2. **NIP-99 listing history** of the pubkey (counts, recency, churn).
3. **Bilateral peer attestations** — kind 30410 (sale-attestation)
   plus kind 30411 (counter-attestation). The pair counts as one
   "valid attestation" only when both sides have signed.
4. **Unilateral dispute-attestations** (kind 30412) — used when the
   counterparty refuses to acknowledge a sale. Weighted lower than
   a paired attestation by default.
5. **Admin-agent decisions** (kind 30430) and **appeals** (kind
   30431) — published by an opt-in admin-agent the user has added
   to their trust list.
6. **Web-of-trust depth** — distance from a user-trusted seed pubkey
   along NIP-02 follow graphs.
7. **On-chain stake** — optional Phase 1 hook. The MVP returns
   `null`; later we can wire a small bonded-stake check (e.g. an
   on-chain commitment the seller posted, queryable via a free
   public RPC). Per `CLAUDE.md` Rules 12–14 the on-chain stake is
   **never** custodied by us; we only read it.

See `reputation/scoring.md` for the reference algorithm and
per-user configurable weights, and `reputation/kinds.md` for the
canonical kind-number registry.

## Tool surface

- `get_reputation(pubkey, vertical_pack) -> ReputationReport`
- `submit_peer_attestation(...)` — kind 30410 sale-attestation
- `submit_counter_attestation(...)` — kind 30411 counter-attestation
- `submit_dispute_attestation(...)` — kind 30412 unilateral
  dispute-attestation (when the counterparty refuses to acknowledge
  a sale)

## Status

**The MVP is real, no longer stubbed.** This MCP now performs live
relay round-trips, signature verification (via pynostr), pairing of
30410+30411 events, NIP-02 web-of-trust traversal, and reference
scoring per `reputation/scoring.md`.

What works today:

- NIP-58 badge reads (kind 8) plus pair-revocation detection (NIP-09
  deletion + matching kind 30430 `decision=flag` per
  `operator_revocation.md`).
- Bilateral peer attestations: kind 30410 sale-attestation paired
  with kind 30411 counter-attestation on shared `d` tag within the
  14-day pair window.
- Unilateral kind 30412 dispute-attestation (half the weight of a
  paired one).
- Admin decisions kind 30430 with appeal-freeze when a 30431 exists.
- NIP-02 contact graph (kind 3), depth-2 by default; depth-4 in the
  pro tier.
- Phase-1 onchain stake placeholder (`_check_onchain_stake()`) that
  returns None — wire-up lands with `STAKE.md`.

NIPs supported on this server:
NIP-01 (events / signatures), NIP-02 (contacts / WoT), NIP-09
(deletion-as-revocation signal), NIP-58 (badges), and the custom
chaos kinds 30410/30411/30412/30430/30431.

## How agents call this MCP

The MCP listens on `http://127.0.0.1:7612/sse` by default. From
Hermes/MCP clients call:

- `get_reputation(pubkey, vertical_pack="cars-pack@1",
  relays=[...], user_pubkey=<viewer>, admin_trust={...},
  trust_issuers={...})` — returns the layered report.

- `submit_peer_attestation(sale_id, counterparty_pubkey,
  listing_event_id, status, currency_band, pack, relays,
  signing_key_hex, note)` — publishes a kind 30410.

- `submit_counter_attestation(sale_id, seller_attestation_event_id,
  seller_pubkey, status, pack, relays, signing_key_hex, note)` —
  publishes a kind 30411.

- `submit_dispute_attestation(sale_id, counterparty_pubkey,
  listing_event_id, reason_short, currency_band, pack, relays,
  signing_key_hex, note)` — publishes a kind 30412.

### `signing_key_hex` is required

Every submit tool refuses to run without `signing_key_hex`. The MCP
is local-only: keys come from the calling agent's local keystore at
`~/.chaos/<role>/seller.key` (mode 0600, per CLAUDE.md Rule 3)
and are passed in only at call time. The server never logs the
signing key, never persists it, and never derives identity from
anywhere else.

The buyer's skill calls `get_reputation` with the user's own pubkey
in `user_pubkey` so the WoT walk is anchored correctly. The seller's
skill calls `submit_peer_attestation` after a sale closes; the buyer
follows up with `submit_counter_attestation` referencing the
seller's 30410 event id. If the counterparty disappears, either
party may publish `submit_dispute_attestation`.

## Tests

```
pip install -e .[dev]
pytest tests/
```

Tests mock relay I/O and pynostr signing, so they run offline.

## Tier mode

- **Fast (free)**: badges + listing history + a shallow WoT depth
  (≤ 2 hops).
- **Thorough (pro)**: deeper WoT (≤ 4 hops), broader attestation
  scan, optional on-chain stake read. Flipped on by
  `chaos-pro`.

## Threat model

- No outbound HTTP except (a) user-configured Nostr relays via WSS
  and (b) optional on-chain RPC against a public free endpoint when
  `tier=thorough` and the user opts in.
- No retention of pubkeys or attestation content beyond the request.
- All received attestations are sanitized through
  `shared/input_safety.py` before any text field is logged or
  surfaced.
