# ml-inference-pack — vertical pack for model-inference endpoints

Pack: `ml-inference-pack@1`. A composable contract for matching
inference **providers** (operators of GPU-backed model endpoints) with
**consumers** (agents needing inference at a given price, latency,
and region) over Nostr discovery + MCP dialogue.

## Why this vertical

Inference is a commodity with high facet variance: same model, ten
different quantizations, twenty different GPUs, dozens of regions,
two-orders-of-magnitude price spread. Consumers today brute-force
this with bespoke aggregators; the protocol fits naturally because
the matching is structural (tag-filterable) and the demo / SLA
exchange is dialogic (MCP `tools/call`). Inference also benefits
from sovereign identity — providers want to publish endpoints
without registering with a centralized broker.

## Tag schema (sketch)

| Tag | Cardinality | Required | Purpose | Example |
|---|---|---|---|---|
| `model_family` | 1 | required | Base model lineage | `model_family,llama-3` |
| `model_size` | 1 | required | Parameter count band | `model_size,70b` |
| `quantization` | 1 | required | Weight quantization | `quantization,int4-awq` |
| `gpu_type` | 1..n | required | Hardware backing the endpoint | `gpu_type,h100-sxm` |
| `region` | 1..n | required | Datacenter region (ISO 3166-1) | `region,eu-west` |
| `price_per_mtok_in_cents` | 1 | required | Input pricing per million tokens (USD cents) | `price_per_mtok_in_cents,75` |
| `price_per_mtok_out_cents` | 1 | required | Output pricing per million tokens | `price_per_mtok_out_cents,300` |
| `latency_p50_ms` | 1 | required | First-token p50 latency | `latency_p50_ms,180` |
| `context_window` | 1 | required | Max context tokens | `context_window,131072` |
| `availability` | 1 | recommended | `24-7`, `business-hours`, `scheduled` | `availability,24-7` |
| `provenance` | 1 | recommended | `open-weights`, `proprietary-finetune`, `merged` | `provenance,open-weights` |
| `throughput_tok_per_s` | 1 | recommended | Sustained per-stream throughput | `throughput_tok_per_s,42` |

`d` (NIP-99 identifier), `title`, `summary`, `published_at`,
`expiration` follow base NIP-99. Long descriptions, system-prompt
caveats, and any benchmark images stay off-relay and flow over MCP.

## MCP tool surface (sketch)

| Tool | Args | Returns | Grant policy |
|---|---|---|---|
| `view_capabilities` | `{}` | TextContent (model card, quant details, hardware, supported tools/JSON-mode) | always-allow (public) |
| `request_demo_inference` | `{prompt, max_tokens, modality}` | TextContent or ImageContent (for image models); capped sample | always-allow within demo budget; rate-limited per buyer pubkey |
| `request_pricing_quote` | `{monthly_mtok_in, monthly_mtok_out, commitment_months}` | TextContent (volume-tiered quote, valid_until) | always-allow |
| `request_sla_terms` | `{}` | EmbeddedResource (signed SLA document) | always-allow |
| `submit_inference_job` | `{messages, params, license_token?}` | TextContent (completion) or job_id for streaming | user-confirm for first-time consumer; license-restricted models require valid `license_token` |
| `cancel_job` | `{job_id}` | TextContent (status) | always-allow if caller pubkey matches submitter |
| `request_attestation_bundle` | `{}` | EmbeddedResource (GPU remote-attestation quote, model-weight hash) | always-allow |

All tool returns route through the provider's own MCP server. No
third-party file hosts; attestation bundles and SLA docs are
`EmbeddedResource` blocks.

## Example listing (NIP-99 event sketch)

```json
{
  "kind": 30402,
  "tags": [
    ["d", "llama3-70b-int4-h100-euwest-001"],
    ["title", "Llama-3-70B int4-AWQ on H100 SXM, eu-west, 24/7"],
    ["summary", "Open-weights Llama-3-70B, int4-AWQ, 8x H100 SXM, p50 first-token 180ms, 131k ctx."],
    ["model_family", "llama-3"],
    ["model_size", "70b"],
    ["quantization", "int4-awq"],
    ["gpu_type", "h100-sxm"],
    ["region", "eu-west"],
    ["price_per_mtok_in_cents", "75"],
    ["price_per_mtok_out_cents", "300"],
    ["latency_p50_ms", "180"],
    ["context_window", "131072"],
    ["availability", "24-7"],
    ["provenance", "open-weights"],
    ["throughput_tok_per_s", "42"],
    ["published_at", "1736953200"]
  ],
  "content": "Open-weights Llama-3-70B served on bare-metal 8x H100 SXM in Frankfurt. Remote-attested GPU type. Demo prompt available via request_demo_inference."
}
```

## Capability MCPs needed

- `reputation-mcp` (existing, cross-vertical) — peer attestations and
  WoT scoring of providers
- `model-card-verifier-mcp` (new, vertical-specific) — fetches the
  provider's claimed open-weights repo (HuggingFace, IPFS) and
  cross-checks weight hash and architecture
- `inference-benchmark-mcp` (new, vertical-specific) — runs a small
  battery of canonical prompts via `request_demo_inference` and
  flags providers whose outputs diverge from the claimed model

`market-comp-mcp` reused with a vertical-pack adapter for
price-per-mtok comps. `reverse-image-mcp` is not relevant here.

## Trust signals specific to this vertical

- **NIP-58 badges**:
  - `verified-model-provider` — operator confirms provider runs
    open-weights without undisclosed fine-tune
  - `gpu-attested` — provider supplies a valid remote-attestation
    quote (NVIDIA Confidential Compute, AMD SEV-SNP)
  - `uptime-verified` — sustained 99.9% over a rolling window per
    consumer attestations
- **Attestations** (kinds 30410/30411): consumers attest to delivered
  latency, output quality vs reference model, and SLA compliance
- **Disputes** typically center on hidden fine-tune (claimed open-
  weights but outputs diverge), throttled throughput, or model swap
  mid-session. Resolved via `inference-benchmark-mcp` re-runs +
  admin-agent decisions kind 30430

## Status

Sketched, not implemented. Open to community implementation per
`VERTICALS.md` § "Anatomy of a new pack".
