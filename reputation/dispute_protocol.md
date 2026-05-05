# Dispute protocol — end-to-end flow

This document describes the full lifecycle of a dispute between a
seeking agent and a offering agent, from packaging evidence through a published
admin-decision and possible appeal.

The flow is **opt-in**: a user only invokes the admin-agent if
they have explicitly added the admin-pubkey to their trust list at
install time (Rule 16). Refusing to opt in costs nothing — the
sale-attestation, mute, and WoT layers continue to operate.

## Roles

- **Submitter** — the aggrieved party (seeking agent or offering agent).
- **Counterparty** — the other side of the disputed sale.
- **Admin-agent** — Hermes instance running the `admin-cars`
  skill, deployed under `operator/cars/admin-agent/`. Owns a
  declared pubkey listed in `pubkey.json`.
- **Human operator** — the person backing the admin-agent;
  reviews escalations and co-signs `severity=high` decisions.

## Step 1 — submitter packages evidence

The submitter's Hermes prepares an evidence package:

```
dispute-<uuid>/
  manifest.yaml            # case metadata: parties, listing event id, pack
  conversation_log.jsonl   # NIP-17 plaintext, decrypted from submitter's side
  listing_event.json       # the NIP-99 30402 the sale concerns
  my_attestations.json     # 30410 / 30411 / 30412 events submitter has published
  complaint.txt            # ≤ 4 KB after input_safety, submitter's narrative
```

The package is then:

1. Serialized as a tar of the directory.
2. Encrypted with NIP-44 to the admin-agent's pubkey.
3. Signed with the submitter's secp256k1 key.

## Step 2 — submitter calls `submit_dispute`

The submitter's seeking agent/offering agent skill opens an MCP HTTP+SSE session
against the admin-agent's MCP server (announced in the operator's
relay metadata) and calls:

```
submit_dispute(
    encrypted_package: bytes,         # tar + NIP-44 ciphertext
    signature: str,                   # over the ciphertext, hex
    submitter_pubkey: str,
) -> {"dispute_id": "<uuid>", "ack_event_id": "<...>"}
```

The submitter's event carries PoW ≥ 24 bits computed over the
ciphertext hash; submissions below the floor are rejected by the
admin-agent's MCP wrapper.

Anti-abuse gates applied at the wrapper layer **before** the
package is decrypted:

- Rate limit: 1 dispute submission per submitter pubkey per 7
  days, sliding window.
- Submitter-rep gate: submitter must hold either at least 1
  paired `completed-clean` attestation OR a verified-seeking agent /
  verified-offering agent / verified-dealer NIP-58 badge.
- Pattern detection: if N submitters have flagged the same
  counterparty within 24h with overlapping content hashes, the
  whole batch is held for human review (coordinated-fraud
  defense).

## Step 3 — admin-agent verifies & decrypts

- Verify submitter signature against the ciphertext.
- Verify PoW.
- NIP-44 decrypt **into memory only**. The plaintext tar is
  never written to disk. Per Rule 5, the admin-agent never
  custodies plaintext at rest.
- Extract `manifest.yaml`, `conversation_log.jsonl`,
  `listing_event.json`, `my_attestations.json`, `complaint.txt`.
- Run `input_safety` on every text field from every party
  (including conversation log entries, where each side is
  separately attributed). Wrap each in
  `<untrusted source="..." pubkey="..." dispute_id="...">` per
  `admin_threat_model.md`.

## Step 4 — admin-agent notifies counterparty

Admin-agent NIP-17 sealed DMs the counterparty:

> A dispute has been submitted naming you. Dispute-id: <uuid>.
> You have 7 days to respond by calling `submit_response(<uuid>)`
> on this MCP server. After 7 days, a decision will be issued
> based on the submitter's evidence alone.

The notification carries no submitter PII beyond the submitter's
pubkey (which the counterparty likely already knows).

## Step 5 — counterparty responds (or doesn't)

The counterparty packages their own evidence in the same shape and
calls `submit_response(dispute_id, encrypted_package, signature)`.
Same PoW + rate-limit + signature gates apply.

If the counterparty doesn't respond within 7 days:

- The admin-agent proceeds to step 6 with submitter-only evidence.
- The decision MUST carry an explicit "counterparty did not
  respond" flag in the admin-agent's internal notes — this affects
  what severity ranges are appropriate.
- Default behavior on no-response: issue at most a `warning` with
  `severity=low` unless the submitter's evidence is overwhelming
  and unambiguous.

## Step 6 — admin-agent applies rubric

The `admin-cars/SKILL.md` rubric is applied to the (possibly
two-sided) sanitized inputs. The rubric distinguishes:

- **Hard violations (auto-flag):** explicit fraud admission,
  theft, threats of violence, no-show after agreed test-drive
  with stake.
- **Soft violations (warning):** late delivery, miscommunication,
  partial misrepresentation.
- **Non-violations (clear):** seeking agent remorse, ambiguous quality
  dispute, civil disagreement.
- **Always escalate:** high-value (>$15k currency_band),
  cross-jurisdiction, novel pattern, contradictory evidence.

When the rubric says "escalate," the admin-agent:

1. Writes the dispute-id + sanitized summary to
   `operator/cars/admin-agent/escalation_queue/`.
2. Notifies both parties via NIP-17 that the case is in human
   review.
3. Does NOT publish a 30430 yet.
4. The human operator processes the queue, makes a decision, and
   passes it back to the admin-agent for publication. If
   `severity=high`, the human's signature is the required
   co-signature.

When the rubric is unambiguous, the admin-agent proceeds to step
6.

## Step 7 — admin-agent publishes 30430

Admin-agent constructs the kind 30430 event per
`attestation_schema.md`:

- `d` = dispute-id (UUID created at step 3).
- `p` tags = both parties.
- `e` = the listing or attestation the dispute concerns.
- `pack` = vertical pack (e.g. `cars-pack@1`).
- `decision` ∈ {clear, warning, flag, escalated}.
- `severity` ∈ {low, moderate, high}.
- `reason_hash` = `sha256(dispute_id || internal_notes_utf8)`.
- `appeal_until` = `created_at + 30 * 86400`.
- `content` ≤ 280 chars, sanitized.
- PoW ≥ 20 bits.

If `severity == high`, the admin-agent verifies it holds a fresh
human co-signature (out-of-band, file in
`operator/cars/admin-agent/escalation_queue/`) before publishing.

The 30430 lands on the relay; both parties' subscriptions surface
it; reputation-mcp picks it up on the next query.

## Step 8 — affected party may appeal

Any party named in the 30430's `p` tags may publish a kind 30431
appeal within `appeal_until`. The appeal:

- Carries `evidence_hash` for the appeal evidence package.
- Halves the effective weight of the original 30430 in
  reputation-mcp scoring until the appeal is resolved.
- Triggers the admin-agent to re-run steps 3–7 with the new
  evidence. Resolution is either a fresh 30430 (which supersedes
  the original for scoring) or a confirmation of the original.

## Privacy boundary

The admin-agent retains **only** structured decision data after 90
days:

```yaml
- dispute_id: <uuid>
  parties: [<pubkey-a>, <pubkey-b>]
  decision: warning
  severity: moderate
  reason_hash: <hex>
  decided_at: <ts>
  appeal_until: <ts>
  appealed: false
  human_co_signed: false
```

Plaintext conversation logs, complaint text, and evidence
packages are **purged at decision time**. The hashes live on; the
contents do not. See `operator/cars/admin-agent/retention/` for
the rotation script.

## Sequence summary

```
submitter ──submit_dispute(MCP)──> admin-agent
                                   │
                                   ├── verify sig + PoW
                                   ├── NIP-44 decrypt in-memory
                                   ├── input_safety + <untrusted> wrap
                                   │
admin-agent ──NIP-17 notify──────> counterparty
counterparty ──submit_response(MCP)─> admin-agent  (within 7 days, optional)
                                   │
                                   ├── apply rubric
                                   ├── if escalate → human queue → wait
                                   ├── if severity=high → require co-sign
                                   │
admin-agent ──publish kind 30430──> relay
                                   │
affected ──publish kind 30431─────> relay  (within 30 days, optional)
                                   │
admin-agent ──republish 30430─────> relay  (if appeal granted)
```

## Failure modes and what they look like

- **Submitter offers no evidence:** request is ack'd but moves
  straight to escalation; the human will likely close it.
- **Counterparty submits forged conversation log:** input_safety
  + cross-check against submitter's log surfaces the divergence;
  flagged as contradictory evidence → escalate.
- **Both parties claim victimhood, no clear violation:** rubric
  says "non-violation: civil disagreement" → publish `clear` for
  both, with `severity=low`. No reputation hit.
- **Admin-agent compromised / mis-issues a flag:** affected party
  appeals. Multiple coordinated appeals cause the operator to
  audit the admin-agent's logs and possibly rotate its pubkey
  (revoke trust, reissue under a new key, force users to re-opt-
  in).
