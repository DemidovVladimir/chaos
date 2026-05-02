# `reverse-image-mcp` — first paid MCP

The first paid MCP for the cars pack (and broadly applicable to every
other vertical). Stores **only perceptual hashes**, never full images.
No third-party data dependency. Protocol-universal — works in
Hermes, Claude Desktop, Cursor, any MCP-compatible client.

## What it does

Given image bytes, return:

- A **perceptual hash** (pHash and dHash)
- **Match results** against a local hash database of known stock
  photos, scam-listing images, and previously-seen marketplace photos
- Optional **EXIF analysis** flag set (date inconsistencies, GPS
  that doesn't match the listing's stated location, missing EXIF on
  photos claimed as recent)
- A confidence score and human-readable explanation

It does NOT call Google Images, TinEye, or any third-party reverse-
image service. Everything is local, hash-based, and the database is
either bundled or distributed via Nostr (see "Hash distribution"
below).

## Why this is the right first paid MCP

1. **Strongest single fraud signal in marketplaces** — across cars,
   real estate, watches, livestock, services, the most common scam is
   reusing stock photos or photos lifted from prior listings.
2. **No data custody** — perceptual hashes are 64-bit fingerprints,
   not images. We never receive, store, or transmit user photos.
   The hashing happens locally; in the marketplace flow the MCP runs
   on the buyer's own machine on bytes the buyer's agent already
   received via ACP from the seller.
3. **Cross-vertical** — a single MCP serves cars, real estate,
   watches, and any future vertical.
4. **GDPR-clean** — no personal data touches the platform.
5. **Protocol-universal** — usable from any MCP client.

## MCP tool surface

```json
{
  "name": "reverse_image_check",
  "description": "Compute a perceptual hash of an image and check it against a local database of known stock images, scam-listing images, and previously-seen marketplace photos. Returns nearest matches with similarity score and a fraud-risk flag set. No third-party services are called; the image bytes are not retained.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "image_b64": {"type": "string",
                    "description": "Base64-encoded image bytes (max 10 MB). This is the canonical input — bytes the buyer's agent received via ACP from the seller, fed directly to the MCP without ever crossing a third party."},
      "image_url": {"type": "string",
                    "description": "OPTIONAL: HTTP(S) URL of the image, only useful for testing against publicly-published images (e.g. checking a stock-image library entry). The marketplace flow never uses this; it always passes bytes received over ACP."},
      "tier":      {"type": "string", "enum": ["fast", "thorough"],
                    "description": "fast = pHash + dHash only. thorough = also check EXIF, run optional CLIP semantic match, query the federated marketplace-photos hash registry."},
      "context":   {"type": "object",
                    "description": "Optional context for EXIF cross-checks.",
                    "properties": {
                      "stated_location": {"type": "string"},
                      "stated_date":     {"type": "string", "format": "date"}
                    }}
    },
    "oneOf": [{"required": ["image_b64"]}, {"required": ["image_url"]}]
  }
}
```

Returns:

```json
{
  "phash": "9f8c4b2a1e6c0d4f",
  "dhash": "7a4f3b8d2a1e6c0d",
  "matches": [
    {
      "kind": "stock_library",
      "source": "shutterstock_id_12345",
      "similarity": 0.97,
      "first_seen": "2019-06-22"
    },
    {
      "kind": "prior_listing",
      "source": "marketplace_event:30402:abc...",
      "similarity": 0.91,
      "first_seen": "2024-11-04",
      "publisher_pubkey": "9d3e..."
    }
  ],
  "exif": {
    "had_exif": true,
    "captured_at": "2024-08-15T14:23:00Z",
    "gps_consistent_with_stated_location": true,
    "warnings": []
  },
  "fraud_risk": "high",
  "fraud_reasons": [
    "image matches Shutterstock library with 97% similarity — likely stock photo",
    "image previously appeared in a different listing 6 months ago by another pubkey"
  ],
  "billed_units": 1,
  "tier_used": "thorough"
}
```

## Pricing

| Tier | Cost to user | Notes |
|---|---:|---|
| `fast` (pHash + dHash + bundled stock-library check) | **Free**, 100/day per pubkey | Catches the most common scams |
| `thorough` (adds EXIF + federated registry + optional CLIP) | **$0.10** per call | Margin product |

Volume tiers:

| Plan | $/month | Included `thorough` calls | Overage |
|---|---:|---:|---:|
| Personal | 0 | 0 | $0.10/call |
| Pro | $9 | 200 | $0.05/call |
| Power | $39 | 1,000 | $0.03/call |
| Whitelabel | custom | custom | custom |

## When the buyer-cars rubric uses this MCP

| Check | Tier | Trigger | Outcome on hit |
|---|---|---|---|
| Photos received via ACP match stock library | fast | every photo arriving in an ACP session | hard suppress + warn user |
| Photos seen before in another listing by a different pubkey | fast | every photo arriving via ACP | hard suppress + warn user |
| Detail photos match stock at lower confidence | thorough | every photo arriving via ACP | warn user, lower score |
| EXIF GPS contradicts stated location | thorough | every photo arriving via ACP | warn user |
| EXIF date contradicts stated `year` | thorough | every photo arriving via ACP | warn user |

## When the seller-cars skill uses this MCP

`seller-cars/SKILL.md` runs `fast` proactively against each photo the
user intends to share, before any ACP session delivers them, to flag
accidental stock-image inclusion. All local; no photos leave the
seller's machine.

## Hash distribution

We don't curate the stock-image database alone. Sources:

1. **Bundled with the MCP**: a starter database of ~500k known stock-
   image hashes from public stock-photo libraries. Updated
   quarterly.
2. **Federated via Nostr**: a custom Nostr event kind (e.g.
   `kind: 31000`, parameterized replaceable) that publishes "this
   image hash is associated with this scam listing". Anyone can
   issue these; clients weigh by issuer reputation.
3. **Local accumulation**: every photo the buyer's agent has seen is
   hashed and stored locally with provenance. Cross-listing reuse
   becomes detectable within the user's own corpus.
4. **Operator-curated set**: as the relay operator, you can publish
   your own scam-hash list (NIP-51 list under your pubkey).

## Implementation outline

```
reverse-image-mcp/
├── pyproject.toml
├── server.py
├── hashing/
│   ├── phash.py              perceptual hash (8x8 DCT)
│   ├── dhash.py              difference hash
│   ├── exif.py               EXIF parser + sanity checks
│   └── clip.py               optional CLIP embedding (thorough tier)
├── db/
│   ├── bundled.lmdb          starter stock-image hashes (~500k entries, ~5 MB)
│   ├── operator.lmdb         operator-curated scam hashes
│   ├── local.lmdb            per-user locally accumulated hashes
│   └── federated.py          subscribe to Nostr kind:31000 events for fresh hashes
├── auth.py
├── billing.py
└── cache.py
```

## Distribution

- npm + PyPI (self-hostable)
- Hosted endpoint at `https://photos.<your-domain>/mcp` (TLS in, no
  retention)
- Container image for users who want full local-only operation

## Roadmap

- v1.0 — pHash + dHash + bundled stock library (week 5–6)
- v1.1 — federated scam-hash registry via Nostr kind:31000
- v1.2 — EXIF cross-checks
- v1.3 — CLIP semantic match for `thorough` tier
- v2.0 — extend to video first-frame hashing for verticals where
  short videos are common
