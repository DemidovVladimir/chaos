# Moderation policy — chaos Mode A relay

This is both the published policy (link from your relay's NIP-11
contact field and from the project website at
`moderation.<your-domain>`) and the operator's runbook.

## What this relay accepts

- NIP-99 classified listings (kinds 30402 / 30403) for cars and
  car-related goods
- NIP-17 sealed DMs (kinds 13 / 14 / 1059) for buyer↔seller inquiries
- Profile metadata (kind 0)
- NIP-51 personal lists (kinds 30000–30099) for follow / mute / etc.
- NIP-58 badge events (kinds 8 / 30009) for verified-seller signaling
- NIP-09 deletion requests (kind 5)
- NIP-32 labels (kind 1985) for tagging

## What this relay rejects

| Reason | Action |
|---|---|
| Kind not in the allowed set | Reject with reason `kind not supported` |
| PoW < 20 bits on listings | Reject with reason `pow too low` |
| Author on blocklist | `shadowReject` (silent drop) |
| Rate limit exceeded | Reject with reason `rate limit` |
| Event larger than 16 KB | Reject with reason `oversized` |
| `content` larger than 8 KB | Reject with reason `content too long` |
| Future-dated > 15 minutes | Reject with reason `clock skew` |
| Older than 1 year (replayed) | Reject with reason `too old` |

## What we manually moderate

We respond to abuse reports and proactive monitoring for:

- Stolen-vehicle listings
- Counterfeit / forged title indicators
- Listings violating sanctions
- Hate speech, harassment, illegal content in listing descriptions
- Spam patterns (sybil-style burst publishing, copy-paste of other
  listings, suspicious price-bait)
- Phishing / scam URLs in `webhook` or `acp` tag values

Reports go to `abuse@<your-domain>`. Triage target: 24 hours.

## Moderation actions, ordered

1. **Notify** — DM the seller's pubkey via NIP-17 with description
   of the issue and a 24h grace period to remove or update.
2. **Remove single event** — `strfry delete --filter
   '{"ids":["<event-id>"]}'`. Audited.
3. **Pubkey blocklist (silent shadow-reject)** — add to
   `pubkey_blocklist.txt`. Future events from this pubkey are
   accepted over the wire but never indexed. Less hostile than
   rejecting; lets the abuser waste effort.
4. **Pubkey blocklist (hard reject)** — for severe abuse. Future
   events return an explicit error.
5. **Reverse-proxy IP block** — for connection-level abuse (DoS,
   scrape floods). Caddy has a rate-limit module.
6. **Public disclosure** — for repeat severe offenders, publish a
   NIP-51 mute list under your operator pubkey naming the bad actors.
   Buyers can subscribe via the cars-pack default trust graph.

Every action is logged to `/var/lib/moderation/log.jsonl`:

```json
{"at": "2026-04-30T11:23:00Z",
 "actor": "<your-mod-pubkey>",
 "subject_pubkey": "<bad-pubkey>",
 "subject_event": "<event-id-or-null>",
 "action": "blocklist_shadow",
 "reason": "stolen vehicle reported by license_plate_match",
 "reporter": "abuse-report-id-12345"}
```

## What we do NOT moderate

- **Disagreements on price or condition** — between buyer and seller
- **Subjective taste** — listing photos that aren't pretty enough,
  awkward grammar, etc.
- **Off-platform interactions** — once buyer and seller exchange DMs,
  what happens between them is theirs
- **NIP-17 DM content** — we cannot read encrypted DMs. We cannot
  moderate them. We act only on metadata (sender pubkey, recipient
  pubkey, timestamp)

## Appeal process

Sellers / buyers who believe an action was wrong can appeal:

1. Email `abuse@<your-domain>` with their pubkey, the event id (if
   applicable), and the reason they believe the action was incorrect.
2. We respond within 5 business days.
3. We publish a quarterly transparency report listing aggregate
   moderation actions and appeal outcomes (no PII).

## Operator pubkey rotation

If our operator pubkey is compromised, we rotate. The rotation event
is published as a kind-0 update on the old pubkey announcing the new
one, signed by both keys (NIP-26 delegation chain), so dependents
(NIP-58 badge consumers, NIP-51 mute-list subscribers) can trust the
transition.

## Legal posture

We're a Nostr relay operator. Closest legal analogue: a web hosting
provider — we move bits, we honor takedown notices, we don't custody
funds or inventory. We are not a marketplace operator in the
regulatory sense.

We comply with:

- DMCA-style takedown notices (or local equivalent)
- Sanctions enforcement (geo-blocking, pubkey blocklists for sanctioned
  parties)
- Consumer-protection notices that apply specifically to relays (rare)

We do not:

- Verify identities at the protocol level (NIP-58 badge issuance is
  optional and lightweight)
- Hold escrow
- Process payments
- Mediate disputes beyond moderation actions above
