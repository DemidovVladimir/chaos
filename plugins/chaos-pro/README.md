# `chaos-pro`

**Cross-vertical paid upgrade.** One subscription, applies to all
installed seeking agent plugins across all verticals.

## What it does

Flips three capability MCPs from **fast** tier into **thorough** /
**pro** tier mode, for every seeking agent plugin you have installed:

- `reverse-image-mcp` — adds EXIF cross-checks, federated scam-
  hash registry queries, and optional CLIP semantic match.
- `market-comp-mcp` — widens the comp window from 60 to 180 days,
  pulls comps from a broader relay set.
- `reputation-mcp` — deeper web-of-trust depth (4 hops vs 2),
  broader attestation scan, optional on-chain stake reads (Phase 1
  hook).

If you install `cars` today and `watches-seeking agent` next month,
**both** automatically use the upgraded MCPs the moment
`chaos-pro` is installed. There is no per-vertical pro
variant (no `cars-pro`).

## Why one cross-vertical pro instead of per-vertical pros

- The capability MCPs that matter at thorough tier are the same
  across verticals (image fraud, pricing, reputation).
- One subscription is lower friction for users.
- Aligned with `BUSINESS_MODEL.md`: the platform's revenue comes
  from premium plugin tiers, not from per-vertical taxes.

## Pricing

- Subscription: $9 / month, or
- x402 per-call: ~$0.10 per `thorough`-tier call.

Both are denominated in USDC on Base. The platform never custodies
funds; pricing is enforced at the MCP level via x402 and at the
engine level via subscription tokens (AGENTS.md rule 8).

## Install (stub)

```sh
hermes plugin install chaos-pro
```

The pro plugin will enumerate every installed `chaos-*-seeking agent`
plugin and flip its `pro_mode` config to `true`. Uninstall returns
all of them to the free fast tier.
