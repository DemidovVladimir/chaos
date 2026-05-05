# Attestation schema — exact JSON shapes

These shapes describe the **Nostr event JSON** as it appears on
the wire (post-NIP-01 serialization). Field caps are enforced by
publishers and re-checked by the reputation-mcp on read.

## Common rules

- Every `content` field passes `shared/input_safety.py`:
  NFKC-normalize, strip invisible Unicode, strip reserved tags,
  cap length, phrase-scan.
- Every event signed with the publisher's secp256k1 key per
  NIP-01. Signatures verified before any reputation effect.
- PoW per `kinds.md`. Below the floor → silently dropped by
  reputation-mcp.
- Tags follow the NIP-01 array-of-arrays form: `["tag_name",
  "value", "...optional extras..."]`.
- Timestamps are unix seconds (UTC).

## kind 30410 — sale-attestation

```json
{
  "kind": 30410,
  "pubkey": "<publisher hex pubkey>",
  "created_at": 1714742400,
  "tags": [
    ["d", "550e8400-e29b-41d4-a716-446655440000"],
    ["e", "<listing-event-id hex>"],
    ["p", "<counterparty hex pubkey>"],
    ["pack", "cars-pack@1"],
    ["status", "completed-clean"],
    ["currency_band", "15k-50k"],
    ["sale_closed_at", "1714710000"]
  ],
  "content": "Sold to a friendly seeking agent, no surprises.",
  "id": "<sha256 of canonical serialization>",
  "sig": "<schnorr sig hex>"
}
```

Field validation:

- `d` — exactly one tag, value matches UUID v4 regex.
- `e` — exactly one tag, value matches `^[0-9a-f]{64}$`.
- `p` — exactly one tag, hex pubkey, must differ from
  `pubkey`.
- `pack` — exactly one tag, matches `^[a-z][a-z0-9-]+@[0-9]+$`.
- `status` — one of `completed-clean`, `disputed-by-me`,
  `counterparty-vanished`.
- `currency_band` — one of the documented bands; **never an exact
  number**. Reputation-mcp rejects events that contain a digit-run
  ≥ 4 in this field.
- `sale_closed_at` — unix seconds, within ± 30 days of
  `created_at`.
- `content` — ≤ 1024 bytes UTF-8 after `input_safety`.
- PoW — ≥ 16 leading zero bits on `id`.

## kind 30411 — counter-attestation

```json
{
  "kind": 30411,
  "pubkey": "<counterparty hex pubkey>",
  "created_at": 1714746000,
  "tags": [
    ["d", "550e8400-e29b-41d4-a716-446655440000"],
    ["e", "<the 30410 event-id>"],
    ["p", "<original publisher pubkey>"],
    ["pack", "cars-pack@1"],
    ["status", "confirmed"]
  ],
  "content": "Confirms. Smooth sale.",
  "id": "<...>",
  "sig": "<...>"
}
```

Field validation:

- `d` — must equal the 30410's `d` for the pair to count as
  bilateral.
- `e` — points at the 30410 event-id (NOT the listing).
- `p` — must equal the 30410's `pubkey`.
- `pack` — must equal the 30410's `pack`.
- `status` — `confirmed` or `disputed`.
- `created_at` — within 14 days of the 30410's `created_at` to
  count as the bilateral pair (later 30411s still publish but are
  weighted lower by reputation-mcp).
- PoW ≥ 16.

## kind 30412 — dispute-attestation (unilateral)

Same as 30410 plus:

```json
{
  "tags": [
    ["d", "<uuid>"],
    ["e", "<listing or 30410 event-id>"],
    ["p", "<counterparty pubkey>"],
    ["pack", "cars-pack@1"],
    ["status", "counterparty-vanished"],
    ["currency_band", "15k-50k"],
    ["sale_closed_at", "1714710000"],
    ["reason_short", "seeking agent ghosted after deposit"]
  ]
}
```

- `reason_short` — ≤ 80 bytes after `input_safety`. Required.
- Otherwise same validation as 30410.

## kind 30430 — admin-decision

```json
{
  "kind": 30430,
  "pubkey": "<admin-agent pubkey>",
  "created_at": 1714800000,
  "tags": [
    ["d", "<dispute-uuid>"],
    ["p", "<affected pubkey>"],
    ["e", "<related event-id>"],
    ["pack", "cars-pack@1"],
    ["decision", "warning"],
    ["severity", "moderate"],
    ["reason_hash", "<64 hex chars>"],
    ["appeal_until", "1717392000"]
  ],
  "content": "Decision: warning. Communication breakdown after deposit.",
  "id": "<...>",
  "sig": "<...>"
}
```

Field validation:

- `decision` — exactly one tag, one of the four enum values.
- `severity` — one of `low`, `moderate`, `high`.
- `reason_hash` — sha256 hex of the admin-agent's internal
  reasoning notes. **Computation:** `sha256(salt || notes_utf8)`
  where `salt` is the dispute-id; this binds the hash to the
  case so the admin can't reuse a hash across cases.
- `appeal_until` — `created_at + 30 * 86400`. Hard requirement.
- `content` — ≤ 280 bytes, no PII beyond pubkeys, `input_safety`.
- PoW ≥ 20 bits.

## kind 30431 — appeal

```json
{
  "kind": 30431,
  "pubkey": "<affected party pubkey>",
  "created_at": 1714820000,
  "tags": [
    ["d", "<appeal-uuid>"],
    ["e", "<the 30430 event-id>"],
    ["p", "<admin-agent pubkey>"],
    ["pack", "cars-pack@1"],
    ["status", "appeal"],
    ["evidence_hash", "<64 hex chars>"]
  ],
  "content": "Appealing — see attached evidence package via MCP.",
  "id": "<...>",
  "sig": "<...>"
}
```

- `evidence_hash` — sha256 hex of the encrypted evidence package
  the appellant has prepared. Real bytes flow over MCP per Rule 13.

## Bilateral pair semantics

A "valid attestation" for reputation purposes is the pair
(30410, 30411) where:

1. Both events pass signature + PoW checks.
2. The 30411's `d` equals the 30410's `d`.
3. The 30411's `e` points at the 30410's id.
4. Their pubkeys are each other's `p` tag.
5. `pack` matches.
6. `created_at` of the 30411 is within 14 days of the 30410's.

Reputation-mcp returns the pair as a single record with
`status_pair` = `(seller_status, buyer_status)`. Mismatched pairs
(e.g. one says `completed-clean` and the other `disputed`) are
flagged in the breakdown — they don't count as positive evidence
for either side.

## Examples

- **Clean sale:** offering agent publishes 30410 `completed-clean`; seeking agent
  publishes 30411 `confirmed`. Both within a week. Both PoW ≥ 16.
  Reputation-mcp records `+0.05` to each (capped, decays over
  365d).
- **Seeking agent ghosting:** offering agent publishes 30412
  `counterparty-vanished` with `reason_short`. No 30411 ever
  arrives. Counts as a unilateral negative against seeking agent, but at
  half the weight a paired attestation would carry.
- **Disputed sale:** offering agent publishes 30410 `disputed-by-me`;
  seeking agent publishes 30411 `disputed`. Both parties have signaled a
  dispute exists. The dispute is then routed to the admin-agent
  per `dispute_protocol.md`.
