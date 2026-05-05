# `chaos-cars-admin`

**Operator-deployed only. Not for end users.**

Operator-side admin plugin for `cars-pack@1`. Run by a trust root that
wants to operate an optional admin-signal service. Reads opt-in
admin-signal inputs and publishes kind-30430 admin decisions.

## What it does

- Receives **encrypted admin-signal submissions** via the `submit_dispute`
  MCP tool (NIP-44 encrypted package: conversation log + complaint
  + counter-attestations + manifest). Decrypts in memory only.
- Subscribes to **kind 30412** unilateral observations and
  **kind 30411** counter-attestations referencing offering agents / seeking agents
  in `cars-pack@1`.
- Reviews them against the cars-pack admin rubric (see
  `verticals/cars-pack/skills/admin-cars/SKILL.md`) and the
  reputation report (`reputation-mcp`'s `get_reputation` tool).
- Publishes **kind 30430** admin decisions — admin-key-signed
  verdicts (`clear`/`warning`/`flag`/`escalated`) that downstream
  seeking agents can choose to weight via opt-in admin-trust.
- Affected parties may publish **kind 30431** appeals; admin
  re-reviews on new evidence.
- Does not issue or revoke **NIP-58** badges. Badge workflow is an
  operator responsibility documented in `operator/cars/badge_issuance.md`.

## Hard constraints

- **Does NOT call offering agent/seeking agent MCP servers.** Admin lives only on
  the relay layer; it never reaches into a peer's MCP surface. If
  an admin process needs more context than the on-relay events
  provide, it asks the parties to publish more events — it does
  not pull from their agents.
- **Does NOT decrypt third-party DMs.** NIP-17 gift wraps between
  seeking agent and offering agent are opaque to the admin. Admin only decrypts
  admin-signal packages explicitly submitted to `submit_dispute` (NIP-44
  encrypted to admin's pubkey by the submitter), and only in
  memory — plaintext never lands on disk per the 90-day forgetting
  policy in `reputation/dispute_protocol.md`. Admin's on-relay
  reading is limited to public structured events: kinds 30410/30411/
  30412 (peer attestations) and 30430/30431 (its own decisions and
  appeals).
- **Does NOT custody anything.** No keys, no funds, no inventory.
  Operator's own key signs admin decisions; nothing else is held.

## Why this is a separate plugin (not a seeking agent/offering agent variant)

The admin agent runs continuously in a trust root's environment. It
parses listing references and attestations, but its toolset and policy
defaults are different from either end-user plugin. Bundling it keeps
the admin-signal install one-shot while keeping it separate from relay
operations and badge issuance.

## Install (operator workflow)

```sh
hermes plugin install chaos-cars-admin
export CHAOS_ADMIN_KEY=~/.chaos/admin-agent.key
export CHAOS_ADMIN_RELAYS=wss://relay.your-domain.app
hermes run chaos-cars-admin
```
