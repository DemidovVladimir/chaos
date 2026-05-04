# Operator badge revocation

The operator issues NIP-58 badges (`verified-private-seller`,
`verified-dealer`). Issuance is a manual due-diligence process
documented in `operator/cars/`. **Revocation** is the
counterpart: when, why, and how the operator pulls a badge.

## When the operator revokes

A badge is revoked when at least one of:

1. The holder has accumulated ≥ 3 paired-attestation disputes
   (kind 30410+30411 with `status=disputed`) within 12 months,
   AND at least 2 of those have a matching admin-decision (30430)
   with `decision ∈ {warning, flag}` and `severity ≥ moderate`.
2. The holder is named in a single 30430 with `decision=flag` and
   `severity=high` that has been co-signed by a human operator
   per `admin_threat_model.md`.
3. The original due-diligence basis is invalidated (e.g. dealer
   license revoked by the relevant authority, identity proof
   later proven forged).
4. The holder requests revocation themselves (e.g. exiting the
   marketplace).

Cases 1 and 2 require the operator to give the holder ≥ 7 days'
notice via NIP-17 sealed DM, and to consider any response, before
publishing.

## Due-diligence checklist (every revocation)

Before publishing a revocation, the operator runs:

- [ ] Holder pubkey confirmed, badge currently active.
- [ ] Trigger condition (1 / 2 / 3 / 4 above) documented in the
      operator's case file with timestamps.
- [ ] If case 1 or 2: 7-day notice sent, response window passed,
      response (if any) reviewed.
- [ ] Public reason, sanitized of PII, ≤ 280 chars, drafted.
- [ ] Internal full reason notes hashed → `reason_hash`.
- [ ] If case 1 or 2 with severity=high: second human reviewer
      has signed off out-of-band.
- [ ] Restoration policy explained to holder.

## Revocation event format

We emit two events when revoking:

1. A NIP-09 deletion event (kind 5) targeting the original badge
   award event. Standard Nostr deletion semantics.
2. A `badge-revoked` event — kind 30430 (admin-decision) with:
   - `decision = flag` (revocation is a strong public signal)
   - `severity` matching the trigger
   - `e` pointing at the original NIP-58 badge-award event id
   - `p` the holder's pubkey
   - `reason_hash` = sha256 over the operator's case-file notes
   - `appeal_until` = `created_at + 30d`
   - `content`: short public reason (≤ 280 chars), no PII

The pair (NIP-09 deletion + 30430 flag) is what reputation-mcp
treats as a revocation. Either alone is insufficient: the
deletion alone could be a key compromise; the flag alone leaves
the badge "live" in caches.

## Transparency requirement

The 30430 above is public, signed, and auditable on the relay.
The `reason_hash` lets the operator commit to a specific rationale
without disclosing PII or third-party complaint content. If a
court later compels disclosure, the operator can reveal the
preimage, and any third party can verify.

The operator's own attestation log (a private `cases.jsonl` in
`operator/cars/`) maps `dispute_id → reason_hash → outcome`.
This file never leaves the operator's machine.

## Restoration policy

A revoked holder may apply for restoration after either:

- An accepted appeal (kind 30431) resolved in their favor — the
  operator publishes a fresh 30430 with `decision=clear`
  referencing the original revocation's `e` tag, and re-issues
  the original NIP-58 badge.
- 12 months elapsed since revocation, plus a clean record (no new
  30430 negative decisions) over that window, plus a fresh
  due-diligence pass.

Restoration is at the operator's discretion. The platform
publishes restoration on the same relay so the audit trail is
symmetric with revocation.

## What revocation is NOT

- Not a court order. The operator's verified-seller badge is one
  trust signal among many (Rule 14). Other trust signals — peer
  attestations, WoT, the user's own mute list — continue to
  operate independently.
- Not a wire-level block. Revoked sellers can still publish
  NIP-99 listings; relays still accept them subject to PoW and
  rate limits. What changes is how every viewer's reputation-mcp
  scores them.
- Not retroactive on prior sales. Past 30410+30411 pairs from
  before the revocation continue to count exactly as they did,
  with the same time-decay.
