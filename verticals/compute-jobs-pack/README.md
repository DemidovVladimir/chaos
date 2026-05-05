# compute-jobs-pack — vertical pack for batch compute jobs

Pack: `compute-jobs-pack@1`. A composable contract for matching
**compute providers** (render farms, GPU clusters, scientific HPC
operators) with **job submitters** (3D artists, ML trainers,
researchers) over Nostr discovery + MCP dialogue.

## Why this vertical

Batch compute is the canonical "job submission" pattern: well-
specified workload, deterministic pricing per GPU-hour, an artifact
returned at the end. The protocol fits because (a) hardware facets
(GPU model, VRAM, interconnect) are highly enumerable, (b) the
quote-then-submit-then-fetch dialogue is exactly an MCP `tools/call`
sequence, and (c) buyers benefit from a sovereign-identity market
where they can route around any single provider that throttles or
censors.

## Tag schema (sketch)

| Tag | Cardinality | Required | Purpose | Example |
|---|---|---|---|---|
| `job_type` | 1..n | required | Workload class | `job_type,rendering` |
| `runtime` | 1..n | required | Compute runtime | `runtime,cuda` |
| `gpu_model` | 1..n | required | GPU SKU | `gpu_model,rtx-4090` |
| `gpu_count_band` | 1 | required | Per-job GPU count tier | `gpu_count_band,1-8` |
| `vram_per_gpu_gb` | 1 | required | VRAM per GPU | `vram_per_gpu_gb,80` |
| `interconnect` | 1 | recommended | `pcie`, `nvlink`, `infiniband` | `interconnect,nvlink` |
| `region` | 1..n | required | Datacenter region (ISO 3166-1) | `region,us-west` |
| `price_per_gpu_hour_cents` | 1 | required | Pricing in USD cents | `price_per_gpu_hour_cents,180` |
| `min_job_seconds` | 1 | recommended | Minimum billable duration | `min_job_seconds,60` |
| `max_job_seconds` | 1 | recommended | Maximum job wall time | `max_job_seconds,604800` |
| `availability_window` | 1 | required | `spot`, `reserved`, `on-demand` | `availability_window,spot` |
| `tee_capable` | 1 | recommended | Confidential-compute support | `tee_capable,sev-snp` |

`d`, `title`, `summary`, `published_at`, `expiration` follow base
NIP-99. Full benchmark logs, attestation quotes, and rendered
artifacts stay off-relay.

## MCP tool surface (sketch)

| Tool | Args | Returns | Grant policy |
|---|---|---|---|
| `view_capabilities` | `{}` | TextContent (full hardware + scheduler + runtime details) | always-allow (public) |
| `request_quote` | `{job_spec: {gpu_model, gpu_count, est_seconds, vram_required}}` | TextContent (estimated cost, queue ETA, valid_until) | always-allow |
| `submit_job` | `{job_spec, container_ref, input_hash, max_cost_cents}` | TextContent (job_id, accepted/queued status) | user-confirm |
| `query_status` | `{job_id}` | TextContent (queued/running/done/failed + progress %) | always-allow if caller pubkey matches submitter |
| `cancel_job` | `{job_id}` | TextContent (final cost, refund details) | always-allow if caller pubkey matches submitter |
| `request_artifact` | `{job_id}` | EmbeddedResource (rendered frames bundle, trained-weights tarball, or `local://` URI for >10MB) | always-allow if caller pubkey matches submitter |
| `request_attestation_quote` | `{job_id}` | EmbeddedResource (TEE attestation: SEV-SNP / SGX / TDX) | always-allow if `tee_capable` and caller pubkey matches submitter |

Artifacts route through the provider's own MCP server. Large
artifacts use the `local://` URI pattern resolved via the same
server's `resources/read` endpoint.

## Example listing (NIP-99 event sketch)

```json
{
  "kind": 30402,
  "tags": [
    ["d", "h100-cluster-uswest-spot-001"],
    ["title", "8x H100 80GB NVLink, us-west, spot pricing"],
    ["summary", "CUDA 12.4, NVLink full-mesh, infiniband node interconnect, SEV-SNP capable."],
    ["job_type", "training"],
    ["job_type", "inference"],
    ["runtime", "cuda"],
    ["gpu_model", "h100-sxm"],
    ["gpu_count_band", "1-8"],
    ["vram_per_gpu_gb", "80"],
    ["interconnect", "nvlink"],
    ["region", "us-west"],
    ["price_per_gpu_hour_cents", "210"],
    ["min_job_seconds", "300"],
    ["max_job_seconds", "604800"],
    ["availability_window", "spot"],
    ["tee_capable", "sev-snp"],
    ["published_at", "1736953200"]
  ],
  "content": "8x H100 SXM with NVLink full-mesh, InfiniBand node fabric. Spot tier — preempt notice 60s. SEV-SNP attestation available for sensitive workloads."
}
```

## Capability MCPs needed

- `reputation-mcp` (existing, cross-vertical) — peer attestations on
  delivered uptime, queue-time accuracy, artifact integrity
- `tee-attestation-mcp` (new, vertical-specific) — verifies
  SEV-SNP / SGX / TDX quotes against vendor root certificates;
  required when the seeking agent's data sensitivity demands confidential compute
- `benchmark-mcp` (new, vertical-specific) — submits a small
  standard test job (tiny CUDA workload, known-output renderer
  scene) before a large commitment, verifying claimed hardware

`market-comp-mcp` is reused for $/GPU-hour comps across the
network.

## Trust signals specific to this vertical

- **NIP-58 badges**:
  - `verified-compute-provider` — operator confirms identity and
    physical datacenter
  - `tee-capable` — operator validates a current TEE quote against
    vendor root certificate
  - `co2-attested` — green-energy attestation (REC certificates,
    grid-mix attestation)
  - `uptime-verified` — sustained availability per consumer
    attestations
- **Attestations** (kinds 30410/30411): submitters attest to
  delivered queue ETA accuracy, artifact integrity (hash matches),
  and refund honor on preemption
- **Disputes** center on artifact tampering, claimed-but-absent
  TEE, queue-time misrepresentation, or hardware swap
  (claimed H100, ran A100). Resolved via `benchmark-mcp` re-runs
  and TEE quote re-validation

## Status

Sketched, not implemented. Open to community implementation per
`VERTICALS.md` § "Anatomy of a new pack".
