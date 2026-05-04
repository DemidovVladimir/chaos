# specialist-services-pack — vertical pack for expert advisory services

Pack: `specialist-services-pack@1`. A composable contract for
matching **specialists** (legal / medical / financial / technical
advisory agents — human-in-loop or fully autonomous expert systems)
with **clients** (those seeking advice) over Nostr discovery + MCP
dialogue.

## Why this vertical

Expert advisory is structurally a discovery + dialogue problem:
clients filter on jurisdiction, practice area, and consultation
format, then enter a private MCP dialogue to scope a question and
receive an opinion. Sovereign identity matters here more than
anywhere else — credential portability across borders, and clients
who explicitly do not want a centralized broker correlating their
sensitive questions. The protocol's per-tool grant policy is what
makes this safe: every tool that touches PII is user-confirm by
default.

## Tag schema (sketch)

| Tag | Cardinality | Required | Purpose | Example |
|---|---|---|---|---|
| `practice_area` | 1..n | required | Top-level area + sub-area | `practice_area,legal-employment` |
| `jurisdiction` | 1..n | required (legal/financial); recommended (medical) | ISO 3166-1 + subdivision | `jurisdiction,us-ca` |
| `language` | 1..n | required | BCP-47 | `language,en` |
| `consultation_format` | 1..n | required | `async-text`, `scheduled-call`, `formal-opinion-document` | `consultation_format,async-text` |
| `specialty_certifications` | 1..n | recommended | Free-text cert list (board cert, fellowship) | `specialty_certifications,aaom-certified` |
| `fee_model` | 1..n | required | `per-hour`, `per-question`, `retainer`, `contingency` | `fee_model,per-question` |
| `years_experience_band` | 1 | recommended | `0-5`, `5-10`, `10-20`, `20-plus` | `years_experience_band,10-20` |
| `liability_insured` | 1 | recommended | Boolean (proof via tool) | `liability_insured,yes` |
| `accepts_pro_bono` | 1 | recommended | Boolean | `accepts_pro_bono,no` |
| `response_sla_hours` | 1 | recommended | First-response SLA | `response_sla_hours,24` |

`d`, `title`, `summary`, `published_at`, `expiration` follow base
NIP-99. **No specialist credentials' raw scans, no client PII, no
case content ever appears in NIP-99 tags or `content`.** Title and
summary stay generic ("IP litigation, Northern District of
California" — never client names or matter numbers).

## MCP tool surface (sketch)

| Tool | Args | Returns | Grant policy |
|---|---|---|---|
| `view_credentials` | `{}` | EmbeddedResource (bar admission letter, board cert, license PDF — public-record items only) | always-allow (public) |
| `request_consultation_terms` | `{format, scope_summary}` | EmbeddedResource (engagement-letter template, fee schedule) | always-allow |
| `submit_question` | `{intake: {summary, redacted_facts}}` | TextContent (intake_id + clarifying questions) | **user-confirm** — prompt warns about PII before send |
| `book_consultation` | `{intake_id, preferred_windows}` | TextContent (scheduled time + meeting URL — opaque to platform) | **user-confirm** |
| `request_formal_opinion` | `{intake_id, opinion_type}` | EmbeddedResource (drafted opinion document) | **user-confirm** — heavyweight tool; client confirms scope and fee |
| `request_insurance_proof` | `{}` | EmbeddedResource (current professional-liability cert) | always-allow |
| `cancel_consultation` | `{intake_id}` | TextContent (status, refund terms) | always-allow if caller pubkey matches submitter |

All credential docs, opinion documents, and engagement letters flow
as `EmbeddedResource` blocks from the specialist's own MCP server.
Meeting URLs are opaque to the platform — we don't know which video
service is used and we don't proxy the call.

## Example listing (NIP-99 event sketch)

```json
{
  "kind": 30402,
  "tags": [
    ["d", "ip-litigation-cand-001"],
    ["title", "IP litigation specialist — Northern District of California"],
    ["summary", "Patent and trade-secret litigation, 14 yrs at firm + in-house, async-text and call formats."],
    ["practice_area", "legal-ip"],
    ["jurisdiction", "us-ca"],
    ["jurisdiction", "us-federal"],
    ["language", "en"],
    ["consultation_format", "async-text"],
    ["consultation_format", "scheduled-call"],
    ["consultation_format", "formal-opinion-document"],
    ["fee_model", "per-hour"],
    ["fee_model", "retainer"],
    ["years_experience_band", "10-20"],
    ["liability_insured", "yes"],
    ["accepts_pro_bono", "no"],
    ["response_sla_hours", "24"],
    ["published_at", "1736953200"]
  ],
  "content": "Patent infringement and trade-secret matters. Engagement letter template via request_consultation_terms. Bar admission verifiable via view_credentials."
}
```

## Capability MCPs needed

- `reputation-mcp` (existing, cross-vertical) — bilateral
  attestations from prior clients (with privacy: clients may attest
  pseudonymously)
- `bar-id-verifier-mcp` (new, vertical-specific, legal sub-pack) —
  queries **public state-bar association registries** (CA, NY, etc.)
  by bar number to confirm active status. Public-record only —
  per Rule 6, this is not a commercial reseller
- `medical-license-verifier-mcp` (new, vertical-specific, medical
  sub-pack) — queries **public state medical-board registries** for
  active license status. Public-record only

`reverse-image-mcp` and `market-comp-mcp` are not core to this
vertical (no photos in scope; pricing too jurisdiction-dependent
for naive comps).

## Trust signals specific to this vertical

- **NIP-58 badges**:
  - `verified-bar-member-{us-ca}`, `verified-bar-member-{us-ny}`,
    etc. — operator confirms bar number against public registry
    at issuance and rolls renewal
  - `verified-medical-license-{us-ca}`, etc. — same pattern, public
    medical board registry
  - `professional-liability-insured` — operator verifies current
    coverage cert (insurance carrier, expiration, limits)
  - `board-certified-{specialty}` — issued for verifiable specialty
    board certifications
- **Attestations** (kinds 30410/30411): clients attest to delivered
  quality, responsiveness, and outcome (where measurable). Many
  attestations may be pseudonymous; `reputation-mcp` aggregates
  with provenance weighting
- **Disputes** center on misrepresented credentials (lapsed bar,
  expired license, fake board cert), missed SLA, or scope creep
  (formal opinion not delivered as scoped). Resolved via
  re-verification through verifier MCPs + admin-agent kind 30430

**Critical note**: this vertical surfaces sensitive PII (medical
history, legal facts, financial detail). The grant policy on every
tool that accepts or returns personal info is **user-confirm by
default** — the buyer skill MUST prompt with a PII warning before
calling `submit_question`, `book_consultation`, or
`request_formal_opinion`. Phase-1 staking (when shipped) plus
verifiable insurance proof are the strongest trust amplifiers in
this vertical.

## Status

Sketched, not implemented. Open to community implementation per
`VERTICALS.md` § "Anatomy of a new pack".
