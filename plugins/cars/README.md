# cars — chaos plugin for cars-pack@1

Single role-flexible plugin that wires `cars-pack@1` into a Hermes
agent via the universal `chaos-agent` engine.

Installing this plugin gives an agent the full toolkit for
participating in cars discovery — both directions:

- **Publish** the user's own car listings as NIP-99 events
- **Serve** photos and the inspection PDF over MCP HTTP+SSE
- **Subscribe** to others' cars listings with REQ tag-filters
- **Inquire** about matched listings via NIP-17 sealed gift-wraps
- **Evaluate** counterparty offerings using the cross-domain
  capability MCPs (`reverse-image`, `market-comp`, `vin-decoder`,
  `reputation`)

Whether any single session looks like "publish only," "subscribe
only," or both at once is decided by the user / the skill, not by
the plugin shape. The plugin itself doesn't pre-commit a role.

## Replaces

This plugin supersedes the previous role-split pair `cars/`
and `cars/`. The split was commerce-coded and assumed an agent
was either a offering agent OR a seeking agent. The protocol is symmetric: any agent
can do either or both, and the plugin shape now reflects that.

## Cross-pack pro upgrade

`plugins/chaos-pro/` is a separate cross-domain pro tier that
upgrades the capability MCPs across every installed pack
plugin (cars + future packs). Install it alongside `plugins/cars/`
to get deeper reverse-image / market-comp / reputation analysis.

## Admin plugin (operator-only)

`plugins/cars-admin/` is a distinct, operator-deployed plugin for
the cars-pack admin agent. It is NOT installed by end-user agents;
it runs only on the operator's infrastructure for dispute resolution
and signed kind-30430 decision events.
