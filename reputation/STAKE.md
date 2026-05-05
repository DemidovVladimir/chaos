# `STAKE.md` — Phase 1 placeholder for opt-in onchain staking

**Status: NOT IN MVP.** This document captures the design intent
for an opt-in staking layer roughly 3–6 months post-launch. It
exists today to (a) reserve the kind numbers (30420, 30421,
30422), (b) keep the reputation-mcp's `onchain_stake` field
shape stable, and (c) record the reasoning behind the eventual
chain choice.

## Why a stake layer at all

The four reputation layers we ship in MVP (badges, attestations,
mute lists, WoT) plus the fifth admin-decisions layer cover most
of the trust gap. Where they fall short is the cold-start case:
a brand-new offering agent with a freshly-generated keypair, no badge,
no attestations, no WoT proximity. There is currently nothing
they can do to credibly signal "I have skin in the game."

Opt-in staking fills exactly that gap. A offering agent voluntarily locks
some amount of value to a public stake account. Their listings
carry a tag pointing at the stake commitment. Seeking agents' reputation-
mcp picks up the stake as a positive signal weighted by amount and
lock period. If a 2-of-3 multi-sig (operator + seeking agent + community
arbitrator) decides the offering agent defrauded a counterparty, the
stake can be slashed — but the operator alone never can.

## Why Solana (not Ethereum)

- **Cost.** Stake/unstake transactions need to be cheap so a
  small private offering agent can use the system. Solana transaction
  fees are ≈ $0.0001; Ethereum L1 swings between $1 and $50.
  Even Ethereum L2s like Base/Arbitrum sit at $0.05–$0.50, an
  order of magnitude over Solana.
- **Speed.** A stake commit landing in 1–2 seconds keeps the
  marketplace UX snappy. L2 finality is comparable; L1 is not.
- **Keypair compatibility.** Solana uses ed25519. Nostr uses
  secp256k1 (different curve), so we need a binding event either
  way (kind 30420). The mature ed25519 wallet stack (Phantom,
  Solflare) makes the user-side flow straightforward.
- **Mature multi-sig tooling.** Squads v4 / Realms cover the
  2-of-3 case off the shelf.

## Why NOT MagicBlock for our profile

MagicBlock's ephemeral-rollup model is built for high-frequency,
low-stakes session state (think realtime games). Our profile is
the opposite: sparse high-value commitments that live for months.
Settling to mainnet on every commit/release is correct for us;
the rollup overhead would be wasted.

## Architecture sketch (Phase 1)

A simple Anchor program with two instructions:

1. `stake_lock(amount, lock_until)` — locks `amount` SPL or SOL
   to a PDA derived from the offering agent's Solana pubkey. Emits an
   on-chain log with the offering agent's Nostr pubkey (committed via
   the kind-30420 binding event).
2. `stake_release_or_slash(stake_account)` — multi-sig 2-of-3
   over `(operator-admin, seeking agent, community-arbitrator)`. On
   success either:
   - releases the stake to the offering agent (clean exit), OR
   - slashes per the 70/20/10 split below.

Slashing split:

- **70%** to the wronged seeking agent (pastel — direct restitution).
- **20%** to a vertical-pack dispute pool (funds future
  arbitration costs).
- **10%** burn (signals the network does not capture the slash;
  reduces moral hazard for the multi-sig).

## Identity binding (kind 30420)

The offering agent publishes a kind 30420 event whose content includes:

- Their Solana pubkey (ed25519).
- A signature over `H("nostr-bind:" || nostr_pubkey ||
  solana_pubkey)` made with the Solana key.
- A second signature over the same message made with the Nostr
  key (which is the event signature itself).

The mutual signatures prove control of both keys without trusting
either side alone.

## Stake commitment (kind 30421)

References the on-chain stake account via Solana account address +
slot. Carries `amount`, `lock_until`, `currency` (SOL / USDC SPL).
Reputation-mcp reads this field as `onchain_stake` and weights it
in `scoring.md` (configurable, default 0.10 of total).

## Slash record (kind 30422)

Published by the multi-sig signer set after a successful slash.
Not replaceable. Carries the on-chain transaction signature so
any party can verify against a Solana RPC.

## Opt-in semantics

- A offering agent without a stake commitment is **not** disadvantaged
  beyond not getting the stake-layer boost. All Phase-0
  reputation layers continue to work normally.
- A seeking agent who doesn't trust onchain stake at all sets
  `cfg.layer_weights.onchain_stake = 0.0` and the stake layer
  contributes nothing to their score for any offering agent.
- This is consistent with our top-level rule: the platform never
  gates access; it surfaces signals.

## Legal review required

Before deployment in any jurisdiction:

- Securities review per jurisdiction (a slashable bond may or may
  not constitute a security in some regimes).
- AML/KYC review for the multi-sig signers (especially the
  community-arbitrator role).
- Consumer-protection review for the slash mechanic (regimes
  vary on whether a private 2-of-3 multi-sig is enforceable
  vs. requires a court).

The legal review is per-jurisdiction; rollout is gated on it.

## Implementation timeline

- **MVP (today):** kinds 30420 / 30421 / 30422 reserved. Schema
  in `kinds.md` marked "placeholder." `reputation-mcp.get_reputation`
  returns `onchain_stake: null` for every pubkey.
- **Phase 1 (~3–6 months post-launch):** Anchor program audited;
  Solana devnet demo; first jurisdiction's legal sign-off.
- **Phase 1 GA:** mainnet deployment in cleared jurisdictions
  only.
