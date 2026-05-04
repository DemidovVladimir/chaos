# `chaos-cars-admin`

**Operator-deployed only. Not for end users.**

The admin agent for the cars vertical. Run by whoever operates a
chaos cars relay (Mode A or Mode B). Reads dispute
submissions, publishes admin decisions, manages NIP-58 badge
issuance.

## What it does

- Receives **encrypted dispute submissions** via the `submit_dispute`
  MCP tool (NIP-44 encrypted package: conversation log + complaint
  + counter-attestations + manifest). Decrypts in memory only.
- Subscribes to **kind 30412** unilateral dispute-attestations and
  **kind 30411** counter-attestations referencing sellers / buyers
  in the cars vertical.
- Reviews them against the cars-pack admin rubric (see
  `verticals/cars-pack/skills/admin-cars/SKILL.md`) and the
  reputation report (`reputation-mcp`'s `get_reputation` tool).
- Publishes **kind 30430** admin decisions — operator-signed
  verdicts (`clear`/`warning`/`flag`/`escalated`) that downstream
  buyers can choose to weight via opt-in admin-trust.
- Affected parties may publish **kind 30431** appeals; admin
  re-reviews on new evidence.
- Issues / revokes **NIP-58** verified-seller badges.

## Hard constraints

- **Does NOT call seller/buyer MCP servers.** Admin lives only on
  the relay layer; it never reaches into a peer's MCP surface. If
  an admin process needs more context than the on-relay events
  provide, it asks the parties to publish more events — it does
  not pull from their agents.
- **Does NOT decrypt third-party DMs.** NIP-17 gift wraps between
  buyer and seller are opaque to the admin. Admin only decrypts
  dispute packages explicitly submitted to `submit_dispute` (NIP-44
  encrypted to admin's pubkey by the submitter), and only in
  memory — plaintext never lands on disk per the 90-day forgetting
  policy in `reputation/dispute_protocol.md`. Admin's on-relay
  reading is limited to public structured events: kinds 30410/30411/
  30412 (peer attestations) and 30430/30431 (its own decisions and
  appeals).
- **Does NOT custody anything.** No keys, no funds, no inventory.
  Operator's own key signs admin decisions; nothing else is held.

## Why this is a separate plugin (not a buyer/seller variant)

The admin agent runs continuously in the operator's environment.
It speaks both the seller and buyer pack contracts (it has to
parse listings AND attestations) but its toolset and policy
defaults are different from either end-user plugin. Bundling it
keeps the operator install one-shot.

## Install (operator workflow)

```sh
hermes plugin install chaos-cars-admin
export CHAOS_OPERATOR_KEY=~/.chaos/operator.key
export CHAOS_ADMIN_RELAYS=wss://relay.your-domain.app
hermes run chaos-cars-admin
```
