# data-licensing-pack — vertical pack for dataset licensing

Pack: `data-licensing-pack@1`. A composable contract for matching
**dataset offerers** (researchers, companies with proprietary
collections) with **dataset seekers** (model trainers, analysts) over
Nostr discovery + MCP dialogue, without custodying the data itself.

## Why this vertical

Datasets are the highest-stakes, lowest-trust good in modern ML.
Buyers can't evaluate without a sample; offerers can't release a
sample without leakage risk. The protocol fits because (a) discovery
on standard facets (modality, domain, size, license) is a clean
tag-filter problem, (b) the sample-and-provenance dialogue is
exactly what MCP `tools/call` was designed for, and (c) sovereign
identity matters more here than anywhere — researchers want to
publish without registering with a data broker.

## Tag schema (sketch)

| Tag | Cardinality | Required | Purpose | Example |
|---|---|---|---|---|
| `data_type` | 1..n | required | Modality | `data_type,text` |
| `domain` | 1..n | required | Subject area | `domain,medical-imaging` |
| `size_band` | 1 | required | Coarse size bucket | `size_band,10-100gb` |
| `row_count_band` | 1 | recommended | Rows / examples / files | `row_count_band,1m-10m` |
| `license_family` | 1 | required | Top-level license class | `license_family,cc-by-sa` |
| `sample_available` | 1 | required | Boolean | `sample_available,yes` |
| `region_origin` | 1..n | required | Data-collection region (ISO 3166-1) | `region_origin,us` |
| `language` | 1..n | recommended | BCP-47 (text/audio only) | `language,en` |
| `update_frequency` | 1 | recommended | `one-shot`, `daily`, `weekly`, `monthly` | `update_frequency,monthly` |
| `compliance_attested` | 1..n | recommended | Attestation classes | `compliance_attested,gdpr` |
| `collection_method` | 1 | recommended | `crawled`, `licensed`, `synthetic`, `consented` | `collection_method,consented` |
| `pii_class` | 1 | required | `none`, `pseudonymous`, `pii-removed`, `phi` | `pii_class,pii-removed` |

`d`, `title`, `summary`, `published_at`, `expiration` follow base
NIP-99. Full data dictionaries, sample rows, and provenance proofs
stay off-relay.

## MCP tool surface (sketch)

| Tool | Args | Returns | Grant policy |
|---|---|---|---|
| `view_dataset_card` | `{}` | TextContent (schema, statistics, collection method, citation) | always-allow (public) |
| `request_sample` | `{n_rows?}` | EmbeddedResource (≤100-row CSV / image bundle ≤25 items / audio ≤30s clip) | always-allow within sample budget; per-caller-pubkey rate limit |
| `request_license_terms` | `{intended_use}` | EmbeddedResource (signed license document) | always-allow |
| `request_provenance_proof` | `{}` | EmbeddedResource (cryptographic chain: source attestations, consent receipts, hash-tree root) | user-confirm (offerer reveals collection chain) |
| `request_compliance_evidence` | `{framework}` | EmbeddedResource (HIPAA/GDPR/SOC2 audit summary) | always-allow if framework is publicly claimed |
| `submit_purchase` | `{license_tier, contact_pubkey}` | TextContent (delivery_id + delivery instructions) | user-confirm |
| `cancel_inquiry` | `{inquiry_id}` | TextContent (status) | always-allow if caller pubkey matches submitter |

All sample bytes and license documents flow as `EmbeddedResource` /
`ImageContent` blocks from the offerer's own MCP server. The
platform never sees the dataset.

## Example listing (NIP-99 event sketch)

```json
{
  "kind": 30402,
  "tags": [
    ["d", "chest-xray-anonymized-2024-q4"],
    ["title", "Anonymized chest-X-ray corpus, 2.1M images, consented"],
    ["summary", "DICOM + PNG, 2.1M images from 14 partner clinics, PHI removed, IRB-approved."],
    ["data_type", "image"],
    ["domain", "medical-imaging"],
    ["size_band", "100gb-plus"],
    ["row_count_band", "1m-10m"],
    ["license_family", "proprietary"],
    ["sample_available", "yes"],
    ["region_origin", "us"],
    ["region_origin", "ca"],
    ["update_frequency", "quarterly"],
    ["compliance_attested", "hipaa"],
    ["collection_method", "consented"],
    ["pii_class", "phi-removed"],
    ["published_at", "1736953200"]
  ],
  "content": "Anonymized chest X-rays with radiologist labels. Sample of 50 images via request_sample. Provenance chain available via request_provenance_proof under NDA."
}
```

## Capability MCPs needed

- `reputation-mcp` (existing, cross-vertical) — bilateral
  attestations from prior buyers
- `market-comp-mcp` (existing, cross-vertical) — price comps across
  comparable datasets already on the network
- `dataset-fingerprint-mcp` (new, vertical-specific) — perceptual /
  Bloom-filter fingerprinting to detect re-licensed public datasets
  being marketed as private (e.g., LAION subsets resold as curated)

`reverse-image-mcp` is reused for image-modality datasets to detect
overlap with known public corpora.

## Trust signals specific to this vertical

- **NIP-58 badges**:
  - `verified-data-source` — operator validates a sample of
    provenance claims out-of-band
  - `compliance-attested-hipaa`, `compliance-attested-gdpr`,
    `compliance-attested-soc2` — operator confirms a current third-
    party audit (audit doc hash recorded in badge)
  - `irb-approved` — IRB approval letter validated for human-subject
    data
- **Attestations** (kinds 30410/30411): buyers attest to delivered
  size, schema accuracy, label quality, and licensing compliance
- **Disputes** center on misrepresented provenance (claimed
  consented; was scraped), license-class lies, or duplicate-of-
  public-corpus. Resolved via `dataset-fingerprint-mcp` evidence +
  admin-agent kind 30430

**Note**: this is the highest-stakes vertical sketched here.
Phase-1 staking (kinds 30420–30422) is the strongest trust amplifier
when it ships — offerers stake against their provenance claims.

## Status

Sketched, not implemented. Open to community implementation per
`VERTICALS.md` § "Anatomy of a new pack".
