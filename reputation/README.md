# `reputation/` — layered, distributed, computed-locally

This folder is **cross-vertical**. It defines the reputation model
that every vertical pack (cars-pack, real-estate-pack, …) inherits.
Pack-specific tweaks (e.g. cars-pack's currency_band tag) live in
the pack; the shape of the system lives here.

## Core principle

Reputation in chaos is **layered, distributed, and computed
locally**. There is no central reputation store. There is no
"official" ranking the platform publishes. Each agent fetches the
public signals from the relay, applies its user's trust weights,
and produces its own score.

This is a hard architectural commitment, not a default we'll relax
later. Centralizing reputation would (a) make us a marketplace
operator in the regulatory sense, (b) put us on the hook for libel
exposure when a score goes wrong, and (c) re-introduce the platform
risk we built on Nostr to avoid. See `AGENTS.md` Rules 12–16.

## The five layers (plus a future sixth)

1. **Operator-issued badges (NIP-58).** `verified-private-offering agent`,
   `verified-dealer`. One trust signal among many — never a
   gatekeeper. See `operator_revocation.md`.
2. **Bilateral peer attestations.** Custom kinds 30410
   (sale-attestation), 30411 (counter-attestation), 30412
   (dispute-attestation). A 30410 + 30411 pair from both parties
   is what counts as a "valid attestation". See
   `attestation_schema.md`.
3. **Mute lists (NIP-51).** Per-user lists, plus an operator-public
   list users may opt-in to follow. Soft signal, never hard
   blacklist.
4. **Web of trust (NIP-02).** Each agent walks the contact graph and
   weights signals by graph distance. See `scoring.md`.
5. **Admin-agent decisions (NEW).** Custom kinds 30430
   (admin-decision), 30431 (appeal). A Hermes instance run by the
   operator applies the per-pack rubric to disputes and publishes
   signed verdicts. **Admin trust is opt-in**: a user must
   explicitly add the admin-pubkey to their trust list. See
   `dispute_protocol.md` and `admin_threat_model.md`.
6. **Future (Phase 1) — opt-in onchain staking.** Custom kinds
   30420 / 30421 / 30422 are placeholders. NOT in MVP. See
   `STAKE.md`.

## Aggregation

`shared-mcp/reputation-mcp/` exposes `get_reputation(pubkey,
vertical_pack)` which collapses the layers above into a single
`score_aggregate` ∈ [0, 1] using the user's configured weights.
The reference algorithm is in `scoring.md`. The MCP returns the
component breakdown alongside the aggregate so the seeking agent's skill
can show "why" — never just a number.

## Files in this folder

- `kinds.md` — every custom Nostr kind we use, with full tag
  schemas, signing party, retention, and replaceable behavior.
- `attestation_schema.md` — JSON shapes, validation rules,
  signature and PoW requirements, bilateral-pair semantics.
- `scoring.md` — reference WoT-weighted aggregation algorithm and
  per-user configurable weights.
- `operator_revocation.md` — when and how the operator revokes
  badges; transparency requirement; restoration policy.
- `dispute_protocol.md` — end-to-end flow from submitter packaging
  evidence to admin-agent publishing a signed decision.
- `admin_threat_model.md` — exhaustive prompt-injection threat
  model for the admin-agent skill.
- `STAKE.md` — Phase 1 placeholder for opt-in Solana staking.

## Cross-references

- `AGENTS.md` Rule 12 — discovery is Nostr-only.
- `AGENTS.md` Rule 13 — binary content moves over MCP only.
- `AGENTS.md` Rule 14 — trust signals layered, not centralized.
- `AGENTS.md` Rule 15 — admin-agent input safety + escalate-on-
  ambiguity.
- `AGENTS.md` Rule 16 — admin trust is opt-in.

## Non-goals

- No central reputation store, ever.
- No "official" platform ranking.
- No machine-learned model that combines layers behind a black
  box — the algorithm is open and the weights are user-configurable.
- No gating of protocol access on reputation. Low score reduces
  seeking agent/offering agent appetite to engage; it never blocks the wire.
