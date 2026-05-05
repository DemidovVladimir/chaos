# Custom Nostr kinds — chaos reputation layer

All kinds below are in the parametrized-replaceable range
(30000–39999) per NIP-01. Each is a regular signed Nostr event;
the `kind` integer is what marks it as a chaos reputation
event. PoW (NIP-13) requirements per kind below.

## Summary table

| Kind  | Name                  | Status      | Signed by         | PoW   | Retention                     | Replaceable                     |
| ----- | --------------------- | ----------- | ----------------- | ----- | ----------------------------- | ------------------------------- |
| 30410 | sale-attestation      | live        | offering agent or seeking agent   | ≥ 16  | indefinite (until reissued)   | yes, on `(pubkey, kind, d)`     |
| 30411 | counter-attestation   | live        | counterparty      | ≥ 16  | indefinite (until reissued)   | yes, on `(pubkey, kind, d)`     |
| 30412 | dispute-attestation   | live        | unilateral        | ≥ 16  | indefinite                    | yes                             |
| 30420 | identity-binding      | placeholder | offering agent (Phase 1)  | ≥ 20  | indefinite                    | yes                             |
| 30421 | stake-commitment      | placeholder | offering agent (Phase 1)  | ≥ 20  | indefinite                    | yes                             |
| 30422 | slash-record          | placeholder | multi-sig 2-of-3  | ≥ 20  | indefinite                    | no                              |
| 30430 | admin-decision        | live        | admin-agent       | ≥ 20  | indefinite (relay-side)       | no                              |
| 30431 | appeal                | live        | affected party    | ≥ 20  | indefinite                    | yes, on `(pubkey, kind, d)`     |

## kind 30410 — sale-attestation

Either party publishes after a sale closes (or fails). The pair
30410+30411 from both parties is what makes the attestation
"valid"; a lone 30410 is a claim, not a fact.

- **Signed by:** the publishing party (offering agent OR seeking agent).
- **Tag schema:**
  - `d` — sale-id (UUID v4 chosen by publisher; the same UUID is
    used by the counterparty's 30411).
  - `e` — listing event-id (the NIP-99 30402 the sale relates to).
  - `p` — counterparty pubkey.
  - `pack` — vertical pack identifier (e.g. `cars-pack@1`).
  - `status` — one of `completed-clean`, `disputed-by-me`,
    `counterparty-vanished`.
  - `currency_band` — coarse band only, e.g. `5k-15k`,
    `15k-50k`, `50k-150k`, `150k+`. **Never an exact price.**
  - `sale_closed_at` — unix ts of the close (or last contact for
    `counterparty-vanished`).
- **Content:** short note (≤ 1 KB) the publisher wants to attach;
  passes through `input_safety`.
- **PoW:** ≥ 16 bits.
- **Read by:** reputation-mcp, seeking agent/offering agent skills.
- **Replaceable:** yes — `(pubkey, kind, d)` replaces. A publisher
  may correct a typo by re-issuing with the same `d`.

## kind 30411 — counter-attestation

The counterparty's matching attestation. Without this, the 30410
counts only as a claim by one side.

- **Signed by:** the counterparty named in the 30410's `p` tag.
- **Tag schema:**
  - `d` — same sale-id as the 30410 it counters.
  - `e` — the 30410 event-id.
  - `p` — original publisher pubkey.
  - `pack` — same as 30410.
  - `status` — `confirmed` or `disputed`.
- **Content:** short note (≤ 1 KB), `input_safety`.
- **PoW:** ≥ 16 bits.
- **Replaceable:** yes on `(pubkey, kind, d)`.

## kind 30412 — dispute-attestation

Unilateral. Used when the counterparty refuses to publish a 30411
at all (e.g. a vanished offering agent). Carries less weight than a paired
30410+30411 but is not zero.

- **Signed by:** the aggrieved party.
- **Tag schema:** same shape as 30410, plus `reason_short` tag
  (≤ 80 chars, `input_safety`-cleaned).
- **PoW:** ≥ 16 bits.
- **Replaceable:** yes.

## kind 30420 — identity-binding (PLACEHOLDER, Phase 1)

Binds a Nostr secp256k1 pubkey to a Solana ed25519 pubkey via
mutual signature. Empty in MVP; the real schema lands in
`STAKE.md` follow-up.

## kind 30421 — stake-commitment (PLACEHOLDER, Phase 1)

Points at the on-chain stake account; carries amount and lock
period. Not used in MVP.

## kind 30422 — slash-record (PLACEHOLDER, Phase 1)

Multi-sig 2-of-3 record of an enforced slash. Not replaceable.
Multi-sig requirement means the admin alone can never publish a
30422.

## kind 30430 — admin-decision

Published by the admin-agent after a dispute is resolved (or
escalated to human queue and then resolved). Public, signed,
auditable. Admin can only emit "soft" signals — clear, warning,
flag, escalated. Hard slash requires the future kind 30422 with
multi-sig.

- **Signed by:** the admin-agent's pubkey (declared in
  `operator/cars/admin-agent/pubkey.json`).
- **Tag schema:**
  - `d` — dispute-id (UUID v4 chosen by admin-agent at intake).
  - `p` — affected pubkey (the party the decision is about). May
    appear twice if both parties are tagged for the same case.
  - `e` — related event id (listing event, or 30410 / 30412 the
    dispute concerns).
  - `pack` — vertical pack identifier.
  - `decision` — one of `clear`, `warning`, `flag`, `escalated`.
  - `severity` — `low`, `moderate`, or `high`.
  - `reason_hash` — sha256 hex of the admin-agent's internal
    notes. Privacy-preserving: the public event reveals that a
    decision exists and its category, but never plaintext rationale.
  - `appeal_until` — unix ts, decided_at + 30 days.
- **Content:** very short public summary (≤ 280 chars), already
  `input_safety`-sanitized, free of names/PII beyond the pubkeys
  in `p` tags.
- **PoW:** ≥ 20 bits.
- **Read by:** reputation-mcp, seeking agent/offering agent/admin skills, anyone.
- **Replaceable:** **no** — corrections happen via a new 30430
  with a different `d` plus an appeal trail.
- **Co-sign requirement:** if `severity == high`, the admin-agent
  MUST hold a human operator co-signature (out-of-band) before
  publishing. See `admin_threat_model.md`.

## kind 30431 — appeal

Published by the affected party after a 30430 they disagree with.

- **Signed by:** the affected party (one of the pubkeys named in
  the 30430's `p` tags).
- **Tag schema:**
  - `d` — appeal-id (UUID v4).
  - `e` — the 30430 event-id being appealed.
  - `p` — admin-agent pubkey.
  - `pack` — same as 30430.
  - `status` — `appeal` (the only legal value at v1).
  - `evidence_hash` — sha256 hex of the encrypted evidence
    package the appellant has prepared (real bytes flow over MCP,
    not the relay).
- **Content:** short public note (≤ 280 chars), `input_safety`.
- **PoW:** ≥ 20 bits.
- **Replaceable:** yes on `(pubkey, kind, d)`.

## Read-side rules

- A 30410 without a matching 30411 = "unconfirmed claim".
- A 30410 + 30411 with matching `d`, both signed within 14 days
  of `sale_closed_at`, and both passing PoW = "valid attestation".
- A 30412 stands alone but reputation-mcp weights it lower than
  a paired attestation by default.
- A 30431 referencing a 30430 freezes the 30430's effective
  weight at 50% until the appeal is resolved (next 30430 with
  decision `clear` for that party + same `e`, OR appeal_until
  expires).
