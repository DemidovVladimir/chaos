# `operator/cars/admin-agent` — opt-in admin-signal Hermes instance

This is the optional deployable admin agent for `cars-pack@1`. It is a
Hermes instance running the `admin-cars` skill (see
`verticals/cars-pack/skills/admin-cars/SKILL.md`) packaged via the
`plugins/cars-admin/` plugin.

The admin agent receives encrypted admin-signal packages from
participants via MCP, applies the per-pack rubric, and publishes
signed kind-30430 admin-decision events to the relay. It does not
operate the relay, issue NIP-58 badges, or arbitrate disputes for the
platform. Its trust is **opt-in**: a user only sees its decisions if
they have explicitly added this admin's pubkey to their trust list at
install time (Rule 16).

## Boundary with `operator/cars`

`operator/cars/` is relay infrastructure: strfry, Caddy, PoW policy,
backups, monitoring, moderation contact, and manual NIP-58 badge
workflow. This folder is only the deployment runbook for a separate
Hermes admin-signal process.

The admin-agent can publish kind 30430/30431 events. It cannot change
relay policy, delete relay data, issue badges, revoke badges, or call
buyer/seller MCP servers.

See also:

- `../../../reputation/dispute_protocol.md` — admin signal / appeal flow
- `../../../reputation/admin_threat_model.md` — required defenses
- `../../../reputation/kinds.md` — kind 30430 / 30431 schemas
- `verticals/cars-pack/skills/admin-cars/SKILL.md` — the skill itself
- `plugins/cars-admin/` — the plugin packaging

## Deployment prerequisites

1. A separate Hermes installation (do NOT colocate with the relay
   process; segregate failure domains).
2. The `cars-admin` plugin installed
   (`hermes plugin install cars-admin`).
3. A dedicated keypair for this admin role (NEVER the operator's
   relay key, badge key, or personal keypair). Stored in
   `~/.chaos/.env` mode 0600.
4. Outbound websocket connectivity to the operator's relay
   (`wss://relay.<domain>`) and 2–3 community relays.
5. An MCP HTTP+SSE bind that buyers/sellers can reach (default
   port 7630, behind Caddy with TLS for production).
6. Matrix or email integration for the escalation queue (see
   `escalation_queue/README.md`).

## Configuration

`config.yaml` lives next to this README. Required keys:

```yaml
admin_pubkey: <hex>             # set in pubkey.json after keygen
relay_urls:
  - wss://relay.<your-domain>
  - wss://relay.community-1.example
mcp_bind: 0.0.0.0:7630
escalation:
  matrix_room: "!ops:<homeserver>"
  email_fallback: ops@<your-domain>
retention:
  plaintext_purge_after_days: 0     # purge plaintext at decision time
  decision_data_retain_days: 90
rubric:
  high_value_threshold: "15k-50k"   # currency_band threshold to escalate
  no_response_window_days: 7
  appeal_window_days: 30
  severity_high_requires_co_sign: true
```

## Pubkey announcement (Rule 16)

The admin-pubkey must be **announced**, not silently assumed. We
do this via:

1. A signed pubkey-announcement file at
   `https://<your-domain>/.well-known/chaos-admin/cars-pack.json`
   (content from `pubkey.json`).
2. A NIP-65 relay-list metadata event from the admin-pubkey itself.
3. Documentation in `trust_list_announcement.md` explaining how
   end-users add this pubkey to their trust list.

Users who don't opt in see no admin decisions; their reputation-mcp
returns `admin_decisions: []` regardless of what's on the relay.

## Operations

- **Start:** `hermes serve --skill admin-cars --config
  operator/cars/admin-agent/config.yaml`
- **Logs:** stderr only at INFO; structured JSON in production. No
  plaintext evidence, ever, in logs.
- **Rotation:** `retention/rotate.sh.example` purges plaintext at
  decision time and decision-records at 90 days. Wire it as a
  systemd timer or cron. See `retention/README.md`.
- **Escalation:** the admin-agent writes a sanitized summary to
  `escalation_queue/` for any case the rubric flags as ambiguous,
  high-value, cross-jurisdiction, or `severity=high`. See
  `escalation_queue/README.md` for Matrix bot wiring.
- **Pubkey rotation:** if you suspect compromise, generate a fresh
  pubkey, publish a NIP-09 deletion of all prior 30430s, and force
  users to re-opt-in to the new pubkey. The old pubkey is
  effectively gone from the trust graph.

## Pre-launch checklist

- [ ] Admin-pubkey generated, stored mode 0600, NEVER colocated
      with the relay key, badge key, or operator's personal key
- [ ] `pubkey.json` populated and operator-signed
- [ ] `.well-known/chaos-admin/cars-pack.json` reachable
- [ ] `trust_list_announcement.md` reviewed and posted publicly
- [ ] `escalation_queue/` integration tested end-to-end (Matrix
      / email fallback both reachable)
- [ ] `retention/rotate.sh.example` adapted, scheduled, dry-run
      tested
- [ ] Skill review per Rule 15 completed (red-team checklist in
      `reputation/admin_threat_model.md` passes)
- [ ] Co-signature workflow tested for `severity=high` decisions
