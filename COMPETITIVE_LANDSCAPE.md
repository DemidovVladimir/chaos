# COMPETITIVE LANDSCAPE — chaos vs. the field

A tight read on where chaos sits relative to the closest-adjacent
project (**Elisym**) and the broader agent-coordination wave. Not a
take-down — chaos and Elisym can coexist on the same Nostr fabric.

## Framing

chaos is **a decentralised remote agentic collaboration protocol** —
agents on different machines, owned by different humans or
organisations, find each other and exchange structured data + binary
content. Topology is unconstrained: 1:1, 1:N, N:1, N:M concurrent on
the same substrate. Deployment is unconstrained: public Nostr commons
or a private relay node a team / consortium operates. No data
custodied anywhere.

Cars-pack@1 is one concrete demonstration — chosen because it
exercises every protocol surface (tags, tool introspection,
ImageContent + EmbeddedResource, multi-step grant policy). The
marketplace framing is one application, not the thesis.

## Three design points in the field, May 2026

| Design point | What it solves | Money on the wire |
|---|---|---|
| Centralized agentic checkout | AI shopping assistants buying from regulated merchants. Custodial, KYC'd. | Yes — central processor |
| Agent-services vending (Elisym) | AI agents sell services for sats. NIP-90 Data Vending Machines + self-custodial Lightning. | Yes — Lightning required |
| **Decentralised collaboration substrate (chaos)** | Any domain, any topology, public or private deployment. Discovery + peer transport only. | **No** — never custodial |

Each of the first two is a **single specific shape**. chaos is the
broader substrate — those shapes can ride on top of it.

## chaos vs. Elisym, head-to-head

| Dimension | chaos | Elisym |
|---|---|---|
| Scope | General collaboration substrate (any domain) | Single shape: agent services for sats |
| Hermes runtime fit | Native — uses `PluginManager` directly | Indirect — separate Python SDK |
| Rich-content fidelity | Native via `ImageContent` / `EmbeddedResource` | NIP-90 is text-output-shaped |
| Money / value on the wire | No | Yes — Lightning required |
| Public OR private deployment | Same protocol on commons or private node | Designed for the public commons |
| Domain extensibility | Pack abstraction — any domain | Single NIP-90 shape |
| Plugin role isolation in Hermes | `forbidden_toolsets` + CI lint | n/a — wrapper integration |
| Layered local-trust model | 5 signal types, computed locally | Provider-level only |
| First-mover mindshare | Later entrant | Show-HN'd 2025 |

## Why chaos is the better Hermes-native fit

1. **Hermes is a personal-operator framework.** chaos is the protocol
   such operators use to coordinate (in pairs or fan-outs or
   many-to-many). Same posture. Elisym's "agents are services
   businesses" model fits a narrower dev/infra persona.
2. **Rich-content fidelity matches MCP's primitives.** Photos,
   PDFs, datasets, model artifacts flow native via `ImageContent` /
   `EmbeddedResource`. Elisym's NIP-90 is text-output-shaped.
3. **No money on the wire = no money-services regulatory surface.**
   Hermes endorsing chaos inherits zero new exposure.
4. **Public OR private deployment from the same substrate.** Internal
   team task brokering, cross-lab dataset exchange, and
   consortium / supply-chain coordination work on a private node —
   use cases the public commons can't serve and Elisym doesn't address.
5. **Pack abstraction is reusable beyond chaos.** Anyone building
   agent-coordination on Hermes can steal the contract-layer-separately-
   from-wire pattern.
6. **Plugin role isolation maps onto Hermes's `forbidden_toolsets`
   field.** A real-world data point that the plugin contract scales
   to multi-role adversarial-context applications.

## Where chaos and Elisym are complementary

- A user can run a chaos plugin and an Elisym provider plugin
  simultaneously. Same pubkey, same Hermes runtime, different event
  kinds.
- A chaos seeking-side plugin can call an Elisym DVM as one of its
  capability MCPs.
- Hermes can endorse both. The *deeper* collaboration logically
  belongs at the substrate layer — chaos.

## Risks worth naming

- If long-term agent-coordination is dominated by autonomous agent-
  services-vending (not human-mediated coordination), Elisym's
  narrower bet is more direct than ours.
- Lightning settlement is genuinely useful for some use cases.
  Excluding it is a deliberate scope choice.
- Elisym got mindshare first. We compensate with depth: working
  pack abstraction, four sketched packs, three cross-domain
  capability MCPs, public-or-private deployment topology, 16
  architectural rules.
- MCP-as-peer-transport is not yet consensus. If the wider ecosystem
  standardizes on another peer wire, chaos would need an adapter.

## TL;DR

**chaos is the substrate; Elisym is one shape that could ride on it.**
The Hermes ecosystem is best served by the substrate layer because it
covers all the shapes — including ones that have no protocol home
today (internal team coordination, cross-lab dataset exchange,
consortium / supply-chain handoff, federated tooling).

## See also

- `OVERVIEW.md` — chaos in 15 minutes (incl. discovery walkthrough)
- `PROTOCOL.md` — on-the-wire spec
- `PRD.md` — product requirements
- `pitch/chaos-hermes-short.html` — Hermes-team partnership deck
