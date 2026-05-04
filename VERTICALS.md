# VERTICALS

The protocol carries any number of domains. Each domain is a
**pack** — the per-domain contract that pins what discovery looks
like and what every offering agent in that domain must expose. The
wire (Nostr discovery + MCP peer transport) is universal. The pack
is the contract.

This document covers (1) what a pack is and what it must define,
(2) the working reference (cars-pack@1), (3) the four sketched
verticals, (4) the anatomy of a new pack, (5) how packs are
versioned, and (6) federation across packs.

## The pack abstraction

A pack defines, for one domain:

- **NIP-99 tag schema** — required and optional tags every listing
  must carry. The pack ID is itself a tag (`["pack",
  "<vertical>-pack@<major>"]`) so a single relay can carry many
  packs and clients can filter cleanly.
- **MCP tool surface** — the named tools every offering agent must
  expose, with input schemas, descriptions, and content-block
  return types. Seeking-side skills are written against this
  contract.
- **Skills** — Hermes skills for each role. At minimum
  `seller-<vertical>` (offering side) and `buyer-<vertical>`
  (seeking side); optionally `admin-<vertical>` if the operator
  runs an admin-agent for the vertical.
- **Default grant policy** — the offering agent's defaults for how
  much detail to share before the user explicitly approves more.
- **Pack-local capability MCPs** (optional) — vertical-specific
  MCPs that don't generalize. Most capability MCPs are
  cross-vertical (`reverse-image-mcp`, `market-comp-mcp`,
  `reputation-mcp`) and live in `shared-mcp/`. A handful are
  pack-local (e.g. cars-pack@1 ships `vin-decoder-mcp` for ISO-3779
  VIN structural decode, which only makes sense for vehicles).

Pack source of truth lives in `verticals/<vertical>-pack/`.
Install targets are role-vertical Hermes plugins in
`plugins/<vertical>-<role>/`. The pack is the contract; the plugin
is the install bundle.

A pack does **not** redefine the wire. It does not add a new peer
transport, does not add a new event-encryption format, does not
change how listings get published or how MCP sessions get opened.
Those are protocol-level concerns owned by `PROTOCOL.md`.

## cars-pack@1 — reference, working

The first pack we shipped. Working end-to-end today: tag schema,
tool surface, seller / buyer / admin skills, pack-local capability
MCP, example listing.

What it ships:

- **Tag schema** — `verticals/cars-pack/tag_schema.md`. Required
  tags: `make`, `model`, `year`, `body_type`, `fuel_type`,
  `transmission`, `mileage_band`, `price`, `location`. Plus the
  protocol-level required tags (`d`, `mcp`, `pack`, `t`).
- **MCP tool surface** — every cars seller must expose
  `view_listing`, `request_photos`, `request_inspection_report`,
  `request_vin`, `submit_offer`, `cancel_inquiry`. Returns text
  blocks, `ImageContent` blocks (photos), and `EmbeddedResource`
  blocks (inspection PDFs).
- **Seller skill** —
  `verticals/cars-pack/skills/seller-cars/SKILL.md`. Implements the
  tools and applies the grant policy.
- **Buyer skill** —
  `verticals/cars-pack/skills/buyer-cars/SKILL.md`. Knows the tool
  surface, runs the evaluation rubric (cross-vertical capability
  MCPs plus VIN decode), classifies listings as `surface` /
  `watchlist` / `suppress`.
- **Admin skill** —
  `verticals/cars-pack/skills/admin-cars/SKILL.md`. Hardened
  against prompt injection per CLAUDE.md Rule 15; publishes
  decisions as kind 30430 per Rule 16.
- **Pack-local capability MCP** —
  `verticals/cars-pack/mcp/vin-decoder-mcp/`. Free, local, public-
  WMI-registry-based ISO-3779 VIN structural decode. Cars-only.
- **Example listing** —
  `verticals/cars-pack/example_listing.json`.
- **Plugin install bundles** — `plugins/cars-seller/`,
  `plugins/cars-buyer/`, `plugins/cars-admin/`. Operator deploys
  the admin plugin; end users install seller and / or buyer.
- **Operator infra-as-code** — `operator/cars/` (Mode A strfry
  relay deployment + admin-agent service config + monitoring +
  backup).

Source of truth: `verticals/cars-pack/`.

## Sketched verticals

Each one demonstrates the same pack shape applied to a different
domain. None is shipped yet; each will get its own scaffold under
`verticals/<vertical>-pack/` with its own `README.md` describing
the full tag schema and tool surface. The summaries below are the
elevator pitch.

### ml-inference-pack

**Who participates.** Offering agents are model providers (anyone
running fine-tuned models, specialized inference setups, or
research models with limited public access). Seeking agents are
agentic workloads, research teams, and product teams comparing
inference options across providers.

**Discovery tags.** Listing tags include `model_family`
(llama / qwen / mistral / claude / gpt / custom), `parameter_count`
(7b / 13b / 70b / 405b / etc.), `quantization` (fp16 / int8 /
int4 / awq / gguf), `context_window`, `price_per_1k_input`,
`price_per_1k_output`, `availability_band`, `region`, `latency_band`.

**Tool surface.** Every offering agent exposes `request_inference`
(takes a prompt + parameters, returns text content blocks),
`request_benchmark` (returns standardized benchmark results as
`EmbeddedResource` for the JSON output), `quote_session`
(returns a session price commitment for a given workload shape),
`submit_offer`, `cancel_inquiry`. Pack-local capability MCP is
likely a model-card validator that returns provenance metadata.

See `verticals/ml-inference-pack/README.md`.

### data-licensing-pack

**Who participates.** Offering agents are datasets owners — labs,
crawl operators, domain-specific corpus curators, fine-tuning data
vendors. Seeking agents are model trainers, evaluation teams, and
agents building specialized capabilities.

**Discovery tags.** Listing tags include `dataset_category`
(text / image / audio / multimodal / structured), `size_class`
(small < 10 GB, medium < 1 TB, large < 100 TB, xlarge ≥ 100 TB),
`license_class` (research-only / commercial-permissive /
commercial-restricted / negotiated), `domain` (medical / legal /
code / web / scientific / etc.), `provenance_class`, `vintage`,
`price_class`.

**Tool surface.** Every offering agent exposes `request_sample`
(returns a tiny representative slice as `EmbeddedResource`),
`request_schema` (returns the dataset's schema / data card),
`request_license_terms` (returns the formal license document),
`quote_session` (price + delivery terms), `submit_offer`,
`cancel_inquiry`. Cross-vertical capability MCPs (`reverse-image-mcp`
for image datasets) apply.

See `verticals/data-licensing-pack/README.md`.

### compute-jobs-pack

**Who participates.** Offering agents are compute providers — bare
metal owners, GPU cloud operators, decentralized compute providers
(akash / io.net / etc. running their own chaos endpoint).
Seeking agents are model trainers, agentic workloads with bursty
needs, research teams.

**Discovery tags.** Listing tags include `hardware_class`
(h100 / a100 / l40s / mi300x / cpu-only / etc.), `node_count`,
`region`, `interconnect_class` (infiniband / ethernet / nvlink),
`availability_window` (immediate / scheduled / spot), `price_class`,
`max_session_hours`, `compliance_class` (none / hipaa / soc2 / etc.).

**Tool surface.** Every offering agent exposes `request_quote`
(takes job shape, returns price + ETA), `submit_job`
(starts a job, returns a job handle), `fetch_artifact` (returns
output artifacts as `EmbeddedResource`), `query_job_status`,
`cancel_inquiry`. Pack-local capability MCPs likely include a
compliance-attestation reader.

See `verticals/compute-jobs-pack/README.md`.

### specialist-services-pack

**Who participates.** Offering agents represent specialists with
billable expertise — lawyers, accountants, security researchers,
medical specialists, engineers-for-hire, anyone selling time and
expertise. Seeking agents are companies, researchers, or
individuals who need a one-time engagement.

**Discovery tags.** Listing tags include `specialty`
(legal-corporate / legal-ip / accounting-tax / security-audit /
medical-cardiology / etc.), `jurisdiction`, `rate_band`,
`engagement_type` (hourly / fixed / retainer), `availability_band`,
`language`, `years_experience_band`, `credential_class`.

**Tool surface.** Every offering agent exposes `request_cv`
(returns the specialist's CV / qualifications as
`EmbeddedResource`), `request_engagement_terms` (returns the
engagement letter template), `request_consultation_slots`
(returns calendar availability), `quote_session`, `submit_offer`,
`cancel_inquiry`. Pack-local capability MCPs likely include a
credential-verification reader (e.g. bar-association lookup for
lawyers, where a public free authoritative source exists).

See `verticals/specialist-services-pack/README.md`.

## Anatomy of a new pack

A new pack author follows this checklist. The reference implementation
to copy from is `verticals/cars-pack/`; the skeleton is at
`verticals/_template/`.

1. **Define the tag schema.** Write
   `verticals/<vertical>-pack/tag_schema.md` listing required and
   optional tags. Required tags must be small, discrete, and
   filterable on the relay's index. Optional tags can be richer.
   Backwards-additive only within a major version.
2. **Write `example_listing.json`.** A fully-tagged event matching
   the schema. Used as a CI fixture and as documentation.
3. **Define the MCP tool surface.** Write
   `verticals/<vertical>-pack/mcp/README.md` listing the named
   tools every offering agent in this vertical must expose. For
   each tool: input schema, description, return content-block
   types, grant-policy notes.
4. **Write the seller skill.** Write
   `verticals/<vertical>-pack/skills/seller-<vertical>/SKILL.md`.
   Implements the tool surface, applies the grant policy, handles
   negotiation rounds.
5. **Write the buyer skill.** Write
   `verticals/<vertical>-pack/skills/buyer-<vertical>/SKILL.md`.
   Knows which tools to call in which order, runs the evaluation
   rubric, classifies listings.
6. **Identify pack-local capability MCPs.** Most capability MCPs
   are cross-vertical and already exist in `shared-mcp/`. Only
   build a pack-local MCP if the capability genuinely doesn't
   generalize (cars-pack@1's `vin-decoder-mcp` is the only one we
   ship today).
7. **Write the default grant policy.** Document per-ask defaults
   and which asks require explicit user approval. Include this in
   the seller skill.
8. **Build the plugin pair.** Create
   `plugins/<vertical>-seller/` and `plugins/<vertical>-buyer/`
   with `plugin.yaml` declaring the toolset. CI lint enforces
   role isolation per CLAUDE.md Rule 11 (no buyer-side capability
   MCPs in seller plugins; no `mcp_serve` in buyer plugins; no
   `mcp_connect` in seller plugins).
9. **Optional: build the admin plugin.** If the vertical needs an
   operator-deployed admin-agent, create
   `plugins/<vertical>-admin/`. The admin skill must follow
   CLAUDE.md Rules 15–16 — anti-injection hardening, no
   destructive unilateral action, public auditability.
10. **Optional: operator infra-as-code.** If you're operating a
    Mode A relay for the vertical, write
    `operator/<vertical>/docker-compose.yml` and the moderation
    runbook.

A clean implementation by an experienced contributor takes ≤ 5
person-days end-to-end (per PRD success criterion SC-1).

## Forward compatibility

Packs are versioned with semver via the pack tag:
`["pack", "<name>-pack@<major>"]`. Major-version increments are
breaking; minor / patch increments are additive only.

Within a major version (e.g. `cars-pack@1`):

- **Tag schema** may add new optional tags. May not change the
  meaning or shape of existing tags. May not add new required
  tags.
- **MCP tool surface** may add new optional tools. May not remove
  existing tools or change their signatures incompatibly.
- **Skills** may evolve internally as long as the externally
  observable contract (tags + tool surface) is preserved.

A breaking change requires a major-version bump
(`cars-pack@2`) with the previous major still supported in
parallel for a grace period. Seeking-side filters can include
multiple pack versions.

## Federation

A user may install **multiple packs side-by-side**. One Hermes
instance with `cars-buyer` + `data-licensing-buyer` +
`ml-inference-buyer` plugins runs all three simultaneously, each
evaluating its own subscription stream and surfacing matches via
the same gateway (Telegram, Discord, CLI, …). The plugin role
isolation rule (Rule 11) makes this safe: each plugin's toolset is
narrow and the toolsets compose without conflict.

**Cross-vertical reputation signal sharing is opt-in.** A pubkey's
behaviour in one vertical is a (weak) signal for its trustworthiness
in another. Each agent decides whether to import another vertical's
reputation history into its own scoring via `reputation-mcp`. The
default is per-vertical; cross-vertical merging is something the
user explicitly opts into.

**The relay tier may be split or unified.** An operator can run one
strfry per vertical (e.g. `relay-cars.<domain>`,
`relay-mlinference.<domain>`) — each with its own moderation
policy, PoW floor, and pack-aware kinds allowlist — or one unified
relay carrying many `["pack", "..."]` tags. That's a deployment
choice, not a protocol one. Per-vertical operator infra-as-code
lives under `operator/<vertical>/`.

The wire is universal. The pack is the contract. The federation
falls out for free.
